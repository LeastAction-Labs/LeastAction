# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
"""Workflow state filtering tests for find_tasks_ready_to_run endpoint."""

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
    python_operator_1_laui: str = ""
    python_operator_2_laui: str = ""
    python_connection_1_laui: str = ""
    python_connection_2_laui: str = ""
    task_config_laui: str = ""


def setup_test_environment(client: TestClient, workflow_2_state: str = "active") -> TestContext:
    """Create test environment with 2 workflows."""
    ctx = TestContext()
    ts = datetime.now().timestamp()
    base_folders = create_base_folders(client)
    ctx.account_laui = base_folders.account_folder_laui
    ctx.project_laui = base_folders.project_folder_laui

    # Workflow 1 (always active)
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

    # Workflow 2 (configurable state)
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
                "folder_metadata": {"state": workflow_2_state},
            },
        ),
    )
    assert resp.status_code == 200
    ctx.workflow_2_laui = CreateItemResponse(**resp.json()).item_laui

    # Python operator for workflow 1
    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "operator.python",
                "name": f"python_operator_1_{ts}",
                "parent_laui": ctx.workflow_1_laui,
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
                "codeblock": {
                    "main.py": "def initialize(self):\n    return {}\ndef run(self, ctx):\n    return {'status': 'ok', 'execution_type': 'sync'}\ndef check_completion(self, ctx, state):\n    return {'status': 'done'}\ndef finish(self, ctx, state, result):\n    return None\n"
                },
                "bashblock": {"main.sh": "echo 'workflow1'"},
            },
        ),
    )
    assert resp.status_code == 200
    ctx.python_operator_1_laui = CreateItemResponse(**resp.json()).item_laui

    # Python operator for workflow 2
    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "operator.python",
                "name": f"python_operator_2_{ts}",
                "parent_laui": ctx.workflow_2_laui,
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
                "codeblock": {
                    "main.py": "def initialize(self):\n    return {}\ndef run(self, ctx):\n    return {'status': 'ok', 'execution_type': 'sync'}\ndef check_completion(self, ctx, state):\n    return {'status': 'done'}\ndef finish(self, ctx, state, result):\n    return None\n"
                },
                "bashblock": {"main.sh": "echo 'workflow2'"},
            },
        ),
    )
    assert resp.status_code == 200
    ctx.python_operator_2_laui = CreateItemResponse(**resp.json()).item_laui

    # Python connection for workflow 1
    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "connection.python",
                "name": f"python_connection_1_{ts}",
                "parent_laui": ctx.workflow_1_laui,
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
                "content": {"type": "docker"},
            },
        ),
    )
    assert resp.status_code == 200
    ctx.python_connection_1_laui = CreateItemResponse(**resp.json()).item_laui

    # Python connection for workflow 2
    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "connection.python",
                "name": f"python_connection_2_{ts}",
                "parent_laui": ctx.workflow_2_laui,
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
                "content": {"type": "docker"},
            },
        ),
    )
    assert resp.status_code == 200
    ctx.python_connection_2_laui = CreateItemResponse(**resp.json()).item_laui

    # Task config in workflow 1
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
    client: TestClient,
    workflow_laui: str,
    operator_laui: str,
    connection_laui: str,
    config_laui: str,
    project_laui: str,
    account_laui: str,
    name_suffix: str = "",
) -> str:
    """Create a scheduled task."""
    now = datetime.now(UTC)
    start = now - timedelta(minutes=1)
    ts = datetime.now().timestamp()

    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"scheduled_task_{name_suffix}_{ts}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "0 * * * *",
                "start_date": start.isoformat(),
                "logical_date": start.isoformat(),
                "end_date": (start + timedelta(days=365)).isoformat(),
                "attached_config_lauis": [config_laui],
            },
        ),
    )
    assert resp.status_code == 200
    return CreateItemResponse(**resp.json()).item_laui


def create_adhoc_task(
    client: TestClient,
    workflow_laui: str,
    operator_laui: str,
    connection_laui: str,
    project_laui: str,
    account_laui: str,
    name_suffix: str = "",
) -> str:
    """Create an ADHOC task."""
    ts = datetime.now().timestamp()
    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"adhoc_task_{name_suffix}_{ts}",
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
    assert resp.status_code == 200
    return CreateItemResponse(**resp.json()).item_laui


async def test_two_workflows_both_scheduled_and_adhoc(client: TestClient):
    """Test case 5: 2 active workflows with both ADHOC and scheduled tasks, return scheduled from both."""
    ctx = setup_test_environment(client=client, workflow_2_state="active")

    # Workflow 1: Create 3 scheduled and 2 ADHOC tasks
    wf1_scheduled = []
    for i in range(3):
        laui = create_scheduled_task(
            client,
            ctx.workflow_1_laui,
            ctx.python_operator_1_laui,
            ctx.python_connection_1_laui,
            ctx.task_config_laui,
            ctx.project_laui,
            ctx.account_laui,
            f"wf1_scheduled_{i}",
        )
        wf1_scheduled.append(laui)

    wf1_adhoc = []
    for i in range(2):
        laui = create_adhoc_task(
            client,
            ctx.workflow_1_laui,
            ctx.python_operator_1_laui,
            ctx.python_connection_1_laui,
            ctx.project_laui,
            ctx.account_laui,
            f"wf1_adhoc_{i}",
        )
        wf1_adhoc.append(laui)

    # Workflow 2: Create 4 scheduled and 3 ADHOC tasks
    wf2_scheduled = []
    for i in range(4):
        laui = create_scheduled_task(
            client,
            ctx.workflow_2_laui,
            ctx.python_operator_2_laui,
            ctx.python_connection_2_laui,
            ctx.task_config_laui,
            ctx.project_laui,
            ctx.account_laui,
            f"wf2_scheduled_{i}",
        )
        wf2_scheduled.append(laui)

    wf2_adhoc = []
    for i in range(3):
        laui = create_adhoc_task(
            client,
            ctx.workflow_2_laui,
            ctx.python_operator_2_laui,
            ctx.python_connection_2_laui,
            ctx.project_laui,
            ctx.account_laui,
            f"wf2_adhoc_{i}",
        )
        wf2_adhoc.append(laui)

    # Query for tasks ready to run
    resp = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/catalog/get/tasks_ready_to_run/{ctx.project_laui}", method="get"
        ),
    )
    assert resp.status_code == 200
    tasks_ready = resp.json()

    # Should return 7 scheduled tasks (3 from wf1 + 4 from wf2)
    assert len(tasks_ready) == 7, (
        f"Expected 7 scheduled tasks from both workflows, got {len(tasks_ready)}"
    )

    ready_task_lauis = [task["laui"] for task in tasks_ready]

    # Verify all scheduled tasks from both workflows are returned
    for task in wf1_scheduled + wf2_scheduled:
        assert task in ready_task_lauis, f"Scheduled task {task} not found in ready tasks"

    # Verify ADHOC tasks are NOT returned
    for task in wf1_adhoc + wf2_adhoc:
        assert task not in ready_task_lauis, f"ADHOC task {task} should NOT be in ready tasks"


async def test_two_workflows_one_paused_returns_active_only(client: TestClient):
    """Test case 6: 2 workflows (1 paused, 1 active), both with scheduled tasks, return only active workflow tasks."""
    ctx = setup_test_environment(client=client, workflow_2_state="PAUSE")

    # Workflow 1 (active): Create 5 scheduled tasks
    wf1_scheduled = []
    for i in range(5):
        laui = create_scheduled_task(
            client,
            ctx.workflow_1_laui,
            ctx.python_operator_1_laui,
            ctx.python_connection_1_laui,
            ctx.task_config_laui,
            ctx.project_laui,
            ctx.account_laui,
            f"wf1_active_{i}",
        )
        wf1_scheduled.append(laui)

    # Workflow 2 (PAUSED): Create 5 scheduled tasks
    wf2_scheduled = []
    for i in range(5):
        laui = create_scheduled_task(
            client,
            ctx.workflow_2_laui,
            ctx.python_operator_2_laui,
            ctx.python_connection_2_laui,
            ctx.task_config_laui,
            ctx.project_laui,
            ctx.account_laui,
            f"wf2_paused_{i}",
        )
        wf2_scheduled.append(laui)

    # Query for tasks ready to run
    resp = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/catalog/get/tasks_ready_to_run/{ctx.project_laui}", method="get"
        ),
    )
    assert resp.status_code == 200
    tasks_ready = resp.json()

    # Should return only 5 tasks from active workflow
    assert len(tasks_ready) == 5, (
        f"Expected 5 tasks from active workflow only, got {len(tasks_ready)}"
    )

    ready_task_lauis = [task["laui"] for task in tasks_ready]

    # Verify all active workflow tasks are returned
    for task in wf1_scheduled:
        assert task in ready_task_lauis, f"Active workflow task {task} not found in ready tasks"

    # Verify NO paused workflow tasks are returned
    for task in wf2_scheduled:
        assert task not in ready_task_lauis, (
            f"Paused workflow task {task} should NOT be in ready tasks"
        )


async def test_paused_workflow_with_scheduled_returns_empty(client: TestClient):
    """Test case 7: Single paused workflow with scheduled tasks, return empty list."""
    ctx = setup_test_environment(client=client, workflow_2_state="PAUSE")

    # Create 10 scheduled tasks in the PAUSED workflow 2
    paused_tasks = []
    for i in range(10):
        laui = create_scheduled_task(
            client,
            ctx.workflow_2_laui,
            ctx.python_operator_2_laui,
            ctx.python_connection_2_laui,
            ctx.task_config_laui,
            ctx.project_laui,
            ctx.account_laui,
            f"paused_{i}",
        )
        paused_tasks.append(laui)

    # Query for tasks ready to run
    resp = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/catalog/get/tasks_ready_to_run/{ctx.project_laui}", method="get"
        ),
    )
    assert resp.status_code == 200
    tasks_ready = resp.json()

    # Should return 0 tasks since only workflow is paused
    assert len(tasks_ready) == 0, f"Expected 0 tasks from paused workflow, got {len(tasks_ready)}"
