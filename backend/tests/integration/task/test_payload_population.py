# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
"""
Test to verify when payload gets populated in task lifecycle.

Test 1: After task creation with payload_laui, payload should be None
Test 2: After task execution, payload should contain the actual payload value
"""

from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.core.catalog.api_request import CreateItemResponse
from src.core.db.types import MongoDatabase
from tests.integration.schema import BaseFolders, TestRequest
from tests.integration.utils import create_base_folders, execute_request

pytestmark = pytest.mark.anyio


def load_code_block():
    """Load a simple test operator that doesn't do much."""
    path = Path(__file__)
    codeblock_path = path.parent / "celery/task-test-data/sleep_operator.py"
    return codeblock_path.read_text(encoding="utf-8")


codeblock = load_code_block()
PAYLOAD_CONTENT = '{"seconds": 10, "test_key": "test_value"}'


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
async def database_cleanup(test_database: MongoDatabase):
    """Clean database before and after test."""
    await test_database.items.drop()
    await test_database.links.delete_many({})
    yield
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
    """Create test workflow."""
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
    """Create test operator."""
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
    """Create test connection."""
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
            },
        ),
    )
    assert connection_resp.status_code == 200
    return CreateItemResponse(**connection_resp.json()).item_laui


@pytest.fixture
async def payload_laui(
    client: TestClient, workflow_laui: str, account_laui: str, project_laui: str
) -> str:
    """Create test payload item."""
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
                "content": PAYLOAD_CONTENT,
            },
        ),
    )
    assert payload_resp.status_code == 200
    return CreateItemResponse(**payload_resp.json()).item_laui


# ---------------------------------------------------------------------------
# test cases
# ---------------------------------------------------------------------------


async def test_payload_is_none_after_creation(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
    payload_laui: str,
):
    """
    Test Case 1: Verify that payload is None immediately after task creation.

    When a task is created with payload_laui, the payload field should remain None
    because the payload content is not resolved during creation.
    """
    # Create task with payload_laui
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_payload_test_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "payload_laui": payload_laui,
                "frequency": "ADHOC",
                "priority": 1,
            },
        ),
    )

    assert task_resp.status_code == 200, (
        f"Task creation failed ({task_resp.status_code}): {task_resp.text}"
    )
    task_laui = CreateItemResponse(**task_resp.json()).item_laui
    print(f"\n✓ Task created with laui: {task_laui}")
    print(f"  payload_laui: {payload_laui}")

    # Get the task and verify payload is None
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={"item_laui": task_laui},
        ),
    )

    assert get_resp.status_code == 200, f"Task GET failed ({get_resp.status_code}): {get_resp.text}"

    task_data = get_resp.json()
    print("\n📋 Task data after creation:")
    print(f"  payload_laui: {task_data.get('payload_laui')}")
    print(f"  payload: {task_data.get('payload')}")

    # Assert payload is None after creation
    assert task_data.get("payload") is None, (
        f"Expected payload to be None after creation, but got: {task_data.get('payload')}"
    )

    # Assert payload_laui is set correctly
    assert task_data.get("payload_laui") == payload_laui, (
        f"Expected payload_laui to be {payload_laui}, but got: {task_data.get('payload_laui')}"
    )

    print("\n✓ PASSED: Payload is None after task creation (as expected)")


async def test_payload_passed_directly(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test Case 3: Verify that payload passed directly during creation is preserved.

    When a task is created with payload directly (not payload_laui), the payload
    should be present immediately after creation and remain after execution.
    """

    DIRECT_PAYLOAD = '{"test": "direct_payload", "value": 42}'

    # Create task with payload directly (not payload_laui)
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_direct_payload_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "payload": DIRECT_PAYLOAD,  # Passing payload directly
                "frequency": "ADHOC",
                "priority": 1,
            },
        ),
    )

    assert task_resp.status_code == 200, (
        f"Task creation failed ({task_resp.status_code}): {task_resp.text}"
    )
    task_laui = CreateItemResponse(**task_resp.json()).item_laui
    print(f"\n✓ Task created with laui: {task_laui}")

    # Get the task and verify payload is set immediately after creation
    get_resp_before = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={"item_laui": task_laui},
        ),
    )

    assert get_resp_before.status_code == 200, (
        f"Task GET failed ({get_resp_before.status_code}): {get_resp_before.text}"
    )

    task_data_before = get_resp_before.json()
    print("\n📋 Task data AFTER creation (before execution):")
    print(f"  payload_laui: {task_data_before.get('payload_laui')}")
    print(f"  payload: {task_data_before.get('payload')}")

    # Assert payload is set after creation
    assert task_data_before.get("payload") == DIRECT_PAYLOAD, (
        f"Expected payload to be '{DIRECT_PAYLOAD}' after creation, but got: {task_data_before.get('payload')}"
    )

    # Assert payload_laui is None when payload is passed directly
    assert task_data_before.get("payload_laui") is None, (
        f"Expected payload_laui to be None when payload is passed directly, but got: {task_data_before.get('payload_laui')}"
    )

    print("\n✓ PASSED: Payload is present after creation when passed directly")

    # Execute the task
    execute_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/multiple_tasks",
            method="post",
            json={"task_lauis": [task_laui]},
        ),
    )

    assert execute_resp.status_code == 200, (
        f"Task execution failed ({execute_resp.status_code}): {execute_resp.text}"
    )
    print("\n✓ Task execution initiated")

    # Get the task again and verify payload is still present
    get_resp_after = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={"item_laui": task_laui},
        ),
    )

    assert get_resp_after.status_code == 200, (
        f"Task GET failed ({get_resp_after.status_code}): {get_resp_after.text}"
    )

    task_data_after = get_resp_after.json()
    print("\n📋 Task data AFTER execution:")
    print(f"  payload: {task_data_after.get('payload')}")

    # Assert payload is still the same after execution
    assert task_data_after.get("payload") == DIRECT_PAYLOAD, (
        f"Expected payload to remain '{DIRECT_PAYLOAD}' after execution, but got: {task_data_after.get('payload')}"
    )

    print("\n✓ PASSED: Payload remains unchanged after execution when passed directly")
    print(f"  Expected: {DIRECT_PAYLOAD}")
    print(f"  Got: {task_data_after.get('payload')}")


async def test_task_system_params_not_replaced_in_db_after_execution(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test Case 6: Verify that payload placeholders are NOT replaced in the DB after execution.

    Payload placeholder replacement happens in-memory at execution time (for Celery dispatch)
    but is not persisted back to the database. The DB payload should retain the original
    placeholder strings after execution.
    """

    task_name = f"task_sys_params_{datetime.now().timestamp()}"

    PAYLOAD_WITH_PLACEHOLDERS = (
        '{"task_name": "{{ name }}", '
        '"project": "{{ project_laui }}", '
        '"account": "{{ account_laui }}", '
        '"operator": "{{ operator_laui }}", '
        '"connection": "{{ connection_laui }}", '
        '"partition": "{{ partition }}", '
        '"desc_excluded": "{{ description }}"}'
    )

    # Create task with payload containing placeholders
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": task_name,
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "payload": PAYLOAD_WITH_PLACEHOLDERS,
                "frequency": "ADHOC",
                "priority": 1,
            },
        ),
    )

    assert task_resp.status_code == 200, (
        f"Task creation failed ({task_resp.status_code}): {task_resp.text}"
    )
    task_laui = CreateItemResponse(**task_resp.json()).item_laui
    print(f"\n Task created with laui: {task_laui}")

    # Execute the task
    execute_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/multiple_tasks",
            method="post",
            json={"task_lauis": [task_laui]},
        ),
    )

    assert execute_resp.status_code == 200, (
        f"Task execution failed ({execute_resp.status_code}): {execute_resp.text}"
    )
    print("\n Task execution initiated")

    # Get the task after execution
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={"item_laui": task_laui},
        ),
    )

    assert get_resp.status_code == 200, f"Task GET failed ({get_resp.status_code}): {get_resp.text}"

    task_data = get_resp.json()
    payload_after = task_data.get("payload")
    print("\n Task data AFTER execution:")
    print(f"  payload: {payload_after}")

    # Payload in DB should still contain the original unreplaced placeholders.
    # Replacement happens in-memory at dispatch time only (not persisted).
    assert payload_after == PAYLOAD_WITH_PLACEHOLDERS, (
        f"Expected DB payload to retain original placeholders '{PAYLOAD_WITH_PLACEHOLDERS}', "
        f"but got: {payload_after}"
    )

    print("\n PASSED: Payload placeholders remain unreplaced in DB after execution")
    print(f"  DB payload (unchanged): {payload_after}")
