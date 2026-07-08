# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
bashblock = {'install_dependencies.sh': 'pip install requests'}

codeblock = {'main.py': 'import requests\n'
                'import os\n'
                'from src.common.logger.logger import log_info, log_error\n'
                '\n'
                '\n'
                'def run(least_action_action_object, task_laui, **kwargs):\n'
                '    """\n'
                '    Runs the specified task using the LeastAction API.\n'
                '    Uses user_access_token for auth (same pattern as LeastActionCancel).\n'
                '\n'
                '    Parameters:\n'
                '        least_action_action_object (dict): Action object with session_id, '
                'connection, task, etc.\n'
                '        task_laui (str): LAUI of the task to run\n'
                '\n'
                '    Returns:\n'
                '        bool: True if successful, False otherwise\n'
                '    """\n'
                '    try:\n'
                '        log_info("action", "run", "start", "Starting task execution")\n'
                '\n'
                "        user_access_token = least_action_action_object.get('user_access_token')\n"
                '        if not user_access_token:\n'
                '            log_error("action", "run", "missing_token", "user_access_token not '
                'found in least_action_action_object")\n'
                '            return False\n'
                '\n'
                '        if not task_laui:\n'
                '            log_error("action", "run", "validate_inputs", "Target task LAUI not '
                'provided")\n'
                '            return False\n'
                '\n'
                '        backend_host = os.getenv("BACKEND_HOST", "backend")\n'
                '        base_api_url = f"http://{backend_host}:8000/api/v1"\n'
                '\n'
                '        headers = {\n'
                '            "Cookie": f"frontend_token={user_access_token}",\n'
                '            "Content-Type": "application/json"\n'
                '        }\n'
                '\n'
                '        log_info("action", "run", "run_target_task", f"Attempting to run target '
                'task: {task_laui}")\n'
                '\n'
                '        run_url = base_api_url + "/task"\n'
                '        run_payload = {\n'
                '            "item_type": "task",\n'
                '            "item_laui": task_laui\n'
                '        }\n'
                '        run_response = requests.post(\n'
                '            run_url,\n'
                '            json=run_payload,\n'
                '            headers=headers,\n'
                '            timeout=30\n'
                '        )\n'
                '\n'
                '        if run_response.status_code not in [200, 201, 202]:\n'
                '            log_error("action", "run", "run_target_task",\n'
                '                      f"Failed to run task. Status: {run_response.status_code}, '
                'Response: {run_response.text}")\n'
                '            return False\n'
                '\n'
                '        log_info("action", "run", "run_target_task", f"Successfully triggered '
                'task: {task_laui}")\n'
                '        log_info("action", "run", "complete", "Task execution triggered '
                'successfully")\n'
                '        return True\n'
                '\n'
                '    except requests.exceptions.Timeout:\n'
                '        log_error("action", "run", "timeout", "Request timed out while running '
                'task")\n'
                '        return False\n'
                '    except requests.exceptions.RequestException as e:\n'
                '        log_error("action", "run", "request_error", f"Request error: {str(e)}")\n'
                '        return False\n'
                '    except Exception as e:\n'
                '        log_error("action", "run", "unexpected_error", f"Unexpected error: '
                '{str(e)}")\n'
                '        return False\n'}

action_variables = {'task_laui': 'task_laui_value'}

connection = {'api_key': '', 'base_url': 'http://localhost:8000'}

prompt = (
    "Trigger execution of a LeastAction task by LAUI. "
    "Action variable: task_laui (the LAUI of the task to run). "
    "POSTs to /api/v1/task/{task_laui} using user_access_token. "
    "Returns True on successful trigger, False on any error."
)

install_docs = """# LeastActionRunTask — Install Guide

## Dependencies

    pip install requests
"""

guide_docs = """# LeastActionRunTask — Action Guide

## What it does

Triggers execution of a LeastAction task by calling the run endpoint. Useful for
programmatically starting downstream tasks, re-running failed tasks, or building
dynamic task chains.

---

## Action Variables

    {"task_laui": "abc123laui"}

---

## Returns

True if the task was triggered successfully. False on any error.
"""

description = """
Triggers a LeastAction task execution via the internal run API. Accepts a task LAUI
and POSTs to the task run endpoint using the executor's user_access_token.
Returns True on success.
"""

publisher = "LeastAction"

metadata = {
    "service": "LeastAction",
    "category": "Workflow",
    "tags": ["run", "task", "trigger", "execute", "leastaction"],
    "airflow_equivalent": "TriggerDagRunOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
