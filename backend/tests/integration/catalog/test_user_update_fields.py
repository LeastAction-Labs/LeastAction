# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from src.core.catalog.api_request import CreateItemResponse
from src.core.db.types import MongoDatabase
from tests.integration.schema import TestRequest
from tests.integration.utils import create_base_folders, execute_request

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def database_cleanup(test_database: MongoDatabase):
    """Clean up database before and after each test"""
    await test_database.items.drop()
    await test_database.links.delete_many({})
    yield
    await test_database.items.drop()
    await test_database.links.drop()


@pytest.fixture
async def test_context(client: TestClient):
    """Create test context with account, project, workflow, and operator"""

    base_folders = create_base_folders(client=client)

    account_laui = base_folders.account_folder_laui
    project_laui = base_folders.project_folder_laui

    # Create workflow
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
    workflow_laui = CreateItemResponse(**wf_resp.json()).item_laui

    # Create operator
    op_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "operator.python",
                "name": f"python_operator_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "codeblock": {
                    "main.py": "def initialize(self):\n    return {}\ndef run(self, ctx):\n    return {'status': 'ok', 'execution_type': 'sync'}\ndef check_completion(self, ctx, state):\n    return {'status': 'done'}\ndef finish(self, ctx, state, result):\n    return None\n"
                },
                "bashblock": {"main.sh": "#!/bin/bash\necho 'test'"},
                "account_laui": account_laui,
                "project_laui": project_laui,
            },
        ),
    )
    assert op_resp.status_code == 200
    operator_laui = CreateItemResponse(**op_resp.json()).item_laui

    # Create connection
    conn_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "connection.python",
                "name": f"python_connection_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "content": {},
                "max_parallelism": 10,
                "account_laui": account_laui,
                "project_laui": project_laui,
            },
        ),
    )
    assert conn_resp.status_code == 200
    connection_laui = CreateItemResponse(**conn_resp.json()).item_laui

    # Create payload
    payload_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "payload.json",
                "name": f"payload_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "content": '{"test": "data"}',
                "account_laui": account_laui,
                "project_laui": project_laui,
            },
        ),
    )
    assert payload_resp.status_code == 200
    payload_laui = CreateItemResponse(**payload_resp.json()).item_laui

    return {
        "account_laui": account_laui,
        "project_laui": project_laui,
        "workflow_laui": workflow_laui,
        "operator_laui": operator_laui,
        "connection_laui": connection_laui,
        "payload_laui": payload_laui,
    }


async def test_update_allowed_fields_success(client: TestClient, test_context):
    """Test updating only allowed fields succeeds"""
    # Create a task with a fixed name (primary key)
    task_name = f"task_{datetime.now().timestamp()}"
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": task_name,
                "project_laui": test_context["project_laui"],
                "account_laui": test_context["account_laui"],
                "parent_laui": test_context["workflow_laui"],
                "operator_laui": test_context["operator_laui"],
                "connection_laui": test_context["connection_laui"],
                "payload_laui": test_context["payload_laui"],
                "frequency": "ADHOC",
                "priority": 1,
            },
        ),
    )
    assert task_resp.status_code == 200
    task_laui = CreateItemResponse(**task_resp.json()).item_laui

    # Update allowed fields (description, priority are in user_update_fields)
    # Pass item_laui to identify which item to update
    update_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "item_laui": task_laui,  # Identify item by laui
                "name": task_name,  # Primary key must remain the same
                "description": "Updated description",
                "priority": 5,
                "project_laui": test_context["project_laui"],
                "account_laui": test_context["account_laui"],
                "parent_laui": test_context["workflow_laui"],
                "operator_laui": test_context["operator_laui"],
                "connection_laui": test_context["connection_laui"],
            },
        ),
    )
    assert update_resp.status_code == 200

    # Verify updates were applied
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": task_laui}
        ),
    )
    assert get_resp.status_code == 200
    task_data = get_resp.json()
    assert task_data["description"] == "Updated description"
    assert task_data["priority"] == 5


async def test_update_user_set_state_allowed(client: TestClient, test_context):
    """Test that user_set_state (in user_update_fields) can be updated"""
    # Create a task with a fixed name (primary key)
    task_name = f"task_{datetime.now().timestamp()}"
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": task_name,
                "project_laui": test_context["project_laui"],
                "account_laui": test_context["account_laui"],
                "parent_laui": test_context["workflow_laui"],
                "operator_laui": test_context["operator_laui"],
                "connection_laui": test_context["connection_laui"],
                "frequency": "ADHOC",
            },
        ),
    )
    assert task_resp.status_code == 200
    task_laui = CreateItemResponse(**task_resp.json()).item_laui

    # Update user_set_state to cancel (this is allowed)
    update_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "item_laui": task_laui,  # Identify item by laui
                "name": task_name,  # Same name (primary key) to identify the item
                "user_set_state": "cancel",
                "project_laui": test_context["project_laui"],
                "account_laui": test_context["account_laui"],
                "parent_laui": test_context["workflow_laui"],
                "operator_laui": test_context["operator_laui"],
                "connection_laui": test_context["connection_laui"],
            },
        ),
    )
    assert update_resp.status_code == 200

    # Verify user_set_state was updated
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": task_laui}
        ),
    )
    assert get_resp.status_code == 200
    task_data = get_resp.json()
    assert task_data["user_set_state"] == "cancel"


async def test_update_system_fields_always_excluded(client: TestClient, test_context):
    """Test that system fields like created_at, updated_at are always excluded"""
    # Create a task with a fixed name (primary key)
    task_name = f"task_{datetime.now().timestamp()}"
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": task_name,
                "project_laui": test_context["project_laui"],
                "account_laui": test_context["account_laui"],
                "parent_laui": test_context["workflow_laui"],
                "operator_laui": test_context["operator_laui"],
                "connection_laui": test_context["connection_laui"],
                "frequency": "ADHOC",
            },
        ),
    )
    assert task_resp.status_code == 200
    task_laui = CreateItemResponse(**task_resp.json()).item_laui

    # Get original created_at
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": task_laui}
        ),
    )
    original_created_at = get_resp.json()["created_at"]

    # Try to update with created_at, updated_at (should be ignored)
    fake_date = "2020-01-01T00:00:00Z"
    update_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "item_laui": task_laui,  # Identify item by laui
                "name": task_name,  # Same name (primary key) to identify the item
                "description": "test description",  # Update an allowed field
                "created_at": fake_date,  # Should be ignored
                "updated_at": fake_date,  # Should be ignored
                "project_laui": test_context["project_laui"],
                "account_laui": test_context["account_laui"],
                "parent_laui": test_context["workflow_laui"],
                "operator_laui": test_context["operator_laui"],
                "connection_laui": test_context["connection_laui"],
            },
        ),
    )
    assert update_resp.status_code == 200

    # Verify system fields were NOT changed
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": task_laui}
        ),
    )
    task_data = get_resp.json()
    assert task_data["created_at"] == original_created_at
    assert task_data["created_at"] != fake_date
