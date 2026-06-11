# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.

bashblock = {
    "install_dependencies.sh": "pip install requests python-dateutil croniter",
}
codeblock = {
    "check_parent_task_state.py": ''' 
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dateutil.parser import isoparse
from croniter import croniter
from src.common.logger.logger import log_info, log_error


def _prev_cron_time(cron_expr: str, anchor: datetime) -> datetime:
    """Return the most recent scheduled time for cron_expr that is <= anchor.

    croniter.get_prev strictly returns a value < start_time, so we start from anchor + 1s
    to include anchor itself if it's exactly on schedule.
    Normalize microseconds to 0 for stable comparisons.
    """
    log_info("action", "_prev_cron_time", "start", f"Computing prev cron time for expr: {cron_expr}, anchor: {anchor.isoformat()}")

    try:
        adjusted_anchor = anchor + timedelta(seconds=1)
        log_info("action", "_prev_cron_time", "adjusted_anchor", f"Adjusted anchor: {adjusted_anchor.isoformat()}")

        it = croniter(cron_expr, adjusted_anchor)
        log_info("action", "_prev_cron_time", "croniter_created", "Croniter instance created successfully")

        prev_dt = it.get_prev(datetime)
        log_info("action", "_prev_cron_time", "prev_dt_raw", f"Raw prev datetime: {prev_dt.isoformat()}")

        normalized_dt = prev_dt.replace(microsecond=0)
        log_info("action", "_prev_cron_time", "normalized", f"Normalized datetime: {normalized_dt.isoformat()}")

        return normalized_dt
    except Exception as e:
        log_error("action", "_prev_cron_time", "exception", f"Error in _prev_cron_time: {str(e)}")
        raise


def _fetch_parent_task(parent_info: Dict[str, Any], auth_token: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
    """Fetch parent task details from catalog search API. Returns first matching item or None."""
    parent_name = parent_info.get("task_name", "unnamed")
    log_info("action", "_fetch_parent_task", "start", f"Fetching parent task: {parent_name}")
    log_info("action", "_fetch_parent_task", "parent_info", f"Parent info: {parent_info}")

    try:
        url = "http://backend-test:8000/api/v1/catalog/search"
        log_info("action", "_fetch_parent_task", "url", f"API URL: {url}")

        headers = {
            "Cookie":f"frontend_token={auth_token}",
            "Content-Type": "application/json"
        }
        log_info("action", "_fetch_parent_task", "headers", "Headers prepared (auth token present)")

        payload = {
            "filter": {
                "item_type": "task",
                "name": parent_info.get("task_name", ""),
                "project_laui": parent_info.get("project_laui", ""),
                "account_laui": parent_info.get("account_laui", ""),
                "partition": parent_info.get("partition", "ALL"),
                "get_by_pk": True
            },
            "pagination": {},
            "projection": {"include": ["name", "parent_laui", "state", "frequency", "last_run_date"]}
        }
        log_info("action", "_fetch_parent_task", "payload", f"Request payload: {payload}")

        log_info("action", "_fetch_parent_task", "sending_request", "Sending POST request to catalog search...")
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
        log_info("action", "_fetch_parent_task", "response_received", f"Response status code: {resp.status_code}")

        resp.raise_for_status()
        log_info("action", "_fetch_parent_task", "status_check_passed", "HTTP status check passed")

        data = resp.json()
        log_info("action", "_fetch_parent_task", "response_data", f"Response data: {data}")

        if data and isinstance(data, dict):
            log_info("action", "_fetch_parent_task", "data_is_dict", "Response is a valid dictionary")

            if "items" in data:
                log_info("action", "_fetch_parent_task", "items_found", f"Items array found with {len(data['items'])} items")

                if data["items"]:
                    first_item = data["items"][0]
                    log_info("action", "_fetch_parent_task", "returning_first_item", f"Returning first item: {first_item}")
                    return first_item
                else:
                    log_info("action", "_fetch_parent_task", "items_empty", "Items array is empty")
            else:
                log_info("action", "_fetch_parent_task", "no_items_key", "No 'items' key in response data")
        else:
            log_info("action", "_fetch_parent_task", "invalid_data", f"Response data is not a valid dict: type={type(data)}")

        log_info("action", "_fetch_parent_task", "returning_none", "No valid parent task found, returning None")
        return None

    except requests.exceptions.HTTPError as e:
        log_error("action", "_fetch_parent_task", "http_error", f"HTTP error fetching parent: {str(e)}")
        return None
    except requests.exceptions.RequestException as e:
        log_error("action", "_fetch_parent_task", "request_exception", f"Request exception fetching parent: {str(e)}")
        return None
    except Exception as e:
        log_error("action", "_fetch_parent_task", "unexpected_exception", f"Unexpected exception fetching parent: {str(e)}")
        return None


def _fetch_current_task(task_laui: str, auth_token: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
    """Fetch current task details from catalog get API."""
    log_info("action", "_fetch_current_task", "start", f"Fetching current task with laui: {task_laui}")

    try:
        url = f"http://backend-test:8000/api/v1/catalog/get?item_laui={task_laui}"
        log_info("action", "_fetch_current_task", "url", f"API URL: {url}")

        headers = {
            "Cookie":f"frontend_token={auth_token}",
            "Content-Type": "application/json"
        }
        log_info("action", "_fetch_current_task", "headers", "Headers prepared")

        log_info("action", "_fetch_current_task", "sending_request", "Sending GET request...")
        resp = requests.get(url, headers=headers, timeout=timeout)
        log_info("action", "_fetch_current_task", "response_received", f"Response status code: {resp.status_code}")

        resp.raise_for_status()
        log_info("action", "_fetch_current_task", "status_check_passed", "HTTP status check passed")

        data = resp.json()
        log_info("action", "_fetch_current_task", "response_data", f"Response data: {data}")

        return data

    except requests.exceptions.HTTPError as e:
        log_error("action", "_fetch_current_task", "http_error", f"HTTP error: {str(e)}")
        return None
    except requests.exceptions.RequestException as e:
        log_error("action", "_fetch_current_task", "request_exception", f"Request exception: {str(e)}")
        return None
    except Exception as e:
        log_error("action", "_fetch_current_task", "unexpected_exception", f"Unexpected exception: {str(e)}")
        return None


def run(
    least_action_action_object: Dict[str, Any],
    parents: List[Dict[str, Any]]
) -> bool:
    """
    Validates parent tasks have state 'success' AND validates that parent ran at or after
    the expected scheduled time derived from cron frequencies.

    Timing validation is ALWAYS performed and cannot be skipped.

    Parameters:
        least_action_action_object (dict): action object containing 'user_access_token', 'task_laui', etc.
        parents (list): list of parent descriptors each containing: task_name, project_laui, account_laui, partition

    Returns:
        bool: True if all parents pass validation (state AND timing), False otherwise
    """
    separator = "=" * 80
    log_info("action", "run", "function_entry", separator)
    log_info("action", "run", "function_entry", "ENTERING run() FUNCTION")
    log_info("action", "run", "function_entry", separator)

    action_id = least_action_action_object.get('laui', 'na')
    session_id = least_action_action_object.get('session_id', 'na')
    log_info("action", "run", "action_metadata", f"Action ID: {action_id}")
    log_info("action", "run", "action_metadata", f"Session ID: {session_id}")

    try:
        log_info("action", "run", "start", f"Starting parent task validation (STATE + TIMING) | action: {action_id} | session: {session_id}")
        log_info("action", "run", "input_params", f"Number of parents to check: {len(parents)}")
        log_info("action", "run", "input_params", f"Parents list: {parents}")

        # Extract auth token
        log_info("action", "run", "auth_check", "Attempting to extract auth token from least_action_action_object")
        auth_token = least_action_action_object.get('user_access_token')

        if not auth_token:
            log_error("action", "run", "missing_auth_token", "VALIDATION FAILED: Authorization token not found in least_action_action_object")
            log_error("action", "run", "missing_auth_token", f"Available keys: {list(least_action_action_object.keys())}")
            log_error("action", "run", "failure_reason", "Cannot proceed without authentication token")
            log_info("action", "run", "return_false", "RETURNING FALSE - missing auth token")
            return False

        log_info("action", "run", "auth_token_found", "Authorization token retrieved successfully")
        log_info("action", "run", "auth_token_found", f"Token length: {len(auth_token)} characters")

        # Check if parents list is empty
        if not parents:
            log_info("action", "run", "no_parents", "No parents to check - passing by default")
            log_info("action", "run", "return_true", "RETURNING TRUE - no parents to validate")
            return True

        log_info("action", "run", "parents_present", f"Found {len(parents)} parent(s) to validate")

        # Initialize timing validation variables
        now = datetime.now()
        log_info("action", "run", "current_time", f"Current time (now): {now.isoformat()}")

        # Fetch current task (REQUIRED for timing validation)
        task_object = least_action_action_object.get('task',{})
        task_laui = task_object.get('laui')
        log_info("action", "run", "task_laui_check", f"task_laui from action object: {task_laui}")

        if not task_laui:
            log_error("action", "run", "missing_task_laui", "VALIDATION FAILED: task_laui not provided in action object")
            log_error("action", "run", "missing_task_laui", "Available keys: " + str(list(least_action_action_object.keys())))
            log_error("action", "run", "failure_reason", "Timing validation requires task_laui but it was not found")
            log_info("action", "run", "return_false", "RETURNING FALSE - missing task_laui")
            return False

        log_info("action", "run", "fetch_current_task", f"Fetching current task for laui: {task_laui}")

        current_task = _fetch_current_task(task_laui, auth_token)
        log_info("action", "run", "fetch_current_task_result", f"Fetch result: {current_task}")

        if not current_task or not isinstance(current_task, dict):
            log_error("action", "run", "current_task_fetch_failed", "VALIDATION FAILED: Failed to fetch current task or result is not valid")
            log_error("action", "run", "current_task_fetch_failed", f"Type: {type(current_task)}, Value: {current_task}")
            log_error("action", "run", "failure_reason", "Cannot perform timing validation without current task details")
            log_info("action", "run", "return_false", "RETURNING FALSE - current task fetch failed")
            return False

        log_info("action", "run", "current_task_valid", "Current task fetched successfully")
        log_info("action", "run", "current_task_name", f"Current task name: {current_task.get('name', 'unnamed')}")

        child_frequency = current_task.get('frequency')
        log_info("action", "run", "child_frequency", f"Child task frequency: {child_frequency}")

        if not child_frequency or child_frequency == 'ADHOC':
            log_error("action", "run", "invalid_child_frequency", "VALIDATION FAILED: Child frequency is missing or ADHOC")
            log_error("action", "run", "invalid_child_frequency", f"Frequency value: {child_frequency}")
            log_error("action", "run", "failure_reason", "Timing validation requires valid cron frequency, but child task has ADHOC or missing frequency")
            log_info("action", "run", "return_false", "RETURNING FALSE - invalid child frequency")
            return False

        log_info("action", "run", "child_frequency_valid", f"Child frequency is valid: {child_frequency}")

        # Compute child's scheduled run time
        try:
            log_info("action", "run", "computing_child_run_time", "Computing child's scheduled run time...")
            child_run_time = _prev_cron_time(child_frequency, now)
            log_info("action", "run", "child_run_time", f"Child scheduled run time: {child_run_time.isoformat()}")
            log_info("action", "run", "child_run_time_ts", f"Child scheduled run time (timestamp): {child_run_time.timestamp()}")
        except Exception as e:
            log_error("action", "run", "child_cron_invalid", f"VALIDATION FAILED: Invalid child cron expression '{child_frequency}'")
            log_error("action", "run", "child_cron_invalid", f"Error: {str(e)}")
            log_error("action", "run", "failure_reason", "Cannot compute child's scheduled run time due to invalid cron expression")
            log_info("action", "run", "return_false", "RETURNING FALSE - child cron error")
            return False

        # Validate each parent
        separator = "=" * 60
        log_info("action", "run", "parent_loop_start", separator)
        log_info("action", "run", "parent_loop_start", "STARTING PARENT VALIDATION LOOP")
        log_info("action", "run", "parent_loop_start", separator)

        for idx, parent_info in enumerate(parents, start=1):
            parent_name = parent_info.get('task_name', 'unnamed_parent')
            log_info("action", "run", "parent_iteration", "\\n" + separator)
            log_info("action", "run", "parent_iteration", "PARENT %d of %d" % (idx, len(parents)))
            log_info("action", "run", "parent_iteration", separator)

            try:
                log_info("action", "run", "evaluating_parent", f"[{idx}/{len(parents)}] Evaluating parent: {parent_name}")
                log_info("action", "run", "parent_descriptor", f"Parent descriptor: {parent_info}")

                # Fetch parent task
                log_info("action", "run", "fetch_parent", f"Calling _fetch_parent_task for: {parent_name}")
                parent_task = _fetch_parent_task(parent_info, auth_token)
                log_info("action", "run", "fetch_parent_result", f"Fetch result: {parent_task}")

                if not parent_task:
                    log_error("action", "run", "parent_fetch_failed", f"VALIDATION FAILED: Failed to fetch parent task: {parent_name}")
                    log_error("action", "run", "parent_fetch_failed", "Parent task not found in catalog search")
                    log_error("action", "run", "failure_reason", f"Parent task '{parent_name}' does not exist or is inaccessible")
                    log_info("action", "run", "return_false", f"RETURNING FALSE - parent {parent_name} not found")
                    return False

                log_info("action", "run", "parent_fetched", f"Parent task fetched successfully: {parent_name}")
                log_info("action", "run", "parent_full_data", f"Full parent data: {parent_task}")

                # Check parent state
                log_info("action", "run", "checking_state", "Extracting parent state...")
                parent_state_raw = parent_task.get('state')
                log_info("action", "run", "state_raw", f"Parent state (raw): '{parent_state_raw}' (type: {type(parent_state_raw)})")

                parent_state = (parent_state_raw or '').strip().lower()
                log_info("action", "run", "parent_state", f"Parent '{parent_name}' state (normalized): '{parent_state}'")

                if parent_state != 'success':
                    log_error("action", "run", "parent_state_not_success", f"VALIDATION FAILED: Parent '{parent_name}' state is '{parent_state}', expected 'success'")
                    log_error("action", "run", "parent_state_not_success", f"State comparison: '{parent_state}' != 'success'")
                    log_error("action", "run", "failure_reason", f"Parent task '{parent_name}' must be in 'success' state before child can run")
                    log_info("action", "run", "return_false", f"RETURNING FALSE - parent {parent_name} state is not success")
                    return False

                log_info("action", "run", "parent_state_success", "[PASS] Parent '{}' state is 'success'".format(parent_name))

                # Timing validation (ALWAYS performed)
                log_info("action", "run", "timing_validation_start", f"Starting timing validation for parent: {parent_name}")

                parent_frequency = parent_task.get('frequency')
                parent_last_run = parent_task.get('last_run_date')

                log_info("action", "run", "parent_frequency", f"Parent frequency: {parent_frequency}")
                log_info("action", "run", "parent_last_run", f"Parent last_run_date: {parent_last_run}")

                if not parent_frequency or parent_frequency == 'ADHOC':
                    log_error("action", "run", "parent_frequency_invalid", f"VALIDATION FAILED: Parent '{parent_name}' has ADHOC or missing frequency")
                    log_error("action", "run", "parent_frequency_invalid", f"Frequency value: {parent_frequency}")
                    log_error("action", "run", "failure_reason", f"Parent task '{parent_name}' must have valid cron frequency for timing validation")
                    log_info("action", "run", "return_false", f"RETURNING FALSE - parent {parent_name} has invalid frequency")
                    return False

                if not parent_last_run:
                    log_error("action", "run", "parent_no_last_run", f"VALIDATION FAILED: Parent '{parent_name}' has no recorded last run date")
                    log_error("action", "run", "parent_no_last_run", "last_run_date field is missing or null")
                    log_error("action", "run", "failure_reason", f"Parent task '{parent_name}' must have completed at least one run")
                    log_info("action", "run", "return_false", f"RETURNING FALSE - parent {parent_name} has no last_run_date")
                    return False

                try:
                    log_info("action", "run", "compute_expected_parent_run", f"Computing expected parent run time using child_run_time: {child_run_time.isoformat()}")
                    log_info("action", "run", "compute_expected_parent_run", f"Parent cron expression: {parent_frequency}")

                    expected_parent_run_time = _prev_cron_time(parent_frequency, child_run_time)
                    log_info("action", "run", "expected_parent_run", f"Expected parent run time: {expected_parent_run_time.isoformat()}")
                    log_info("action", "run", "expected_parent_run_ts", f"Expected parent run time (timestamp): {expected_parent_run_time.timestamp()}")

                    log_info("action", "run", "parse_parent_last_run", f"Parsing parent last_run_date: {parent_last_run}")
                    parent_last_run_dt = isoparse(parent_last_run).replace(microsecond=0)
                    log_info("action", "run", "parsed_parent_last_run", f"Parsed parent last_run_date: {parent_last_run_dt.isoformat()}")
                    log_info("action", "run", "parsed_parent_last_run_ts", f"Parsed parent last_run_date (timestamp): {parent_last_run_dt.timestamp()}")

                    expected_ts = expected_parent_run_time.timestamp()
                    actual_ts = parent_last_run_dt.timestamp()

                    log_info("action", "run", "timing_comparison", f"Parent '{parent_name}' timing comparison:")
                    log_info("action", "run", "timing_comparison", f"  Expected: {expected_parent_run_time.isoformat()} ({expected_ts})")
                    log_info("action", "run", "timing_comparison", f"  Actual:   {parent_last_run_dt.isoformat()} ({actual_ts})")
                    log_info("action", "run", "timing_comparison", f"  Difference (seconds): {actual_ts - expected_ts}")

                    if actual_ts >= expected_ts:
                        log_info("action", "run", "timing_pass", "[PASS] Parent '{}' ran at or after expected time".format(parent_name))
                        log_info("action", "run", "timing_pass", f"  {actual_ts} >= {expected_ts} is TRUE")
                    else:
                        log_error("action", "run", "timing_fail", f"VALIDATION FAILED: Parent '{parent_name}' last run is before expected scheduled time")
                        log_error("action", "run", "timing_fail", f"  Expected: {expected_parent_run_time.isoformat()}")
                        log_error("action", "run", "timing_fail", f"  Actual:   {parent_last_run_dt.isoformat()}")
                        log_error("action", "run", "timing_fail", f"  Parent ran {expected_ts - actual_ts} seconds too early")
                        log_error("action", "run", "failure_reason", f"Parent task '{parent_name}' must complete its scheduled run before child can execute")
                        log_info("action", "run", "return_false", f"RETURNING FALSE - parent {parent_name} timing validation failed")
                        return False

                except Exception as e:
                    log_error("action", "run", "timing_validation_error", f"VALIDATION FAILED: Error during timing validation for '{parent_name}'")
                    log_error("action", "run", "timing_validation_error", f"Error: {str(e)}")
                    log_error("action", "run", "failure_reason", f"Could not validate timing for parent task '{parent_name}' due to technical error")
                    log_info("action", "run", "return_false", f"RETURNING FALSE - timing validation exception for {parent_name}")
                    return False

            except Exception as e:
                log_error("action", "run", "parent_evaluation_error", f"VALIDATION FAILED: Error evaluating parent '{parent_name}'")
                log_error("action", "run", "parent_evaluation_error", f"Error: {str(e)}")
                log_error("action", "run", "failure_reason", f"Unexpected error while processing parent task '{parent_name}'")
                log_info("action", "run", "return_false", f"RETURNING FALSE - exception while evaluating {parent_name}")
                return False

        log_info("action", "run", "parent_loop_end", separator)
        log_info("action", "run", "parent_loop_end", "COMPLETED PARENT VALIDATION LOOP")
        log_info("action", "run", "parent_loop_end", separator)

        log_info("action", "run", "complete_success", "All parent tasks passed validation: SUCCESS state AND correct timing")
        log_info("action", "run", "return_true", "RETURNING TRUE - all validations passed")
        return True

    except Exception as e:
        log_error("action", "run", "unexpected_error", f"VALIDATION FAILED: Unexpected error in run function")
        log_error("action", "run", "unexpected_error", f"Exception type: {type(e).__name__}")
        log_error("action", "run", "unexpected_error", f"Error message: {str(e)}")
        log_error("action", "run", "failure_reason", "Critical error during parent task validation process")
        log_info("action", "run", "return_false", "RETURNING FALSE - unexpected exception")
        return False
'''
}

action_variables = {
    "parents": [
        {
            "task_name": "parent_task_name_example",
            "project_laui": "project_laui_example",
            "account_laui": "account_laui_example",
            "partition": "ALL",
        }
    ]
}
connection = {}
