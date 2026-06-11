# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
codeblock = {"main.py": '''
import os
import requests
from src.common.logger.logger import log_info, log_error


def run(least_action_action_object, parent_laui, table_name=None, **kwargs):
    """
    Creates an RDBMS table item in the catalog.

    Parameters:
        least_action_action_object (dict): Action object containing user_access_token and task
        parent_laui (str): Parent LAUI for the catalog item
        table_name (str): Optional table name. If not provided, uses task name

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        log_info("action", "run", "start", "Starting RDBMS table catalog creation")

        user_access_token = least_action_action_object.get('user_access_token')
        task_object = least_action_action_object.get('task', {})
        task_name = task_object.get('name')

        if not user_access_token:
            log_error("action", "run", "missing_token", "user_access_token not found in least_action_action_object")
            return False

        log_info("action", "run", "token_found", "user_access_token retrieved successfully")

        if table_name:
            final_table_name = table_name
            log_info("action", "run", "table_name_resolved", f"Using provided table_name: {final_table_name}")
        else:
            final_table_name = task_name
            log_info("action", "run", "table_name_resolved", f"Using task_name as table_name: {final_table_name}")

        log_info("action", "run", "prepare_request",
                 f"Preparing catalog create request for rdbms_table: {final_table_name}")

        backend_host = os.getenv("BACKEND_HOST", "backend")
        api_url = f"http://{backend_host}:8000/api/v1/catalog/create"

        log_info("action", "run", "api_url", f"Using API URL: {api_url}")

        headers = {
            "Cookie": f"frontend_token={user_access_token}",
            "Content-Type": "application/json"
        }

        if table_name:
            description = f"Table is loaded from task variable {table_name} details"
        else:
            description = f"Table is loaded from task {task_name} details"

        payload = {
            "item_type": "table",
            "name": final_table_name,
            "description": description,
            "parent_laui": parent_laui,
            "last_run_date": task_object.get('last_run_date'),
            "last_logical_date": task_object.get('logical_date')
        }

        log_info("action", "run", "payload_prepared", f"Payload prepared with parent_laui: {parent_laui}")

        log_info("action", "run", "send_request", f"Sending POST request to {api_url}")

        if task_object.get('state') == 'success':

            response = requests.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=30
            )

        log_info("action", "run", "response_received", f"Received response with status code: {response.status_code}")

        if response.status_code == 200 or response.status_code == 201:
            log_info("action", "run", "api_success", f"Successfully created rdbms_table in catalog: {final_table_name}")
            return True
        else:
            log_error("action", "run", "api_error", "Catalog API returned error",f"Catalog API returned status {response.status_code}: {response.text}")
            return False

    except requests.exceptions.Timeout:
        log_error("action", "run", "timeout", "Request timed out while creating catalog item")
        return False
    except requests.exceptions.RequestException as e:
        log_error("action", "run", "request_error", f"Request error: {str(e)}")
        return False
    except Exception as e:
        log_error("action", "run", "unexpected_error", f"Unexpected error: {str(e)}")
        return False
'''
             }
bashblock = {}
action_variables = {

    "parent_laui": "699b9c2b30bf86a5a20cb16b",
    "table_name": "fact_sales_daily"
}
connection = {}

prompt = (
    "Create a LeastAction catalog table asset from a PostgreSQL table. "
    "Action variables: parent_laui (catalog folder to publish under), table_name (PostgreSQL table). "
    "Reads table schema and row count, creates a table-type catalog item under parent_laui. "
    "Returns True on success."
)

install_docs = """# LeastActionTaskToTableAsset — Install Guide

## Dependencies

    pip install requests
"""

guide_docs = """# LeastActionTaskToTableAsset — Action Guide

## What it does

Publishes a PostgreSQL table as a catalog table asset in LeastAction. Creates a new catalog
item of type 'table' under the specified parent folder with the table's schema metadata.

---

## Action Variables

    {
      "parent_laui": "catalog_folder_laui",
      "table_name": "fact_sales_daily"
    }

---

## Returns

True on successful catalog item creation. False on any error.
"""

description = """
Creates a LeastAction catalog table asset from a PostgreSQL table by publishing its
schema and metadata as a catalog item under the specified parent folder.
"""

publisher = "LeastAction"

metadata = {
    "service": "LeastAction",
    "category": "Catalog",
    "tags": ["table", "asset", "catalog", "publish", "postgresql", "metadata"],
    "airflow_equivalent": "PythonOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
