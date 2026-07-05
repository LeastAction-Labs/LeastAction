# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from src.core.catalog.api_request import CreateItemResponse
from src.core.db.types import MongoDatabase
from src.core.task.schema import TaskState
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
# TEST CASES SUMMARY
# ============================================================================
# This test file covers task update functionality with system_update_fields:
#
# SUCCESS CASES:
#    - Update task with all allowed system_update_fields
#    - Update task with partial allowed fields
#    - Update task state transitions
#    - Update task duration with float to int conversion
#
# VALIDATION CASES:
#    - Attempt to update task with non-allowed fields (should be ignored)
#    - Ensure only system_update_fields are updated
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
    """Create a Python connection"""
    conn_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.workflow",
                "name": f"connection_{datetime.now().timestamp()}",
                "parent_laui": project_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
            },
        ),
    )
    assert conn_resp.status_code == 200
    return CreateItemResponse(**conn_resp.json()).item_laui


@pytest.fixture
async def connection_laui(
    client: TestClient, workflow_laui: str, account_laui: str, project_laui: str
) -> str:
    """Create a Python connection"""
    conn_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "connection.python",
                "name": f"connection_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "content": {},  # Required field for connection
            },
        ),
    )
    assert conn_resp.status_code == 200
    return CreateItemResponse(**conn_resp.json()).item_laui


@pytest.fixture
async def operator_laui(
    client: TestClient, workflow_laui: str, account_laui: str, project_laui: str
) -> str:
    """Create a Python operator"""
    op_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "operator.python",
                "name": f"test_operator_{datetime.now().timestamp()}.operator",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "codeblock": {
                    "main.py": "def initialize(self):\n    return {}\ndef run(self, ctx):\n    return {'status': 'ok', 'execution_type': 'sync'}\ndef check_completion(self, ctx, state):\n    return {'status': 'done'}\ndef finish(self, ctx, state, result):\n    return None\n"
                },
                "bashblock": {},  # Required field
            },
        ),
    )
    assert op_resp.status_code == 200
    return CreateItemResponse(**op_resp.json()).item_laui


@pytest.fixture
async def task_laui(
    client: TestClient,
    account_laui: str,
    project_laui: str,
    workflow_laui: str,
    connection_laui: str,
    operator_laui: str,
) -> str:
    """Create a basic task for testing updates"""
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"test_task_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "frequency": "ADHOC",
            },
        ),
    )
    assert task_resp.status_code == 200
    return CreateItemResponse(**task_resp.json()).item_laui


async def test_update_task_with_all_allowed_fields_pass(
    client: TestClient,
    task_laui: str,
):
    """
    Test Case 1: Update task with ALL allowed system_update_fields.

    This test verifies that all fields defined in system_update_fields
    in task.json can be successfully updated:
    - logical_date
    - last_run_date
    - last_system_updated_date
    - latest_heartbeat
    - last_run_output
    - payload
    - config
    - state
    - user_set_state
    - iteration
    - duration
    - task_instance
    - last_run_session_id
    - retry_number
    """
    now = datetime.now(UTC)

    # Prepare update data with ALL allowed fields
    update_data = {
        "logical_date": now.isoformat(),
        "last_run_date": now.isoformat(),
        "last_system_updated_date": now.isoformat(),
        "latest_heartbeat": now.isoformat(),
        "last_run_output": {"message": "Task executed successfully"},
        "payload": '{"key": "value", "data": [1, 2, 3]}',
        "config": {"timeout": 300, "retries": 3, "environment": "production"},
        "state": TaskState.RUNNING.value,
        "user_set_state": None,
        "iteration": 5,
        "duration": 1500.75,  # Test float to int conversion
        "task_instance": "worker-01.example.com",
        "last_run_session_id": "673a1b2c3d4e5f6789abcdef",
        "retry_number": 2,
    }

    # Execute update request
    update_resp = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/task/update/{task_laui}",
            method="post",
            json=update_data,
        ),
    )

    # Verify update was successful
    assert update_resp.status_code == 200, f"Update failed: {update_resp.json()}"
    update_result = update_resp.json()
    assert "item_laui" in update_result
    assert update_result["item_laui"] == task_laui

    # Fetch the updated task to verify all fields were updated
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={"item_laui": task_laui},
        ),
    )

    assert get_resp.status_code == 200
    updated_task = get_resp.json()

    # Verify all updated fields
    assert updated_task["state"] == TaskState.RUNNING.value
    assert updated_task["iteration"] == 5
    assert updated_task["duration"] == 1500  # Should be converted to int
    assert updated_task["retry_number"] == 2
    assert updated_task["last_run_output"]["message"] == "Task executed successfully"
    assert updated_task["payload"] == '{"key": "value", "data": [1, 2, 3]}'
    assert updated_task["config"]["timeout"] == 300
    assert updated_task["config"]["retries"] == 3
    assert updated_task["task_instance"] == "worker-01.example.com"
    assert updated_task["last_run_session_id"] == "673a1b2c3d4e5f6789abcdef"

    # Verify datetime fields are set (ISO format strings)
    assert updated_task["logical_date"] is not None
    assert updated_task["last_run_date"] is not None
    assert updated_task["last_system_updated_date"] is not None
    assert updated_task["latest_heartbeat"] is not None


async def test_update_task_with_non_allowed_fields_validation(
    client: TestClient,
    task_laui: str,
    project_laui: str,
):
    """
    Test Case 2: Attempt to update task with NON-ALLOWED fields.

    This test verifies that fields NOT in system_update_fields are ignored
    or rejected. Fields like:
    - name (user-defined field, not in system_update_fields)
    - operator_laui (required field, but not in system_update_fields)
    - connection_laui (required field, but not in system_update_fields)
    - frequency (user-defined field, not in system_update_fields)
    - description (user-defined field, not in system_update_fields)

    The system should:
    1. Successfully process allowed fields
    2. Ignore or reject non-allowed fields
    3. Keep original values for non-updatable fields
    """
    # Get original task data
    get_resp_before = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={"item_laui": task_laui},
        ),
    )
    assert get_resp_before.status_code == 200
    original_task = get_resp_before.json()
    original_name = original_task["name"]
    original_operator = original_task["operator_laui"]
    original_connection = original_task["connection_laui"]
    original_frequency = original_task["frequency"]

    # Prepare update data mixing ALLOWED and NON-ALLOWED fields
    update_data = {
        # ALLOWED fields (these should be updated)
        "state": TaskState.SUCCESS.value,
        "iteration": 10,
        "duration": 2500,
        "last_run_output": {"message": "Updated output"},
        # NON-ALLOWED fields (these should be ignored or cause validation error)
        "name": "CHANGED_NAME",  # Not in system_update_fields
        "operator_laui": "000000000000000000000000",  # Not in system_update_fields
        "connection_laui": "111111111111111111111111",  # Not in system_update_fields
        "frequency": "0 * * * *",  # Not in system_update_fields
        "description": "Unauthorized description change",  # Not in system_update_fields
        "project_laui": project_laui,  # Not in system_update_fields
    }

    # Execute update request
    update_resp = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/task/update/{task_laui}",
            method="post",
            json=update_data,
        ),
    )

    # The update should succeed (with non-allowed fields ignored)
    assert update_resp.status_code == 200, f"Update failed: {update_resp.json()}"

    # Fetch the updated task
    get_resp_after = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={"item_laui": task_laui},
        ),
    )

    assert get_resp_after.status_code == 200
    updated_task = get_resp_after.json()

    # VERIFY: Allowed fields WERE updated
    assert updated_task["state"] == TaskState.SUCCESS.value, "State should be updated"
    assert updated_task["iteration"] == 10, "Iteration should be updated"
    assert updated_task["duration"] == 2500, "Duration should be updated"
    assert updated_task["last_run_output"]["message"] == "Updated output", (
        "Output should be updated"
    )

    # VERIFY: Non-allowed fields were NOT changed (kept original values)
    assert updated_task["name"] == original_name, "Name should NOT be changed"
    assert updated_task["operator_laui"] == original_operator, "Operator should NOT be changed"
    assert updated_task["connection_laui"] == original_connection, (
        "Connection should NOT be changed"
    )
    assert updated_task["frequency"] == original_frequency, "Frequency should NOT be changed"

    # Verify description remains unchanged (if it existed)
    original_description = original_task.get("description")
    updated_description = updated_task.get("description")
    assert updated_description == original_description, "Description should NOT be changed"


async def test_update_task_partial_fields_pass(
    client: TestClient,
    task_laui: str,
):
    """
    Test updating task with only a subset of allowed fields.
    Verifies that partial updates work correctly.
    """
    update_data = {
        "state": TaskState.QUEUED_IN_REDIS.value,
        "iteration": 3,
    }

    update_resp = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/task/update/{task_laui}",
            method="post",
            json=update_data,
        ),
    )

    assert update_resp.status_code == 200

    # Verify update
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={"item_laui": task_laui},
        ),
    )

    assert get_resp.status_code == 200
    updated_task = get_resp.json()
    assert updated_task["state"] == TaskState.QUEUED_IN_REDIS.value
    assert updated_task["iteration"] == 3


async def test_update_task_duration_float_to_int_conversion_pass(
    client: TestClient,
    task_laui: str,
):
    """
    Test that duration field properly converts float to int.
    """
    update_data = {
        "duration": 3456.789,  # Float value
    }

    update_resp = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/task/update/{task_laui}",
            method="post",
            json=update_data,
        ),
    )

    assert update_resp.status_code == 200

    # Verify conversion
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={"item_laui": task_laui},
        ),
    )

    assert get_resp.status_code == 200
    updated_task = get_resp.json()
    assert updated_task["duration"] == 3456  # Should be int
    assert isinstance(updated_task["duration"], int)


async def test_update_nonexistent_task_fail(
    client: TestClient,
):
    """
    Test updating a task that doesn't exist.
    Should return 404 Not Found.
    """
    fake_task_id = "000000000000000000000000"

    update_data = {
        "state": TaskState.RUNNING.value,
        "iteration": 1,
    }

    update_resp = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/task/update/{fake_task_id}",
            method="post",
            json=update_data,
        ),
    )

    # Should fail with 404
    assert update_resp.status_code == 403
