# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
"""
Integration tests for TaskExecutionService with real write-to-file operator.

Tests the task executor with three scenarios:
1. Natural finish - task completes successfully
2. Cancellation - user cancels task during execution
3. Error - operator fails with validation error

Each test verifies file existence/content as assertion.
Uses API client for TaskExecutionService (no direct Celery usage).
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.core.catalog.api_request import CreateItemResponse
from src.core.catalog.item.schema import Item
from src.core.celery.client import APIClient
from src.core.celery.executors.task_executor import TaskExecutionService
from src.core.celery.registry import execute_action
from src.core.celery.schema import TaskRequest
from src.core.db.types import MongoDatabase
from src.core.task.action.action_manager import ActionManager
from src.core.task.schema import TaskState, TaskUpdateData
from tests.integration.schema import BaseFolders, TestRequest
from tests.integration.utils import (
    create_base_folders,
    execute_request,
    get_system_access_token,
)

pytestmark = pytest.mark.anyio


class TestAPIClient(APIClient):
    """Test-specific APIClient that uses TestClient instead of real HTTP requests"""

    def __init__(self, test_client: TestClient):
        super().__init__(base_url="http://backend-test")
        self.test_client = test_client

    async def get_item(
        self, auth_token: str, item_laui: str, session_id: str | None = None
    ) -> Item:
        """Get item using TestClient synchronously in async context"""

        # Run the sync TestClient request in thread pool
        def _sync_get():
            headers = {"Cookie": f"frontend_token={auth_token}"}
            if session_id:
                headers["X-Session-ID"] = session_id

            response = self.test_client.get(
                "/api/v1/catalog/get", params={"item_laui": item_laui}, headers=headers
            )
            response.raise_for_status()
            return response.json()

        data = await asyncio.to_thread(_sync_get)

        # Handle list response (API returns list)
        if isinstance(data, list) and len(data) > 0:
            item_data = data[0]
            if "item_laui" in item_data and "laui" not in item_data:
                item_data["laui"] = item_data["item_laui"]
            return Item(**item_data)
        elif isinstance(data, dict):
            if "item_laui" in data and "laui" not in data:
                data["laui"] = data["item_laui"]
            return Item(**data)
        else:
            raise ValueError(f"No item found with laui: {item_laui}")

    async def update_item(
        self,
        auth_token: str,
        system_auth_token: str,
        task_laui: str,
        update_data: TaskUpdateData,
    ) -> str:
        """Update item using TestClient synchronously in async context"""

        def _sync_update():
            try:
                # Serialize to JSON string and then parse to ensure proper serialization of all types
                update_json_str = update_data.model_dump_json(exclude_none=True)
                update_fields = json.loads(update_json_str)

                headers = {
                    "Cookie": f"frontend_token={auth_token};",
                    "X-System-Auth-Token": system_auth_token,
                }
                response = self.test_client.post(
                    f"/api/v1/task/update/{task_laui}", json=update_fields, headers=headers
                )
                if response.status_code != 200:
                    print(f"[TestAPIClient] Update failed with {response.status_code}")
                    print(f"[TestAPIClient] Payload sent: {update_fields}")
                    print(f"[TestAPIClient] Response: {response.text}")
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"[TestAPIClient] Exception in _sync_update: {type(e).__name__}: {e}")
                import traceback

                traceback.print_exc()
                raise

        response_data = await asyncio.to_thread(_sync_update)

        # Return the item_laui from the response
        response = CreateItemResponse(**response_data)
        return response.item_laui

    async def finish_task(
        self,
        auth_token: str,
        system_auth_token: str,
        task_laui: str,
        session_id: str | None = None,
    ):
        def _sync_finish():
            headers = {
                "Cookie": f"frontend_token={auth_token};",
                "X-System-Auth-Token": system_auth_token,
            }
            if session_id:
                headers["X-Session-ID"] = session_id

            response = self.test_client.post(f"/api/v1/task/finish/{task_laui}", headers=headers)
            response.raise_for_status()

        await asyncio.to_thread(_sync_finish)


@pytest.fixture(autouse=True)
async def database_cleanup(test_database: MongoDatabase, client: TestClient):
    """Clean database before and after each test"""
    await test_database.items.delete_many({})
    await test_database.links.delete_many({})
    yield
    await test_database.items.delete_many({})
    await test_database.links.delete_many({})


# ============================================================================
# FOLDER HIERARCHY FIXTURES
# ============================================================================


@pytest.fixture
async def access_token() -> str:
    """Get system access token"""
    return await get_system_access_token()


@pytest.fixture
async def auth_header(access_token: str) -> str:
    """Return auth header with access token"""
    return f"frontend_token={access_token};"


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
async def workflow_laui(
    client: TestClient, auth_header: str, account_laui: str, project_laui: str
) -> str:
    """Create a workflow folder under project"""
    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            headers={"Cookie": auth_header},
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
    assert resp.status_code == 200
    return CreateItemResponse(**resp.json()).item_laui


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================


@pytest.fixture
def operator_codeblock() -> dict:
    """Load operator code from task-test-data/main.py"""
    operator_path = Path(__file__).parent / "task-test-data" / "operator.py"
    with open(operator_path) as f:
        operator_code = f.read()
    return {"main.py": operator_code}


@pytest.fixture
def connection_content() -> dict:
    """Load connection content from task-test-data/connection.py"""
    import json

    connection_path = Path(__file__).parent / "task-test-data" / "connection.py"
    with open(connection_path) as f:
        content = "\n".join(line for line in f if not line.startswith("#"))
    return json.loads(content)


@pytest.fixture
def payload_content() -> str:
    """Load payload content from task-test-data/payload.py"""
    payload_path = Path(__file__).parent / "task-test-data" / "payload.py"
    with open(payload_path) as f:
        return f.read()


@pytest.fixture
async def operator_laui(
    client: TestClient,
    auth_header: str,
    account_laui: str,
    project_laui: str,
    workflow_laui: str,
    operator_codeblock: dict,
) -> str:
    """Create operator item using task-test-data/operator.py"""
    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            headers={"Cookie": auth_header},
            json={
                "item_type": "operator.python",
                "name": f"file_write_operator_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "codeblock": operator_codeblock,
                "bashblock": {},
            },
        ),
    )
    assert resp.status_code == 200
    return CreateItemResponse(**resp.json()).item_laui


@pytest.fixture
async def connection_laui(
    client: TestClient,
    auth_header: str,
    account_laui: str,
    project_laui: str,
    workflow_laui: str,
    connection_content: dict,
) -> str:
    """Create connection item using task-test-data/connection.py"""
    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            headers={"Cookie": auth_header},
            json={
                "item_type": "connection.python",
                "name": f"python_connection_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "content": connection_content,
            },
        ),
    )
    assert resp.status_code == 200
    return CreateItemResponse(**resp.json()).item_laui


@pytest.fixture
async def task_execution_service(client: TestClient, tmp_path: Path) -> TaskExecutionService:
    """Create TaskExecutionService instance with TestAPIClient"""
    # Create TestAPIClient that uses the test client
    api_client = TestAPIClient(test_client=client)
    action_manager = ActionManager(api_client=api_client, action_task=execute_action)
    # Create operators directory in tmp_path
    operators_dir = tmp_path / "operators"
    operators_dir.mkdir(parents=True, exist_ok=True)

    return TaskExecutionService(
        api_client=api_client, operators_dir=operators_dir, action_manager=action_manager
    )


# ============================================================================
# TEST CASES
# ============================================================================


async def test_task_executor_natural_finish(
    client: TestClient,
    task_execution_service: TaskExecutionService,
    auth_header: str,
    access_token: str,
    account_laui: str,
    project_laui: str,
    workflow_laui: str,
    operator_laui: str,
    connection_laui: str,
    tmp_path: Path,
):
    """
    Test 1: Natural finish - task completes successfully

    - Creates a task with valid payload
    - Executes task using TaskExecutionService
    - Verifies file is created with correct content
    - Verifies task state is SUCCESS
    """
    # Create test file path in tmp_path
    test_file = tmp_path / "test_output.txt"
    test_message = "Task completed successfully!"

    # Generate task name once to use consistently
    task_name = f"task_natural_finish_{datetime.now().timestamp()}"

    # Create payload
    payload = {"path": str(test_file), "message": test_message, "append": False}

    # Create task via API
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            headers={"Cookie": auth_header},
            json={
                "item_type": "task",
                "name": task_name,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "frequency": "ADHOC",
                "state": TaskState.SCHEDULED,
                "payload": json.dumps(payload),
            },
        ),
    )
    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    task_laui = task_data.item_laui

    # Create TaskRequest object
    task_request = TaskRequest(
        name=task_name,
        laui=task_laui,
        account_laui=account_laui,
        project_laui=project_laui,
        parent_laui=workflow_laui,
        last_run_session_id="test-session-natural",
        connection_laui=connection_laui,
        operator_laui=operator_laui,
        frequency="ADHOC",
        payload=json.dumps(payload),
        logical_date=None,
        retry_number=0,
        user_access_token=access_token,
    )

    # Execute task
    await task_execution_service.execute_task(task_request, access_token)

    # Wait for update to complete
    await asyncio.sleep(2)

    # Verify file exists and has correct content
    assert test_file.exists(), f"File {test_file} should exist"
    with open(test_file) as f:
        content = f.read()
    assert content == test_message, f"File content should be '{test_message}', got '{content}'"

    # Verify task state via API
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={"item_laui": task_laui},
        ),
    )
    assert get_resp.status_code == 200
    response_data = get_resp.json()
    # Handle both list and dict responses
    task_data = response_data[0] if isinstance(response_data, list) else response_data
    task_state = TaskState(task_data.get("state"))
    assert task_state == TaskState.SUCCESS, (
        f"Task state should be {TaskState.SUCCESS}, got {task_state}"
    )


async def test_task_executor_cancellation(
    client: TestClient,
    task_execution_service: TaskExecutionService,
    auth_header: str,
    access_token: str,
    account_laui: str,
    project_laui: str,
    workflow_laui: str,
    operator_laui: str,
    connection_laui: str,
    tmp_path: Path,
):
    """
    Test 2: Cancellation - user cancels task during execution

    - Creates a task
    - Starts task execution in background
    - Updates user_set_state to 'cancel' during execution
    - Verifies task state is CANCELLED with cancellation message
    """
    # Create test file path in tmp_path
    test_file = tmp_path / "test_cancelled.txt"
    test_message = "This should be cancelled"

    # Generate task name once to use consistently
    task_name = f"task_cancellation_{datetime.now().timestamp()}"

    # Create payload with delay to allow cancellation
    payload = {
        "path": str(test_file),
        "message": test_message,
        "append": False,
        "delay": 4,  # Sleep for 4 seconds to allow cancellation
    }

    # Create task via API
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            headers={"Cookie": auth_header},
            json={
                "item_type": "task",
                "name": task_name,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "frequency": "ADHOC",
                "state": TaskState.SCHEDULED,
                "payload": json.dumps(payload),
            },
        ),
    )
    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    task_laui = task_data.item_laui

    # Create TaskRequest object
    task_request = TaskRequest(
        name=task_name,
        laui=task_laui,
        account_laui=account_laui,
        project_laui=project_laui,
        parent_laui=workflow_laui,
        last_run_session_id="test-session-cancel",
        connection_laui=connection_laui,
        operator_laui=operator_laui,
        frequency="ADHOC",
        payload=json.dumps(payload),
        logical_date=None,
        retry_number=0,
        user_access_token=access_token,
    )

    # Function to cancel task after a brief delay
    async def cancel_task():
        await asyncio.sleep(0.5)  # Wait briefly for task to start
        # Update task with user_set_state = 'cancel'
        cancel_resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/task/run",
                method="post",
                headers={"Cookie": auth_header},
                json={
                    "item_type": "task",
                    "name": task_name,
                    "account_laui": account_laui,
                    "project_laui": project_laui,
                    "parent_laui": workflow_laui,
                    "operator_laui": operator_laui,
                    "connection_laui": connection_laui,
                    "frequency": "ADHOC",
                    "state": TaskState.RUNNING,  # Required field - task should be running at this point
                    "user_set_state": "cancel",
                },
            ),
        )
        assert cancel_resp.status_code == 200, (
            f"Cancel request failed with status {cancel_resp.status_code}"
        )

    # Run task execution and cancellation concurrently
    await asyncio.gather(
        task_execution_service.execute_task(task_request, access_token), cancel_task()
    )

    # Wait for update to complete
    await asyncio.sleep(2)

    # Verify task state via API
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={"item_laui": task_laui},
        ),
    )
    assert get_resp.status_code == 200
    response_data = get_resp.json()
    # Handle both list and dict responses
    task_result = response_data[0] if isinstance(response_data, list) else response_data
    task_state = TaskState(task_result.get("state"))
    last_run_output = task_result.get("last_run_output", {})

    assert task_state == TaskState.CANCELLED, (
        f"Task state should be {TaskState.CANCELLED}, got {task_state}"
    )
    assert "cancel" in last_run_output.get("message", "").lower(), (
        "last_run_output should contain cancellation message"
    )


async def test_task_executor_error(
    client: TestClient,
    task_execution_service: TaskExecutionService,
    auth_header: str,
    access_token: str,
    account_laui: str,
    project_laui: str,
    workflow_laui: str,
    operator_laui: str,
    connection_laui: str,
    tmp_path: Path,
):
    """
    Test 3: Error - operator fails with validation error

    - Creates a task with invalid payload (missing required fields)
    - Executes task using TaskExecutionService
    - Verifies task state is ERROR
    - Verifies error message in last_run_output
    - Verifies no file is created due to validation error
    """
    # Create test file path (should not be created due to error)
    test_file = tmp_path / "test_error.txt"

    # Generate task name once to use consistently
    task_name = f"task_error_{datetime.now().timestamp()}"

    # Create invalid payload - missing 'path' field (required by operator)
    invalid_payload = {"message": "This will fail", "append": False}

    # Create task via API
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            headers={"Cookie": auth_header},
            json={
                "item_type": "task",
                "name": task_name,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "frequency": "ADHOC",
                "state": TaskState.SCHEDULED,
                "payload": json.dumps(invalid_payload),
            },
        ),
    )
    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    task_laui = task_data.item_laui

    # Create TaskRequest object
    task_request = TaskRequest(
        name=task_name,
        laui=task_laui,
        account_laui=account_laui,
        project_laui=project_laui,
        parent_laui=workflow_laui,
        last_run_session_id="test-session-error",
        connection_laui=connection_laui,
        operator_laui=operator_laui,
        frequency="ADHOC",
        payload=json.dumps(invalid_payload),
        logical_date=None,
        retry_number=0,
        user_access_token=access_token,
    )

    # Execute task (should complete with error state)
    await task_execution_service.execute_task(task_request, access_token)

    # Wait for update to complete
    await asyncio.sleep(2)

    # Verify task state via API
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={"item_laui": task_laui},
        ),
    )
    assert get_resp.status_code == 200
    response_data = get_resp.json()
    # Handle both list and dict responses
    task_result = response_data[0] if isinstance(response_data, list) else response_data
    task_state = TaskState(task_result.get("state"))
    last_run_output = task_result.get("last_run_output", {})

    assert task_state == TaskState.ERROR, (
        f"Task state should be {TaskState.ERROR}, got {task_state}"
    )
    error_msg = last_run_output.get("error", "")
    # assert "'path' is required" in error_msg, f"Error message should mention missing 'path', got: {error_msg}"

    # Verify file was not created due to validation error
    assert not test_file.exists(), f"File {test_file} should not exist due to validation error"
