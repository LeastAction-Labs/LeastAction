# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
bashblock= {
"install_dependencies.sh": "pip install requests",
}
codeblock = {
"main.py": '''
import requests
import json
import os
from src.common.logger.logger import log_info, log_error


def run(least_action_action_object, task_lauis, start_date=None, end_date=None, frequency=None, **kwargs):
    """
    Schedule (or reschedule) one or more existing tasks by updating their
    frequency, start_date, and end_date via the catalog upsert API, then
    resetting their runtime state to 'scheduled' so the cron scheduler
    picks them up on the next cycle.

    Parameters:
        least_action_action_object (dict): action object containing 'user_access_token'.
        task_lauis (list[str]): LAUIs of tasks to schedule.
        start_date (str | None): ISO-8601 datetime string for the schedule start.
        end_date (str | None): ISO-8601 datetime string for the schedule end.
        frequency (str | None): 'ADHOC' or a valid 5-part cron expression (e.g. '0 * * * *').

    Returns:
        bool: True if all tasks were successfully scheduled, False otherwise.
    """
    separator = "=" * 80
    log_info("action", "run", "function_entry", separator)
    log_info("action", "run", "function_entry", "ENTERING run() FUNCTION - LeastActionScheduleTasks")
    log_info("action", "run", "function_entry", separator)

    try:
        log_info("action", "run", "start", f"Starting schedule update for tasks: {task_lauis}")
        log_info("action", "run", "input_params", f"frequency={frequency}, start_date={start_date}, end_date={end_date}")

        user_access_token = least_action_action_object.get('user_access_token')

        if not user_access_token:
            log_error("action", "run", "missing_token", "user_access_token not found in action object")
            return False

        log_info("action", "run", "auth_ok", f"Auth token found (length: {len(user_access_token)})")

        if not task_lauis:
            log_error("action", "run", "empty_task_lauis", "task_lauis list is empty — nothing to schedule")
            return False

        log_info("action", "run", "task_count", f"Number of tasks to schedule: {len(task_lauis)}")

        backend_host = os.getenv("BACKEND_HOST", "backend")
        base_api_url = f"http://{backend_host}:8000/api/v1"
        get_api_url = base_api_url + "/catalog/get"
        task_create_url = base_api_url + "/task"
        task_update_url = base_api_url + "/task"

        log_info("action", "run", "urls", f"base_api_url={base_api_url}")

        headers = {
            "Cookie": f"frontend_token={user_access_token}",
            "Content-Type": "application/json"
        }

        for idx, task_laui in enumerate(task_lauis, start=1):
            log_info("action", "run", "task_iteration", separator[:60])
            log_info("action", "run", "task_iteration", f"TASK {idx} of {len(task_lauis)}: {task_laui}")
            log_info("action", "run", "task_iteration", separator[:60])

            # ── 1. Fetch existing task ──────────────────────────────────
            log_info("action", "run", "fetch_task", f"Fetching task {task_laui} from catalog...")
            task_get_response = requests.get(
                get_api_url,
                params={"item_laui": task_laui},
                headers=headers,
                timeout=30,
            )
            log_info("action", "run", "fetch_task_status", f"GET status: {task_get_response.status_code}")
            task_get_response.raise_for_status()

            task = task_get_response.json()
            log_info("action", "run", "fetch_task_ok", f"Fetched task name='{task.get('name')}' current_frequency='{task.get('frequency')}'")

            # ── 2. Build upsert body (PK: name + project_laui + account_laui + partition) ──
            body = {
                "item_type": "task",
                "name": task["name"],
                "project_laui": task["project_laui"],
                "account_laui": task["account_laui"],
                "parent_laui": task.get("parent_laui"),
                "operator_laui": task["operator_laui"],
                "connection_laui": task["connection_laui"],
            }

            # Preserve optional fields
            for field in ("partition", "payload", "config", "actions", "priority",
                          "total_retries", "retry_interval", "description"):
                if task.get(field) is not None:
                    body[field] = task[field]

            # Apply new schedule params (fall back to existing values)
            body["frequency"] = frequency if frequency is not None else task.get("frequency", "ADHOC")
            resolved_start = start_date or task.get("start_date")
            resolved_end = end_date or task.get("end_date")
            if resolved_start:
                body["start_date"] = resolved_start
            if resolved_end:
                body["end_date"] = resolved_end

            log_info("action", "run", "upsert_body", f"Upsert body: frequency={body['frequency']}, start_date={body.get('start_date')}, end_date={body.get('end_date')}")

            # ── 3. Upsert task definition ────────────────────────────────
            log_info("action", "run", "catalog_create", f"Upserting task via catalog/create for '{task['name']}'...")
            create_resp = requests.post(
                task_create_url,
                json=body,
                headers=headers,
                timeout=30,
            )
            log_info("action", "run", "catalog_create_status", f"POST catalog/create status: {create_resp.status_code}")
            create_resp.raise_for_status()
            log_info("action", "run", "catalog_create_ok", "Task definition upserted successfully")

            # ── 4. Reset runtime state so scheduler picks it up ──────────
            update_body = {
                "state": "scheduled",
                "retry_number": 0,
            }
            body.update(update_body)
            log_info("action", "run", "task_update", f"Resetting task state to 'scheduled' for {task_laui}...")
            task_post_response = requests.post(
                task_update_url,
                json=body,
                headers=headers,
                timeout=30,
            )
            log_info("action", "run", "task_update_status", f"POST task/update status: {task_post_response.status_code}")
            task_post_response.raise_for_status()
            log_info("action", "run", "task_update_ok", f"[DONE] Task {task_laui} scheduled successfully")

        log_info("action", "run", "complete_success", f"All {len(task_lauis)} task(s) scheduled successfully")
        log_info("action", "run", "return_true", "RETURNING TRUE")
        return True

    except requests.exceptions.Timeout:
        log_error("action", "run", "timeout", "Request timed out while calling catalog API")
        return False
    except requests.exceptions.ConnectionError as e:
        log_error("action", "run", "connection_error", f"Connection error: {str(e)}")
        return False
    except requests.exceptions.RequestException as e:
        log_error("action", "run", "request_error", f"Request error: {str(e)}")
        return False
    except Exception as e:
        log_error("action", "run", "unexpected_error", f"Unexpected error: {str(e)}")
        return False
'''
}
action_variables = {
    "task_lauis": [],
    "start_date": "",
    "end_date": "",
    "frequency": ""
}
connection = {}

prompt = (
    "Schedule one or more LeastAction tasks to run at a specified frequency over a date range. "
    "Action variables: task_lauis (list), start_date (ISO string), end_date (ISO string), frequency (cron or interval). "
    "Creates scheduled run entries via the LeastAction schedule API for each task. "
    "Returns True if all tasks were scheduled successfully."
)

install_docs = """# LeastActionScheduleTasks — Install Guide

## Dependencies

    pip install requests
"""

guide_docs = """# LeastActionScheduleTasks — Action Guide

## What it does

Schedules one or more LeastAction tasks to run over a date range at a given frequency.
Useful for backfills, periodic batch runs, or setting up recurring workflows programmatically.

---

## Action Variables

    {
      "task_lauis": ["laui_1", "laui_2"],
      "start_date": "2026-01-01",
      "end_date": "2026-01-31",
      "frequency": "daily"
    }

---

## Returns

True if all tasks were scheduled. False on any error.
"""

description = """
Schedules one or more LeastAction tasks to run over a date range at a given frequency.
Creates scheduled run entries via the LeastAction API. Returns True on success.
"""

publisher = "LeastAction"

metadata = {
    "service": "LeastAction",
    "category": "Workflow",
    "tags": ["schedule", "task", "backfill", "recurring", "leastaction"],
    "airflow_equivalent": "PythonOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
