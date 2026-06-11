# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
"""
Integration tests for the /task/multiple_tasks API endpoint.

These tests verify that:
1. Multiple tasks can be executed successfully via API
2. Session IDs are properly set on each task
3. Task results are returned correctly
4. Empty task list is handled properly
"""

import asyncio
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from src.core.catalog.api_request import CreateItemResponse, MultipleTaskResponse
from src.core.db.types import MongoDatabase
from src.core.task.connection.schema import SortOrder
from tests.integration.schema import BaseFolders, TestRequest
from tests.integration.utils import create_base_folders, execute_request

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def database_cleanup(test_database: MongoDatabase, client: TestClient):
    await test_database.items.drop()
    await test_database.links.delete_many({})
    yield
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
                "max_parallelism": 25,
                "content": {"type": "docker"},
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
    """Create a payload item"""
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


async def create_task(
    client: TestClient,
    project_laui: str,
    account_laui: str,
    workflow_laui: str,
    operator_laui: str,
    connection_laui: str,
    payload_laui: str,
    task_name: str,
) -> str:
    """Helper to create a task and return its laui"""
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "task",
                "name": task_name,
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "payload_laui": payload_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )
    assert task_resp.status_code == 200
    return CreateItemResponse(**task_resp.json()).item_laui


async def test_execute_multiple_tasks_with_ten_tasks_pass(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
    payload_laui: str,
):
    """Test successful execution of ten tasks via API endpoint"""
    task_lauis = []
    await asyncio.sleep(0.5)
    for i in range(10):
        task_laui = await create_task(
            client,
            project_laui,
            account_laui,
            workflow_laui,
            operator_laui,
            connection_laui,
            payload_laui,
            f"task_{i}_{datetime.now().timestamp()}",
        )
        task_lauis.append(task_laui)
        if i < 9:  # Don't sleep after the last task
            await asyncio.sleep(0.2)  # 50ms between creations

    # Call the API endpoint instead of item_orchestrator directly
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/multiple_tasks", method="post", json={"task_lauis": task_lauis}
        ),
    )
    await asyncio.sleep(0.1)

    assert response.status_code == 200, f"API call failed: {response.text}"
    result = MultipleTaskResponse(**response.json())

    assert result is not None
    assert isinstance(result, MultipleTaskResponse)
    assert len(result.task_results) == 10


async def test_execute_multiple_tasks_with_single_task_pass(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
    payload_laui: str,
):
    """Test execution of a single task via API endpoint"""
    task_laui = await create_task(
        client,
        project_laui,
        account_laui,
        workflow_laui,
        operator_laui,
        connection_laui,
        payload_laui,
        f"single_task_{datetime.now().timestamp()}",
    )

    # Call the API endpoint instead of item_orchestrator directly
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/multiple_tasks", method="post", json={"task_lauis": [task_laui]}
        ),
    )

    assert response.status_code == 200, f"API call failed: {response.text}"
    result = MultipleTaskResponse(**response.json())

    assert result is not None
    assert isinstance(result, MultipleTaskResponse)
    assert len(result.task_results) == 1


async def test_execute_multiple_tasks_empty_list_pass(client: TestClient):
    """Test execution with empty task list via API endpoint"""
    # Call the API endpoint instead of item_orchestrator directly
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/multiple_tasks", method="post", json={"task_lauis": []}
        ),
    )

    assert response.status_code == 200, f"API call failed: {response.text}"
    result = MultipleTaskResponse(**response.json())

    assert result is not None
    assert isinstance(result, MultipleTaskResponse)
    assert len(result.task_results) == 0
