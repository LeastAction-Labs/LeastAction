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
import os
from src.common.logger.logger import log_info, log_error


def run(least_action_action_object, item_lauis, parent_laui=None, hard_delete=False, **kwargs):
    """
    Delete one or more catalog items via the catalog delete API.

    Parameters:
        least_action_action_object (dict): action object containing 'user_access_token'.
        item_lauis (list[str]): LAUIs of items to delete.
        parent_laui (str | None): Optional parent LAUI context for the delete operation.
        hard_delete (bool): If True, permanently removes the item; if False (default), soft-deletes it.

    Returns:
        bool: True if all items were successfully deleted, False otherwise.
    """
    separator = "=" * 80
    log_info("action", "run", "function_entry", separator)
    log_info("action", "run", "function_entry", "ENTERING run() FUNCTION - LeastActionDeleteItems")
    log_info("action", "run", "function_entry", separator)

    try:
        log_info("action", "run", "start", f"Starting delete for items: {item_lauis}")
        log_info("action", "run", "input_params", f"parent_laui={parent_laui}, hard_delete={hard_delete}")

        user_access_token = least_action_action_object.get('user_access_token')

        if not user_access_token:
            log_error("action", "run", "missing_token", "user_access_token not found in action object")
            return False

        log_info("action", "run", "auth_ok", "Auth token found")

        if not item_lauis:
            log_error("action", "run", "empty_item_lauis", "item_lauis list is empty — nothing to delete")
            return False

        log_info("action", "run", "item_count", f"Number of items to delete: {len(item_lauis)}")

        backend_host = os.getenv("BACKEND_HOST", "backend")
        base_api_url = f"http://{backend_host}:8000/api/v1"
        delete_api_url = base_api_url + "/catalog/delete"

        log_info("action", "run", "urls", f"delete_api_url={delete_api_url}")

        headers = {
            "Cookie": f"frontend_token={user_access_token}",
            "Content-Type": "application/json"
        }

        for idx, item_laui in enumerate(item_lauis, start=1):
            log_info("action", "run", "item_iteration", separator[:60])
            log_info("action", "run", "item_iteration", f"ITEM {idx} of {len(item_lauis)}: {item_laui}")
            log_info("action", "run", "item_iteration", separator[:60])

            body = {
                "item_laui": item_laui,
                "hard_delete": hard_delete,
            }
            if parent_laui is not None:
                body["parent_laui"] = parent_laui

            log_info("action", "run", "delete_request", f"Sending delete request for item {item_laui} (hard_delete={hard_delete})...")
            delete_resp = requests.post(
                delete_api_url,
                json=body,
                headers=headers,
                timeout=30,
            )
            log_info("action", "run", "delete_status", f"POST catalog/delete status: {delete_resp.status_code}")
            delete_resp.raise_for_status()
            log_info("action", "run", "delete_ok", f"[DONE] Item {item_laui} deleted successfully")

        log_info("action", "run", "complete_success", f"All {len(item_lauis)} item(s) deleted successfully")
        log_info("action", "run", "return_true", "RETURNING TRUE")
        return True

    except requests.exceptions.Timeout:
        log_error("action", "run", "timeout", "Request timed out while calling catalog delete API")
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
    "item_lauis": []
}
connection = {}

prompt = (
    "Delete one or more LeastAction catalog items by LAUI. "
    "Action variable: item_lauis (list of LAUIs to delete). "
    "Calls DELETE /api/v1/catalog/delete for each item using user_access_token. "
    "Returns True if all items were deleted successfully. "
    "Handles items that may already be deleted (idempotent on 404)."
)

install_docs = """# LeastActionDeleteItems — Install Guide

## Dependencies

    pip install requests
"""

guide_docs = """# LeastActionDeleteItems — Action Guide

## What it does

Deletes one or more LeastAction catalog items by LAUI. Useful for cleanup operations,
removing temporary assets, or managing lifecycle of catalog entries.

---

## Action Variables

    {"item_lauis": ["laui_1", "laui_2"]}

---

## Returns

True if all items deleted successfully. False on any error.
"""

description = """
Deletes one or more LeastAction catalog items by LAUI via the catalog delete API.
Iterates over item_lauis and calls DELETE for each. Returns True on success.
"""

publisher = "LeastAction"

metadata = {
    "service": "LeastAction",
    "category": "Catalog",
    "tags": ["delete", "catalog", "items", "cleanup", "leastaction"],
    "airflow_equivalent": "PythonOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

