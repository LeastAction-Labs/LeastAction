# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
bashblock= {
"install_dependencies.sh": "pip install requests",
}
codeblock= {"main.py":
"""
import requests
import json
from src.common.logger.logger import log_info, log_error


def run(least_action_action_object, task_lauis, **kwargs):
    try:
        log_info("action", "run", "start", f"Starting task update for tasks: {task_lauis}")

        user_access_token = least_action_action_object.get('user_access_token')

        if not user_access_token:
            log_error("action", "run", "missing_token", "user_access_token not found in least_action_action_object")
            return False

        # Use backend-test for test environment, backend for production
        import os
        backend_host = os.getenv("BACKEND_HOST", "backend")
        base_api_url = f"http://{backend_host}:8000/api/v1"
        get_api_url = base_api_url + "/catalog/get"
        post_api_url = base_api_url + "/task"
        headers = {
            "Cookie": f"frontend_token={user_access_token}",
            "Content-Type": "application/json"
        }
        for task_laui in task_lauis:
            task_get_response = requests.get(
                get_api_url,
                params={"item_laui":task_laui},
                headers=headers
            )
            task_get_response.raise_for_status()
            task = task_get_response.json()
            task["user_set_state"]="cancel"
            task_post_response = requests.post(
                post_api_url,
                json=task,
                headers=headers
            )
            print(task_post_response.json())
            task_post_response.raise_for_status()
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
"""
}
action_variables={
   "task_lauis":[]
}
connection={}

prompt = (
    "Cancel one or more LeastAction tasks by setting user_set_state to 'cancel'. "
    "Action variable: task_lauis (list of task LAUIs to cancel). "
    "Fetches each task via GET /api/v1/catalog/get, sets user_set_state=cancel, "
    "then POSTs to /api/v1/task. Returns True if all tasks were cancelled successfully."
)

install_docs = """# LeastActionCancelTask — Install Guide

## Dependencies

    pip install requests

## Setup

No additional setup required. The action uses the LeastAction internal API with the
user_access_token from the action object (injected automatically by the executor).
"""

guide_docs = """# LeastActionCancelTask — Action Guide

## What it does

Cancels one or more running or queued LeastAction tasks by updating their user_set_state
to 'cancel'. Useful for stopping dependent tasks when a parent pipeline fails or when
a workflow needs to be aborted mid-run.

---

## Action Variables

    {"task_lauis": ["laui_1", "laui_2"]}

| Field      | Required | Description                    |
|------------|----------|--------------------------------|
| task_lauis | Yes      | List of task LAUIs to cancel   |

---

## Connection

Not required (empty dict). Uses user_access_token from the action object.

---

## Returns

True if all tasks were cancelled successfully. False on any error.
"""

description = """
Cancels one or more LeastAction tasks by setting their user_set_state to 'cancel' via the
internal task update API. Iterates over the task_lauis list, fetches each task, and posts
the cancel update. Returns True on success, False on any failure.
"""

publisher = "LeastAction"

metadata = {
    "service": "LeastAction",
    "category": "Workflow",
    "tags": ["cancel", "task", "workflow", "control", "leastaction"],
    "airflow_equivalent": "PythonOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
