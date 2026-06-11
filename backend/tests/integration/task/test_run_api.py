# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
"""
Integration tests for the task run API endpoint (/api/v1/task/run).

These tests verify that:
1. Valid tasks can be executed successfully
2. Only tasks (item_type="task") can be executed
3. Task execution validates both creation and execution requirements
4. Proper error handling for invalid requests
5. Task is created and validated before execution

NOTE: The run API creates a task first, then validates task execution.
"""

import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from src.core.catalog.api_request import CreateItemResponse
from src.core.db.types import MongoDatabase
from tests.integration.schema import BaseFolders, TestRequest
from tests.integration.utils import create_base_folders, execute_request

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def database_cleanup(test_database: MongoDatabase, client: TestClient):
    await test_database.items.drop()
    await test_database.links.delete_many({})
    yield  # Test runs here
    await test_database.items.drop()
    await test_database.links.drop()


# ============================================================================
# FIXTURES
# ============================================================================


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
    op_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "operator.python",
                "name": f"python_operator_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "codeblock": {
                    "main.py": "def initialize(self):\n    return {}\ndef run(self, ctx):\n    return {'status': 'ok', 'execution_type': 'sync'}\ndef check_completion(self, ctx, state):\n    return {'status': 'done'}\ndef finish(self, ctx, state, result):\n    return None\n"
                },
                "bashblock": {"main.sh": "echo 'test'"},
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
                "content": {"type": "docker"},
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
                "content": '{"test": "data"}',
            },
        ),
    )
    assert payload_resp.status_code == 200
    return CreateItemResponse(**payload_resp.json()).item_laui


@pytest.fixture
async def file_system_action_laui(
    client: TestClient, action_folder_laui: str, account_laui: str, project_laui: str
) -> str:
    """Create a file system operation action"""

    path = Path(__file__)
    codeblock_path = path.parent / "celery/task-test-data/action_run_code.py"
    if not codeblock_path.exists():
        raise FileNotFoundError(f"Action script not found at {codeblock_path}")
    action_code = codeblock_path.read_text(encoding="utf-8")
    action_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "action",
                "name": "FileSystemOperation.action",
                "parent_laui": action_folder_laui,
                "is_root": False,
                "prompt": "Generate an action that creates a folder, creates a file with content, checks if file exists, and deletes it",
                "codeblock": {"main.py": action_code},
                "bashblock": {},
                "account_laui": account_laui,
                "project_laui": project_laui,
            },
        ),
    )
    assert action_resp.status_code == 200
    return CreateItemResponse(**action_resp.json()).item_laui


@pytest.fixture
async def action_folder_laui(client: TestClient, project_laui: str, account_laui: str) -> str:
    """Create an action folder under the project"""
    folder_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.action",
                "name": f"actions_{datetime.now().timestamp()}",
                "parent_laui": project_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
            },
        ),
    )
    assert folder_resp.status_code == 200
    return CreateItemResponse(**folder_resp.json()).item_laui


# ============================================================================
# SUCCESS CASES
# ============================================================================


async def test_create_action_for_task_execution(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
    file_system_action_laui: str,
):
    test_dir = tempfile.mkdtemp()
    expected_content = "INTEGRATION TEST ::: test_create_action_for_task_execution"
    file_name = "task_test_file.txt"
    file_name2 = "task_test_file2.txt"
    file_path_obj = Path(test_dir) / file_name
    actions_dict = {
        "create_actions": [
            {
                "laui": file_system_action_laui,
                "action_variables": {
                    "folder_path": test_dir,
                    "file_path": file_name,
                    "file_content": expected_content,
                },
            },
            {
                "laui": file_system_action_laui,
                "action_variables": {
                    "folder_path": test_dir,
                    "file_path": file_name2,
                    "file_content": expected_content,
                },
            },
        ],
        "pre_actions": [],
        "running_actions": [],
        "post_actions": [],
    }

    # Trigger Task Execution
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_adhoc_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "actions": actions_dict,  # Passing the actions dictionary here
            },
        ),
    )

    print(f"Task execution response: {task_resp.json()}")
    assert task_resp.status_code == 200

    # Assert folder exists (action creates it)
    folder_path_obj = Path(test_dir)
    assert folder_path_obj.exists(), f"Folder {test_dir} should exist"

    for _ in range(20):  # Increased range for task-overhead
        if file_path_obj.exists():
            assert file_path_obj.read_text(encoding="utf-8") == expected_content
            break
        time.sleep(0.05)


async def test_run_task_with_adhoc_frequency_pass(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test successful task execution with ADHOC frequency.
    ADHOC tasks do not require start_date or end_date.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_adhoc_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )

    print(task_resp.json())
    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None
    assert isinstance(task_data.item_laui, str)


async def test_run_task_with_cron_expression_pass(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test successful task execution with valid cron expression.
    Scheduled tasks with cron require start_date and end_date.
    """
    now = datetime.now(UTC)
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_cron_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "0 * * * *",
                "start_date": now.isoformat(),
                "end_date": (now + timedelta(days=1)).isoformat(),
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None


async def test_run_task_with_payload_as_input_pass(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test successful task execution with payload as direct input string.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_payload_input_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "payload": '{"key": "value", "data": [1, 2, 3]}',
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None


async def test_run_task_with_payload_laui_pass(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    payload_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test successful task execution with payload_laui referencing a payload item.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_payload_laui_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "payload_laui": payload_laui,
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None


async def test_run_task_with_complex_json_payload_pass(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test task execution with complex nested JSON payload.
    """
    complex_payload = {
        "database": {
            "host": "localhost",
            "port": 5432,
            "credentials": {"username": "admin", "password": "secret"},
        },
        "arrays": [1, 2, 3, {"nested": "value"}],
        "flags": {"enabled": True, "retry": False},
    }

    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_complex_payload_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "payload": complex_payload,
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None


async def test_run_existing_task_with_item_laui_adhoc_pass(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test successful execution of an existing task by passing its item_laui.
    First creates a task with ADHOC frequency, then executes it using item_laui.
    """
    # First, create a task
    create_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "task",
                "name": f"existing_task_adhoc_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )
    assert create_resp.status_code == 200
    created_task = CreateItemResponse(**create_resp.json())
    task_laui = created_task.item_laui

    # Now execute the existing task using item_laui
    run_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "item_laui": task_laui,
            },
        ),
    )

    assert run_resp.status_code == 200
    run_data = CreateItemResponse(**run_resp.json())
    assert run_data.item_laui == task_laui


async def test_run_existing_task_with_item_laui_cron_pass(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test successful execution of an existing task with cron frequency by passing its item_laui.
    First creates a task with cron frequency, then executes it using item_laui.
    """
    now = datetime.now(UTC)

    # First, create a task with cron frequency
    create_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "task",
                "name": f"existing_task_cron_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "0 * * * *",
                "start_date": now.isoformat(),
                "end_date": (now + timedelta(days=1)).isoformat(),
            },
        ),
    )
    assert create_resp.status_code == 200
    created_task = CreateItemResponse(**create_resp.json())
    task_laui = created_task.item_laui

    # Now execute the existing task using item_laui
    run_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "item_laui": task_laui,
            },
        ),
    )

    assert run_resp.status_code == 200
    run_data = CreateItemResponse(**run_resp.json())
    assert run_data.item_laui == task_laui


async def test_run_existing_task_with_logical_date_pass(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test successful execution of an existing task with logical_date by passing its item_laui.
    First creates a task, then executes it using item_laui with a specific logical_date.
    Verifies that the logical_date persists when retrieving the task after execution.
    """
    # First, create a task
    create_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "task",
                "name": f"existing_task_logical_date_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )
    assert create_resp.status_code == 200
    created_task = CreateItemResponse(**create_resp.json())
    task_laui = created_task.item_laui

    # Define a specific logical_date to be used for execution
    logical_date = datetime(2024, 6, 15, 10, 30, 0, tzinfo=UTC)

    # Execute the existing task using item_laui with logical_date
    run_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "item_laui": task_laui,
                "logical_date": logical_date.isoformat(),
            },
        ),
    )

    assert run_resp.status_code == 200
    run_data = CreateItemResponse(**run_resp.json())
    assert run_data.item_laui == task_laui

    # Retrieve the task and verify logical_date was set correctly
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": task_laui}
        ),
    )
    assert get_resp.status_code == 200
    task_data = get_resp.json()

    # Assert that the logical_date matches what was passed to /run
    assert "logical_date" in task_data
    assert task_data["logical_date"] is not None
    # Parse the returned datetime string and compare with the expected value
    returned_logical_date = datetime.fromisoformat(task_data["logical_date"].replace("Z", "+00:00"))
    assert returned_logical_date == logical_date


async def test_run_non_task_item_type_fail(
    client: TestClient, workflow_laui: str, project_laui: str, account_laui: str
):
    """
    Test that non-task item types cannot be executed.
    Only tasks (item_type="task") can be executed via the run API.
    """
    # Try to run an operator (should fail)
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "operator.python",
                "name": f"operator_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "codeblock": {"main.py": "print('test')"},
                "bashblock": {"main.sh": "echo 'test'"},
            },
        ),
    )

    assert response.status_code == 422
    response_data = response.json()
    assert "detail" in response_data
    # Should indicate that only tasks can be executed
    assert "task" in response_data["detail"].lower() or "Only tasks" in response_data["detail"]


async def test_run_existing_non_task_item_with_item_laui_fail(
    client: TestClient, operator_laui: str
):
    """
    Test that execution fails when item_laui references a non-task item.
    The orchestrator should check that the item is a task before executing.
    """
    # Try to execute an existing operator using its item_laui (should fail)
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "operator.python",
                "item_laui": operator_laui,
            },
        ),
    )

    assert response.status_code == 422
    response_data = response.json()
    assert "detail" in response_data
    # Should indicate that only tasks can be executed
    assert "you can only run 'task' items" in response_data["detail"].lower()


async def test_run_task_with_missing_operator_fail(
    client: TestClient,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that task execution fails when operator_laui is missing.
    """
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_no_operator_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )

    assert response.status_code in [400, 422]  # Validation error


async def test_run_task_with_missing_connection_fail(
    client: TestClient, operator_laui: str, workflow_laui: str, project_laui: str, account_laui: str
):
    """
    Test that task execution fails when connection_laui is missing.
    """
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_no_connection_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )

    assert response.status_code in [400, 422]  # Validation error


async def test_run_task_with_nonexistent_operator_fail(
    client: TestClient,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that task execution fails when operator_laui references a non-existent item.
    """
    fake_operator_laui = str(ObjectId())
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_fake_operator_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": fake_operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )

    assert response.status_code in [400, 404, 422]  # Not found or validation error


async def test_run_task_with_nonexistent_connection_fail(
    client: TestClient, operator_laui: str, workflow_laui: str, project_laui: str, account_laui: str
):
    """
    Test that task execution fails when connection_laui references a non-existent item.
    """
    fake_connection_laui = str(ObjectId())
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_fake_connection_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": fake_connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )

    assert response.status_code in [400, 404, 422]  # Not found or validation error


async def test_run_task_with_missing_account_laui_fail(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
):
    """
    Test that task execution fails when account_laui is missing (required field).
    """
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_no_account_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )

    assert response.status_code in [400, 422]  # Validation error


async def test_run_task_with_missing_project_laui_fail(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    account_laui: str,
):
    """
    Test that task execution fails when project_laui is missing (required field).
    """
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_no_project_{datetime.now().timestamp()}",
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )

    assert response.status_code in [400, 422]  # Validation error


async def test_run_task_with_cron_missing_start_date_fail(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that task execution fails when cron frequency is provided without start_date.
    """
    now = datetime.now(UTC)
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_cron_no_start_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "0 12 * * *",
                "end_date": now.isoformat(),
            },
        ),
    )

    assert response.status_code in [400, 422]  # Validation error


async def test_run_task_with_invalid_cron_expression_fail(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that task execution fails with invalid cron expression.
    """
    now = datetime.now(UTC)
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_invalid_cron_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "invalid_cron",
                "start_date": now.isoformat(),
                "end_date": (now + timedelta(days=1)).isoformat(),
            },
        ),
    )

    assert response.status_code in [400, 422]  # Validation error


async def test_run_task_with_end_date_before_start_date_fail(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that task execution fails when end_date is before start_date.
    """
    now = datetime.now(UTC)
    start_date = now.isoformat()
    end_date = (now - timedelta(days=1)).isoformat()  # End before start

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_bad_dates_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "0 12 * * *",
                "start_date": start_date,
                "end_date": end_date,
            },
        ),
    )

    assert response.status_code in [400, 422]  # Validation error


async def test_run_task_with_nonexistent_payload_laui_fail(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that task execution fails when payload_laui references a non-existent item.
    """
    fake_payload_laui = str(ObjectId())
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_fake_payload_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "payload_laui": fake_payload_laui,
            },
        ),
    )

    assert response.status_code in [400, 404, 422]  # Not found or validation error


async def test_run_task_with_empty_request_body_fail(client: TestClient):
    """
    Test that task execution fails with empty request body.
    """
    response = execute_request(
        client=client, request=TestRequest(url="/api/v1/task/run", method="post", json={})
    )

    assert response.status_code == 422  # Validation error - missing item_type


async def test_run_task_with_missing_item_type_fail(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that task execution fails when item_type is missing.
    """
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "name": f"task_no_type_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )

    assert response.status_code == 422  # Validation error - missing item_type


@pytest.fixture
async def pre_action_laui(
    client: TestClient, action_folder_laui: str, project_laui: str, account_laui: str
) -> str:
    """Create a simple pre-action that logs a message"""
    action_code = '''from src.common.logger.logger import log_info

def run(least_action_action_object, message):
    """
    """
    action_id = least_action_action_object.get("laui")

    try:
        log_info("pre_action", "run", "start", f"Pre-action {action_id} starting")
        return True
    except Exception as e:
        log_info("pre_action", "run", "error", f"Error: {str(e)}")
        return False'''

    action_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "action",
                "name": f"PreActionLogger_{datetime.now().timestamp()}",
                "parent_laui": action_folder_laui,
                "is_root": False,
                "prompt": "Generate a pre-action that logs a message",
                "codeblock": {"main.py": action_code},
                "bashblock": {},
                "project_laui": project_laui,
                "account_laui": account_laui,
            },
        ),
    )
    assert action_resp.status_code == 200
    return CreateItemResponse(**action_resp.json()).item_laui


async def test_run_task_with_pre_action_pass(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
    pre_action_laui: str,
):
    """
    Test successful task execution with pre_action in the actions field.
    The task should include a pre_action that runs before the task executes.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_with_pre_action_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "actions": {
                    "pre_actions": [
                        {
                            "laui": pre_action_laui,
                            "action_variables": {
                                "message": "This is a pre-action running before the task"
                            },
                        }
                    ]
                },
            },
        ),
    )

    print(task_resp.json())
    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None
    assert isinstance(task_data.item_laui, str)

    # Verify the task was created with the pre_action
    task_item_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": task_data.item_laui}
        ),
    )
    assert task_item_resp.status_code == 200
    task_item = task_item_resp.json()

    # Verify actions field exists and contains pre_actions
    assert "actions" in task_item
    assert "pre_actions" in task_item["actions"]
    assert len(task_item["actions"]["pre_actions"]) == 1
    assert task_item["actions"]["pre_actions"][0]["laui"] == pre_action_laui


# =============================================================================
#                       FAILURE CASES(marked with _fail)
# =============================================================================
async def test_create_action_for_task_execution_fail(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
    file_system_action_laui: str,
):
    fake = "507f1f77bcf86cd799439011"
    test_dir = tempfile.mkdtemp()
    expected_content = "INTEGRATION TEST ::: test_create_action_for_task_execution"
    file_name = "task_test_file.txt"
    actions_dict = {
        "create_actions": [
            {
                "laui": file_system_action_laui,
                "action_variables": {
                    "folder_path": test_dir,
                    "file_path": file_name,
                    "file_content": expected_content,
                },
            },
            {
                "laui": fake,
                "action_variables": {
                    "folder_path": test_dir,
                    "file_path": file_name,
                    "file_content": expected_content,
                },
            },
        ],
        "pre_actions": [],
        "running_actions": [],
        "post_actions": [],
    }
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_adhoc_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "actions": actions_dict,  # Passing the actions dictionary here
            },
        ),
    )
    assert task_resp.status_code == 422
    response_data = task_resp.json()["detail"]
    assert "not found" in response_data.lower()
