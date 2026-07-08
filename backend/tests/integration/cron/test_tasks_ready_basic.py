# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
"""Basic filtering tests for find_tasks_ready_to_run endpoint."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from src.core.catalog.api_request import CreateItemResponse
from src.core.db.types import MongoDatabase
from tests.integration.schema import TestRequest
from tests.integration.utils import create_base_folders, execute_request

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def database_cleanup(test_database: MongoDatabase, client: TestClient):
    await test_database.items.drop()
    await test_database.links.delete_many({})
    create_base_folders(client)  # Ensure trash folder exists for link validation in task creation
    yield  # Test runs here
    await test_database.items.drop()
    await test_database.links.drop()


@dataclass
class TestContext:
    """Container for all test resources"""

    account_laui: str = ""
    project_laui: str = ""
    workflow_1_laui: str = ""
    workflow_2_laui: str = ""
    python_operator_laui: str = ""
    python_connection_laui: str = ""
    task_config_laui: str = ""


def setup_test_environment(client: TestClient) -> TestContext:
    """Create test environment with project, workflow, operator, connection, and config."""
    ctx = TestContext()
    ts = datetime.now().timestamp()
    base_folders = create_base_folders(client)
    ctx.account_laui = base_folders.account_folder_laui
    ctx.project_laui = base_folders.project_folder_laui

    # Workflow 1
    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.workflow",
                "name": f"workflow_1_{ts}",
                "parent_laui": ctx.project_laui,
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
                "folder_metadata": {"state": "active"},
            },
        ),
    )
    assert resp.status_code == 200
    ctx.workflow_1_laui = CreateItemResponse(**resp.json()).item_laui

    # Workflow 2
    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.workflow",
                "name": f"workflow_2_{ts}",
                "parent_laui": ctx.project_laui,
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
                "folder_metadata": {"state": "active"},
            },
        ),
    )
    assert resp.status_code == 200
    ctx.workflow_2_laui = CreateItemResponse(**resp.json()).item_laui

    # Python operator
    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "operator.python",
                "name": f"python_operator_{ts}",
                "parent_laui": ctx.workflow_1_laui,
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
                "codeblock": {
                    "main.py": "def initialize(self):\n    return {}\ndef run(self, ctx):\n    return {'status': 'ok', 'execution_type': 'sync'}\ndef check_completion(self, ctx, state):\n    return {'status': 'done'}\ndef finish(self, ctx, state, result):\n    return None\n"
                },
                "bashblock": {"main.sh": "echo 'test'"},
            },
        ),
    )
    assert resp.status_code == 200
    ctx.python_operator_laui = CreateItemResponse(**resp.json()).item_laui

    # Python connection
    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "connection.python",
                "name": f"python_connection_{ts}",
                "parent_laui": ctx.workflow_1_laui,
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
                "content": {"type": "docker"},
            },
        ),
    )
    assert resp.status_code == 200
    ctx.python_connection_laui = CreateItemResponse(**resp.json()).item_laui

    # Task config
    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "config",
                "name": f"task_config_{ts}",
                "parent_laui": ctx.workflow_1_laui,
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
                "config_type": "task",
                "content": {"parameters": {"DB_HOST": "localhost"}},
            },
        ),
    )
    assert resp.status_code == 200
    ctx.task_config_laui = CreateItemResponse(**resp.json()).item_laui

    return ctx


def create_scheduled_task(
    client: TestClient, ctx: TestContext, workflow_laui: str = None, name_suffix: str = ""
) -> str:
    """Create a scheduled task with valid dates and frequency."""
    now = datetime.now(UTC)
    start = now - timedelta(minutes=1)
    ts = datetime.now().timestamp()

    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"scheduled_task_{name_suffix}_{ts}",
                "project_laui": ctx.project_laui,
                "account_laui": ctx.account_laui,
                "parent_laui": workflow_laui or ctx.workflow_1_laui,
                "operator_laui": ctx.python_operator_laui,
                "connection_laui": ctx.python_connection_laui,
                "state": "scheduled",
                "frequency": "0 * * * *",
                "start_date": start.isoformat(),
                "logical_date": start.isoformat(),
                "end_date": (start + timedelta(hours=1)).isoformat(),
                "attached_config_lauis": [ctx.task_config_laui],
            },
        ),
    )
    assert resp.status_code == 200
    return CreateItemResponse(**resp.json()).item_laui


def create_adhoc_task(client: TestClient, ctx: TestContext, name_suffix: str = "") -> str:
    """Create an ADHOC task."""
    ts = datetime.now().timestamp()
    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"adhoc_task_{name_suffix}_{ts}",
                "project_laui": ctx.project_laui,
                "account_laui": ctx.account_laui,
                "parent_laui": ctx.workflow_1_laui,
                "operator_laui": ctx.python_operator_laui,
                "connection_laui": ctx.python_connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )
    assert resp.status_code == 200
    return CreateItemResponse(**resp.json()).item_laui


async def test_no_tasks_in_db_returns_empty(client: TestClient):
    """Test case 1: No tasks exist in database, return empty list."""
    ctx = setup_test_environment(client)

    # Don't create any tasks
    # Query for tasks ready to run
    resp = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/catalog/get/tasks_ready_to_run/{ctx.project_laui}", method="get"
        ),
    )
    assert resp.status_code == 200
    tasks_ready = resp.json()

    assert len(tasks_ready) == 0, f"Expected 0 tasks when database is empty, got {len(tasks_ready)}"


async def test_only_adhoc_tasks_returns_empty(client: TestClient):
    """Test case 2: Only ADHOC tasks exist, return empty list."""
    ctx = setup_test_environment(client)

    # Create 10 ADHOC tasks
    adhoc_tasks = []
    for i in range(10):
        laui = create_adhoc_task(client=client, ctx=ctx, name_suffix=f"adhoc_{i}")
        adhoc_tasks.append(laui)

    # Query for tasks ready to run
    resp = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/catalog/get/tasks_ready_to_run/{ctx.project_laui}", method="get"
        ),
    )
    assert resp.status_code == 200
    tasks_ready = resp.json()

    assert len(tasks_ready) == 0, (
        f"Expected 0 tasks when only ADHOC tasks exist, got {len(tasks_ready)}"
    )


async def test_only_scheduled_tasks_returns_all(client: TestClient):
    """Test case 3: Only scheduled tasks exist for 1 workflow, return all."""
    ctx = setup_test_environment(client)

    # Create 10 scheduled tasks
    scheduled_tasks = []
    for i in range(10):
        laui = create_scheduled_task(client=client, ctx=ctx, name_suffix=f"scheduled_{i}")
        scheduled_tasks.append(laui)

    # Query for tasks ready to run
    resp = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/catalog/get/tasks_ready_to_run/{ctx.project_laui}", method="get"
        ),
    )
    assert resp.status_code == 200
    tasks_ready = resp.json()

    assert len(tasks_ready) == 10, f"Expected 10 scheduled tasks, got {len(tasks_ready)}"

    # Verify all scheduled tasks are returned
    ready_task_lauis = [task["laui"] for task in tasks_ready]
    for scheduled_task in scheduled_tasks:
        assert scheduled_task in ready_task_lauis, (
            f"Scheduled task {scheduled_task} not found in ready tasks"
        )


async def test_mixed_adhoc_and_scheduled_returns_only_scheduled(client: TestClient):
    """Test case 4: Both scheduled and ADHOC tasks exist, return only scheduled."""
    ctx = setup_test_environment(client)

    # Create 5 scheduled tasks
    scheduled_tasks = []
    for i in range(5):
        laui = create_scheduled_task(client=client, ctx=ctx, name_suffix=f"scheduled_{i}")
        scheduled_tasks.append(laui)

    # Create 5 ADHOC tasks
    adhoc_tasks = []
    for i in range(5):
        laui = create_adhoc_task(client=client, ctx=ctx, name_suffix=f"adhoc_{i}")
        adhoc_tasks.append(laui)

    # Query for tasks ready to run
    resp = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/catalog/get/tasks_ready_to_run/{ctx.project_laui}", method="get"
        ),
    )
    assert resp.status_code == 200
    tasks_ready = resp.json()

    assert len(tasks_ready) == 5, (
        f"Expected 5 scheduled tasks (ADHOC excluded), got {len(tasks_ready)}"
    )

    # Verify only scheduled tasks are returned
    ready_task_lauis = [task["laui"] for task in tasks_ready]
    for scheduled_task in scheduled_tasks:
        assert scheduled_task in ready_task_lauis, (
            f"Scheduled task {scheduled_task} not found in ready tasks"
        )

    # Verify ADHOC tasks are NOT returned
    for adhoc_task in adhoc_tasks:
        assert adhoc_task not in ready_task_lauis, (
            f"ADHOC task {adhoc_task} should NOT be in ready tasks"
        )
