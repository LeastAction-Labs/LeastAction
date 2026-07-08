# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.

import requests

from src.common.logger.logger import log_error, log_info


def run(
    least_action_action_object,
    item_type,
    task_laui,
    name,
    project_laui,
    account_laui,
    parent_laui,
    operator_laui,
    connection_laui,
    user_set_state,
):
    """
    Updates a task in the catalog to set its user_set_state (typically for cancellation).

    Parameters:
        least_action_action_object (dict): Action object containing user_access_token and metadata
        item_type (str): Type of item (should be 'task')
        task_laui (str): Task LAUI identifier to update
        name (str): Name of the task
        project_laui (str): Project LAUI identifier
        account_laui (str): Account LAUI identifier
        parent_laui (str): Parent LAUI identifier
        operator_laui (str): Operator LAUI identifier
        connection_laui (str): Connection LAUI identifier
        user_set_state (str): User set state for the task (e.g., "cancel")

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        log_info("action", "run", "start", f"Starting task update for task: {task_laui}")

        user_access_token = least_action_action_object.get("user_access_token")

        if not user_access_token:
            log_error(
                "action",
                "run",
                "missing_token",
                "user_access_token not found in least_action_action_object",
            )
            return False

        log_info(
            "action",
            "run",
            "prepare_request",
            f"Preparing update request for task: {name} with user_set_state={user_set_state}",
        )

        # Use backend-test for test environment, backend for production
        import os

        backend_host = os.getenv("BACKEND_HOST", "backend-test")
        api_url = f"http://{backend_host}:8000/api/v1/task"

        headers = {
            "Cookie": f"frontend_token={user_access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "item_type": item_type,
            "name": name,
            "project_laui": project_laui,
            "account_laui": account_laui,
            "parent_laui": parent_laui,
            "operator_laui": operator_laui,
            "connection_laui": connection_laui,
            "user_set_state": user_set_state,
        }

        log_info("action", "run", "send_request", f"Sending POST request to {api_url}")

        response = requests.post(api_url, json=payload, headers=headers, timeout=30)

        log_info(
            "action", "run", "response_received", f"Response status code: {response.status_code}"
        )

        if response.status_code in [200, 201]:
            log_info(
                "action", "run", "success", f"Task updated successfully. Response: {response.text}"
            )
            return True
        else:
            log_error(
                "action",
                "run",
                "api_error",
                f"API returned status {response.status_code}. Response: {response.text}",
            )
            return False

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
bashblock:{}
action_variables: {
  "item_type": "task",
  "task_laui": "",
  "name": "",
  "project_laui": "",
  "account_laui": "",
  "parent_laui": "",
  "operator_laui": "",
  "connection_laui": "",
  "user_set_state": ""
}

"""
