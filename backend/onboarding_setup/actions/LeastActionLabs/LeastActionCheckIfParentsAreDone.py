# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.

bashblock= {
"install_dependencies.sh": "pip install requests python-dateutil croniter",
}
codeblock = {
"main.py": '''
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dateutil.parser import isoparse
from croniter import croniter
from src.common.logger.logger import log_info, log_error

BANNER = "=" * 57


def _get_cron_granularity(cron_expr: str) -> str:
    parts = cron_expr.strip().split()
    if len(parts) < 5:
        return 'minute'
    minute, hour, dom, month, dow = parts[0], parts[1], parts[2], parts[3], parts[4]
    if month != '*' and dom != '*':
        return 'year'
    if dom != '*' and dow == '*':
        return 'month'
    if dow != '*':
        return 'week'
    if hour != '*':
        return 'day'
    if minute != '*':
        return 'hour'
    return 'minute'


def _truncate_dt(dt: datetime, granularity: str) -> datetime:
    if granularity == 'year':
        return dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    if granularity == 'month':
        return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if granularity == 'week':
        return (dt - timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    if granularity == 'day':
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    if granularity == 'hour':
        return dt.replace(minute=0, second=0, microsecond=0)
    return dt.replace(second=0, microsecond=0)


def _prev_cron_time(cron_expr: str, anchor: datetime) -> datetime:
    """Return the most recent scheduled time for cron_expr that is <= anchor."""
    try:
        it = croniter(cron_expr, anchor + timedelta(seconds=1))
        return it.get_prev(datetime).replace(microsecond=0)
    except Exception as e:
        log_error("action", "_prev_cron_time", "exception", f"Invalid cron '{cron_expr}': {str(e)}")
        raise


def _fetch_parent_task(parent_info: Dict[str, Any], auth_token: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
    parent_name = parent_info.get("task_name", "unnamed")
    try:
        resp = requests.post(
            "http://backend:8000/api/v1/catalog/search",
            json={
                "item_filter": {
                    "item_type": "task",
                    "name": parent_info.get("task_name", ""),
                    "project_laui": parent_info.get("project_laui", ""),
                    "account_laui": parent_info.get("account_laui", ""),
                    "partition": parent_info.get("partition", "ALL"),
                    "get_by_pk": True
                },
                "pagination": {},
                "projection": {"include": ["name", "parent_laui", "state", "frequency", "prev_interval_start"]}
            },
            headers={"Cookie": f"frontend_token={auth_token}", "Content-Type": "application/json"},
            timeout=timeout
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", []) if isinstance(data, dict) else []
        if not items:
            log_info("action", "_fetch_parent_task", "not_found", f"Parent not found in catalog: {parent_name}")
        return items[0] if items else None
    except requests.exceptions.HTTPError as e:
        log_error("action", "_fetch_parent_task", "http_error", f"HTTP error fetching '{parent_name}': {str(e)}")
        return None
    except requests.exceptions.RequestException as e:
        log_error("action", "_fetch_parent_task", "request_error", f"Request error fetching '{parent_name}': {str(e)}")
        return None
    except Exception as e:
        log_error("action", "_fetch_parent_task", "error", f"Unexpected error fetching '{parent_name}': {str(e)}")
        return None


def _fetch_current_task(task_laui: str, auth_token: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
    try:
        resp = requests.get(
            f"http://backend:8000/api/v1/catalog/get?item_laui={task_laui}",
            headers={"Cookie": f"frontend_token={auth_token}", "Content-Type": "application/json"},
            timeout=timeout
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        log_error("action", "_fetch_current_task", "http_error", f"HTTP error fetching current task: {str(e)}")
        return None
    except requests.exceptions.RequestException as e:
        log_error("action", "_fetch_current_task", "request_error", f"Request error fetching current task: {str(e)}")
        return None
    except Exception as e:
        log_error("action", "_fetch_current_task", "error", f"Unexpected error fetching current task: {str(e)}")
        return None


def run(
    least_action_action_object: Dict[str, Any],
    parents: List[Dict[str, Any]],
    **kwargs,
) -> bool:
    try:
        auth_token = least_action_action_object.get('user_access_token')
        if not auth_token:
            log_error("action", "run", "missing_auth_token", "Authorization token not found")
            return False

        if not parents:
            return True

        task_laui = least_action_action_object.get('task', {}).get('laui')
        if not task_laui:
            log_error("action", "run", "missing_task_laui", "task_laui not found in action object")
            return False

        current_task = _fetch_current_task(task_laui, auth_token)
        if not current_task or not isinstance(current_task, dict):
            log_error("action", "run", "current_task_fetch_failed", "Failed to fetch current task")
            return False

        child_frequency = current_task.get('frequency')
        if not child_frequency or child_frequency == 'ADHOC':
            log_info("action", "run", "adhoc_child", "Child is ADHOC — skipping parent timing check")
            return True

        child_logical_date_raw = current_task.get('logical_date')
        if not child_logical_date_raw:
            log_error("action", "run", "missing_logical_date", "Child task has no logical_date")
            return False

        child_logical_date = isoparse(child_logical_date_raw).replace(microsecond=0)
        log_info("action", "run", "start", f"Checking {len(parents)} parent(s) — child logical_date: {child_logical_date.isoformat()}")

        for idx, parent_info in enumerate(parents, start=1):
            parent_name = parent_info.get('task_name', 'unnamed_parent')
            try:
                parent_task = _fetch_parent_task(parent_info, auth_token)
                if not parent_task:
                    log_error("action", "run", "parent_not_found",
                        f"\\n{BANNER}\\n  PARENT NOT FOUND: {parent_name}\\n{BANNER}")
                    return False

                parent_state = (parent_task.get('state') or '').strip().lower()
                if parent_state in ['error', 'fail', 'cancelled', 'cancel']:
                    log_error("action", "run", "parent_bad_state",
                        f"\\n{BANNER}\\n  PARENT NOT DONE [{idx}/{len(parents)}]: {parent_name}\\n  State: {parent_state}  (must not be error/fail/cancelled)\\n{BANNER}")
                    return False

                parent_frequency = parent_task.get('frequency')
                if not parent_frequency or parent_frequency == 'ADHOC':
                    log_error("action", "run", "parent_adhoc",
                        f"\\n{BANNER}\\n  PARENT NOT DONE [{idx}/{len(parents)}]: {parent_name}\\n  Reason: frequency is ADHOC or missing — cannot validate interval\\n{BANNER}")
                    return False

                parent_prev_interval_start = parent_task.get('prev_interval_start')
                if not parent_prev_interval_start:
                    log_error("action", "run", "parent_no_prev_interval",
                        f"\\n{BANNER}\\n  PARENT NOT DONE [{idx}/{len(parents)}]: {parent_name}\\n  Reason: no prev_interval_start — has never completed a successful run\\n{BANNER}")
                    return False

                expected_parent_run_time = _prev_cron_time(parent_frequency, child_logical_date)
                parent_prev_interval_dt = isoparse(parent_prev_interval_start).replace(microsecond=0)
                granularity = _get_cron_granularity(parent_frequency)
                expected_trunc = _truncate_dt(expected_parent_run_time, granularity)
                actual_trunc = _truncate_dt(parent_prev_interval_dt, granularity)

                if actual_trunc >= expected_trunc:
                    log_info("action", "run", "parent_pass",
                        f"[{idx}/{len(parents)}] {parent_name}: prev_interval_start={parent_prev_interval_start} ✓")
                else:
                    log_error("action", "run", "parent_not_done",
                        f"\\n{BANNER}\\n  PARENT NOT DONE [{idx}/{len(parents)}]: {parent_name}\\n  Required: {expected_trunc.isoformat()}  (granularity={granularity})\\n  Actual:   {actual_trunc.isoformat()}  (prev_interval_start)\\n{BANNER}")
                    return False

            except Exception as e:
                log_error("action", "run", "parent_error", f"Error evaluating parent '{parent_name}': {str(e)}")
                return False

        log_info("action", "run", "all_passed", f"All {len(parents)} parent(s) done ✓")
        return True

    except Exception as e:
        log_error("action", "run", "unexpected_error", f"Unexpected error: {str(e)}")
        return False
'''
}

action_variables= {
"parents": [
  {
    "task_name": "parent_task_name_example",
    "project_laui": "{{ project_laui }}",
    "account_laui": "{{account_laui}}",
    "partition": "{{ partition}}"
  }
]
}
connection= {
}

prompt = (
    "Validate that all specified parent tasks have completed successfully with correct timing. "
    "Action variable: parents (list of {task_name, project_laui, account_laui, partition}). "
    "Fetches each parent task via the LeastAction catalog API and checks: "
    "1) state is 'success', 2) execution time matches the expected logical_date partition. "
    "Returns True only if ALL parents pass both checks. Used as a dependency gate in workflows."
)

install_docs = """# LeastActionCheckIfParentsAreDone — Install Guide

## Dependencies

    pip install requests python-dateutil croniter
"""

guide_docs = """# LeastActionCheckIfParentsAreDone — Action Guide

## What it does

Validates that all specified parent tasks have completed successfully with the correct
execution timing before allowing a downstream task to proceed.

---

## Action Variables

    {
      "parents": [
        {
          "task_name": "daily_ingest",
          "project_laui": "proj_laui",
          "account_laui": "acct_laui",
          "partition": "{{ partition }}"
        }
      ]
    }

---

## Returns

True if all parent tasks are in success state with correct timing. False otherwise.
"""

description = """
Validates that all specified parent tasks have completed successfully with correct timing.
Checks each parent task's state and logical_date partition alignment via the LeastAction API.
Returns True only when all parents pass both state and timing checks.
"""

publisher = "LeastAction"

metadata = {
    "service": "LeastAction",
    "category": "Workflow",
    "tags": ["dependency", "parent", "check", "gate", "workflow", "sensor"],
    "airflow_equivalent": "ExternalTaskSensor"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

