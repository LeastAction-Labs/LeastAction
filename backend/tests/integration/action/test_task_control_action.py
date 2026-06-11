# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import asyncio
import time
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.core.catalog.api_request import CreateItemResponse, GetItemsFilter
from src.core.catalog.orchestrator import ItemOrchestrator
from src.core.db.types import MongoDatabase
from src.core.task.connection.schema import SortOrder
from tests.integration.schema import BaseFolders, TestRequest
from tests.integration.utils import create_base_folders, execute_request, get_item_orchestrator

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def database_cleanup(test_database: MongoDatabase, client: TestClient):
    await test_database.items.drop()
    await test_database.links.delete_many({})
    yield  # Test runs here
    await test_database.items.drop()
    await test_database.links.drop()


@pytest.fixture(autouse=True)
def base_folders_setup(client: TestClient, database_cleanup):
    base_folders = create_base_folders(client)
    yield base_folders


@pytest.fixture
async def account_laui(base_folders_setup: BaseFolders) -> str:
    return base_folders_setup.account_folder_laui


@pytest.fixture
async def project_laui(base_folders_setup: BaseFolders) -> str:
    return base_folders_setup.project_folder_laui


@pytest.fixture
async def workflow_laui(client: TestClient, project_laui: str, account_laui: str) -> str:
    """Create a workflow folder under the project"""
    wf_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.workflow",
                "name": f"workflow_{datetime.now().timestamp()}",
                "parent_laui": project_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "folder_metadata": {"state": "active"},
            },
        ),
    )
    assert wf_resp.status_code == 200
    return CreateItemResponse(**wf_resp.json()).item_laui


@pytest.fixture
async def operator_laui(
    client: TestClient, workflow_laui: str, account_laui: str, project_laui: str
) -> str:
    """Create a Python operator in the workflow"""
    codeblock = load_operator_code_block()

    op_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "operator.python",
                "name": f"sleep_operator_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "codeblock": {"main.py": codeblock},
                "bashblock": {},
            },
        ),
    )
    assert op_resp.status_code == 200
    return CreateItemResponse(**op_resp.json()).item_laui


@pytest.fixture
async def connection_laui(
    client: TestClient, workflow_laui: str, account_laui: str, project_laui: str
) -> str:
    """Create a Python connection environment"""
    connection_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "connection.python",
                "name": f"python_connection_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "content": {},
                "max_parallelism": 10,
                "sort_dict": {"priority": SortOrder.ASC},
            },
        ),
    )
    assert connection_resp.status_code == 200
    return CreateItemResponse(**connection_resp.json()).item_laui


@pytest.fixture
async def payload_laui(
    client: TestClient, workflow_laui: str, account_laui: str, project_laui: str
) -> str:
    """Create a payload item in the workflow"""
    payload_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "payload.json",
                "name": f"payload_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "content": '{"seconds": 30}',
            },
        ),
    )
    assert payload_resp.status_code == 200
    return CreateItemResponse(**payload_resp.json()).item_laui


@pytest.fixture
async def cancel_action_laui(
    client: TestClient, workflow_laui: str, account_laui: str, project_laui: str
) -> str:
    """Create an action to cancel tasks"""
    action_code_block = load_cancel_action_code_block()

    action_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "action",
                "name": f"cancel_task_action_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "bashblock": {},
                "codeblock": {"main.py": action_code_block},
                "account_laui": account_laui,
                "project_laui": project_laui,
            },
        ),
    )
    assert action_resp.status_code == 200
    return CreateItemResponse(**action_resp.json()).item_laui


@pytest.fixture
async def item_orchestrator(test_database: MongoDatabase):
    async for orchestrator in get_item_orchestrator(test_database):
        yield orchestrator


def load_operator_code_block():
    """Load the sleep operator code"""
    path = Path(__file__)
    codeblock_path = path.parent.parent / "task/celery/task-test-data/sleep_operator.py"
    return codeblock_path.read_text(encoding="utf-8")


def load_cancel_action_code_block():
    """Action to cancel a task by updating its user_set_state to 'cancel'"""
    return '''import requests
import json
from src.common.logger.logger import log_info, log_error


def run(least_action_action_object, item_type, task_laui, name, project_laui, account_laui, parent_laui,
        operator_laui, connection_laui, user_set_state):
    """
    Updates a task in the catalog to set its user_set_state to cancel.

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
        user_set_state (str): User set state for the task (should be "cancel")

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        log_info("action", "run", "start", f"Starting task cancellation for task: {task_laui}")

        user_access_token = least_action_action_object.get('user_access_token')

        if not user_access_token:
            log_error("action", "run", "missing_token", "user_access_token not found in least_action_action_object")
            return False

        log_info("action", "run", "prepare_request", f"Preparing cancel request for task: {name}")

        # Use backend-test for test environment, backend for production
        import os
        backend_host = os.getenv("BACKEND_HOST", "backend-test")
        api_url = f"http://{backend_host}:8000/api/v1/catalog/create"

        headers = {
            "Cookie": f"frontend_token={user_access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "item_type": item_type,
            "item_laui": task_laui,  # Include laui to update existing task
            "name": name,
            "project_laui": project_laui,
            "account_laui": account_laui,
            "parent_laui": parent_laui,
            "operator_laui": operator_laui,
            "connection_laui": connection_laui,
            "user_set_state": user_set_state
        }

        log_info("action", "run", "send_request", f"Sending POST request to {api_url} with user_set_state={user_set_state}")

        response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=30
        )

        log_info("action", "run", "response_received", f"Response status code: {response.status_code}")

        if response.status_code in [200, 201]:
            log_info("action", "run", "success", f"Task updated successfully. Response: {response.text}")
            return True
        else:
            log_error("action", "run", "api_error",
                      f"API returned status {response.status_code}. Response: {response.text}")
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
'''


def create_task(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
    payload_laui: str,
    priority: int = 1,
):
    """Helper function to create a task"""
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "payload_laui": payload_laui,
                "frequency": "ADHOC",
                "priority": priority,
            },
        ),
    )
    assert task_resp.status_code == 200, (
        f"Task creation failed with status {task_resp.status_code}: {task_resp.text}"
    )
    time.sleep(2)
    return CreateItemResponse(**task_resp.json()).item_laui


async def test_cancel_action_updates_task_user_set_state(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
    payload_laui: str,
    cancel_action_laui: str,
    item_orchestrator: ItemOrchestrator,
):
    """
    Test that the cancel action successfully updates a task's user_set_state to 'cancel'.

    This test verifies:
    1. A task can be created
    2. The cancel action can be called with the task details
    3. The action successfully updates the task's user_set_state to 'cancel'
    4. The action returns success (status 200)
    """

    print("\n=== Test: Cancel Action Updates Task user_set_state ===")

    # Step 1: Create a task
    print("\n>>> Creating task...")
    task_laui = create_task(
        client,
        operator_laui,
        connection_laui,
        workflow_laui,
        project_laui,
        account_laui,
        payload_laui,
    )
    print(f"✓ Task created with LAUI: {task_laui}")

    # Get initial task state
    task = await item_orchestrator.get_items(request=GetItemsFilter(item_laui=task_laui))
    print(task)
    initial_user_set_state = task.get("user_set_state")
    print(f"  Initial user_set_state: {initial_user_set_state}")

    # Step 2: Call the cancel action
    print("\n>>> Calling cancel action...")
    action_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/action/run",
            method="post",
            json={
                "item_type": "action",
                "item_laui": cancel_action_laui,
                "action_variables": {
                    "item_type": "task",
                    "task_laui": task_laui,
                    "name": task["name"],
                    "project_laui": project_laui,
                    "account_laui": account_laui,
                    "parent_laui": workflow_laui,
                    "operator_laui": operator_laui,
                    "connection_laui": connection_laui,
                    "user_set_state": "cancel",
                },
            },
        ),
    )

    # Assert action call was successful
    print(f"  Action response status: {action_resp.status_code}")
    print(f"  Action response body: {action_resp.json()}")
    assert action_resp.status_code == 200, (
        f"Action run failed with status {action_resp.status_code}: {action_resp.text}"
    )
    print("✓ Action executed successfully")

    # Step 3: Verify the task was updated
    print("\n>>> Verifying task was updated...")
    await asyncio.sleep(0.5)  # Small delay to ensure update is processed

    # Get updated task via API
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": task_laui}
        ),
    )
    assert get_resp.status_code == 200, f"Get task failed: {get_resp.text}"
    updated_task = get_resp.json()

    updated_user_set_state = updated_task.get("user_set_state")
    print(f"  Updated user_set_state: {updated_user_set_state}")

    # Assert user_set_state was updated to 'cancel'
    assert updated_user_set_state == "cancel", (
        f"Task user_set_state is '{updated_user_set_state}', expected 'cancel'"
    )

    print("\n✓ Test passed: Cancel action successfully updated task user_set_state to 'cancel'")


async def test_cancel_action_with_invalid_task_laui_fail(
    client: TestClient,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
    cancel_action_laui: str,
):
    """
    Test that the cancel action handles invalid task LAUI gracefully.
    """

    print("\n=== Test: Cancel Action with Invalid Task LAUI ===")

    fake_task_laui = "507f1f77bcf86cd799439011"

    print(f"\n>>> Calling cancel action with fake task LAUI: {fake_task_laui}")
    action_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/action/run",
            method="post",
            json={
                "item_type": "action",
                "item_laui": cancel_action_laui,
                "action_variables": {
                    "item_type": "task",
                    "task_laui": fake_task_laui,
                    "name": "fake_task",
                    "project_laui": project_laui,
                    "account_laui": account_laui,
                    "parent_laui": workflow_laui,
                    "operator_laui": fake_task_laui,
                    "connection_laui": fake_task_laui,
                    "user_set_state": "cancel",
                },
            },
        ),
    )

    print(f"  Action response status: {action_resp.status_code}")
    print(f"  Action response: {action_resp.json()}")

    # Action should execute but may return an error or False
    # The important thing is it doesn't crash
    assert action_resp.status_code in [200, 404, 422], (
        f"Unexpected status code: {action_resp.status_code}"
    )

    print("\n✓ Test passed: Action handled invalid LAUI gracefully")
