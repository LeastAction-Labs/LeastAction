# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import datetime

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
async def task_laui(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
) -> str:
    """Create a valid task"""
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_get_{datetime.now().timestamp()}",
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
    assert task_resp.status_code == 200
    return CreateItemResponse(**task_resp.json()).item_laui


async def test_get_valid_task_pass(
    client: TestClient,
    task_laui: str,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test successfully getting a valid task by its ID.
    Should return the task with all its properties.
    """
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": task_laui}
        ),
    )

    assert response.status_code == 200
    task_data = response.json()

    # Verify basic task properties
    assert task_data["laui"] == task_laui
    assert task_data["item_type"] == "task"
    assert task_data["parent_laui"] == workflow_laui
    assert not task_data["is_root"]
    assert "name" in task_data
    assert task_data["name"].startswith("task_get_")

    # Verify task-specific fields
    assert task_data["project_laui"] == project_laui
    assert task_data["account_laui"] == account_laui
    assert task_data["state"] == "scheduled"
    assert task_data["frequency"] == "ADHOC"
    assert task_data["operator_laui"] == operator_laui
    assert task_data["connection_laui"] == connection_laui


async def test_get_task_with_nonexistent_laui_fail(client: TestClient):
    """
    Test that getting a task with a non-existent ID fails.
    Should return 404 status code.
    """
    fake_task_laui = str(ObjectId())

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": fake_task_laui}
        ),
    )

    assert response.status_code == 404


async def test_get_task_with_config_field_pass(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test getting a task that has a config field.
    Verify that the config field is returned correctly.
    """
    # Create a task with config field
    task_config = {
        "parameters": {"env": "staging", "timeout": 200},
        "defaults": {"task": {"retry_count": 3}},
    }

    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_with_config_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "config": task_config,
            },
        ),
    )

    assert task_resp.status_code == 200
    task_laui = CreateItemResponse(**task_resp.json()).item_laui

    # Get the task
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": task_laui}
        ),
    )

    assert response.status_code == 200
    task_data = response.json()

    # Verify config field is present and correct
    assert "config" in task_data
    assert task_data["config"] == task_config
    assert task_data["config"]["parameters"]["env"] == "staging"
    assert task_data["config"]["parameters"]["timeout"] == 200
    assert task_data["config"]["defaults"]["task"]["retry_count"] == 3


async def test_get_task_without_config_field_pass(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test getting a task that has no config field (default empty dict).
    Verify that the config field is returned as empty dict.
    """
    # Create a task without config field
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_no_config_{datetime.now().timestamp()}",
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

    assert task_resp.status_code == 200
    task_laui = CreateItemResponse(**task_resp.json()).item_laui

    # Get the task
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": task_laui}
        ),
    )

    assert response.status_code == 200
    task_data = response.json()

    # Verify config field is present and is empty dict (default)
    assert "config" in task_data
    assert task_data["config"] == {}
