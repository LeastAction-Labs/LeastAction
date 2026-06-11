# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
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
class ProjectContext:
    """Container for a single project's resources"""

    account_laui: str = ""
    project_laui: str = ""
    workflow_1_laui: str = ""
    workflow_2_laui: str = ""
    python_operator_1_laui: str = ""
    python_operator_2_laui: str = ""
    python_connection_1_laui: str = ""
    python_connection_2_laui: str = ""
    task_config_laui: str = ""


def setup_project_with_workflows(
    client: TestClient,
    project_suffix: str,
    workflow_1_state: str = "active",
    workflow_2_state: str = "active",
) -> ProjectContext:
    """Create a complete project with 2 workflows, operators, connections, and configs."""
    ctx = ProjectContext()
    ts = datetime.now().timestamp()

    base_folders = create_base_folders(client)
    ctx.account_laui = base_folders.account_folder_laui

    # Project
    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.project",
                "name": f"test_project_{project_suffix}_{ts}",
                "parent_laui": ctx.account_laui,
                "account_laui": ctx.account_laui,
            },
        ),
    )
    assert resp.status_code == 200
    ctx.project_laui = CreateItemResponse(**resp.json()).item_laui

    # Workflow 1
    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.workflow",
                "name": f"workflow_1_{project_suffix}_{ts}",
                "parent_laui": ctx.project_laui,
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
                "folder_metadata": {"state": workflow_1_state},
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
                "name": f"workflow_2_{project_suffix}_{ts}",
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
                "name": f"python_operator_1_{project_suffix}_{ts}",
                "parent_laui": ctx.workflow_1_laui,
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
                "codeblock": {
                    "main.py": "def initialize(self):\n    return {}\ndef run(self, ctx):\n    return {'status': 'ok', 'execution_type': 'sync'}\ndef check_completion(self, ctx, state):\n    return {'status': 'done'}\ndef finish(self, ctx, state, result):\n    return None\n"
                },
                "bashblock": {"main.sh": f"echo 'project_{project_suffix}_workflow1'"},
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
                "name": f"python_operator_2_{project_suffix}_{ts}",
                "parent_laui": ctx.workflow_2_laui,
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
                "codeblock": {
                    "main.py": "def initialize(self):\n    return {}\ndef run(self, ctx):\n    return {'status': 'ok', 'execution_type': 'sync'}\ndef check_completion(self, ctx, state):\n    return {'status': 'done'}\ndef finish(self, ctx, state, result):\n    return None\n"
                },
                "bashblock": {"main.sh": f"echo 'project_{project_suffix}_workflow2'"},
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
                "name": f"python_connection_1_{project_suffix}_{ts}",
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
                "name": f"python_connection_2_{project_suffix}_{ts}",
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
                "name": f"task_config_{project_suffix}_{ts}",
                "parent_laui": ctx.workflow_1_laui,
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
                "config_type": "task",
                "content": {"parameters": {"DB_HOST": f"localhost_{project_suffix}"}},
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
            url="/api/v1/catalog/create",
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
            url="/api/v1/catalog/create",
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


async def test_multiple_projects_isolated_scheduled_tasks(client: TestClient):
    """Test that get_tasks_ready_to_run returns tasks only for the specified project."""
    # Setup Project A
    proj_a = setup_project_with_workflows(client=client, project_suffix="A")
    proj_a_tasks = []

    # Project A - Workflow 1: 3 scheduled + 2 ADHOC
    for i in range(3):
        laui = create_scheduled_task(
            client,
            proj_a.workflow_1_laui,
            proj_a.python_operator_1_laui,
            proj_a.python_connection_1_laui,
            proj_a.task_config_laui,
            proj_a.project_laui,
            proj_a.account_laui,
            f"projA_wf1_scheduled_{i}",
        )
        proj_a_tasks.append(laui)

    for i in range(2):
        create_adhoc_task(
            client,
            proj_a.workflow_1_laui,
            proj_a.python_operator_1_laui,
            proj_a.python_connection_1_laui,
            proj_a.project_laui,
            proj_a.account_laui,
            f"projA_wf1_adhoc_{i}",
        )

    # Project A - Workflow 2: 3 scheduled + 2 ADHOC
    for i in range(3):
        laui = create_scheduled_task(
            client,
            proj_a.workflow_2_laui,
            proj_a.python_operator_2_laui,
            proj_a.python_connection_2_laui,
            proj_a.task_config_laui,
            proj_a.project_laui,
            proj_a.account_laui,
            f"projA_wf2_scheduled_{i}",
        )
        proj_a_tasks.append(laui)

    for i in range(2):
        create_adhoc_task(
            client,
            proj_a.workflow_2_laui,
            proj_a.python_operator_2_laui,
            proj_a.python_connection_2_laui,
            proj_a.project_laui,
            proj_a.account_laui,
            f"projA_wf2_adhoc_{i}",
        )

    # Setup Project B
    proj_b = setup_project_with_workflows(client=client, project_suffix="B")
    proj_b_tasks = []

    # Project B - Workflow 1: 4 scheduled + 1 ADHOC
    for i in range(4):
        laui = create_scheduled_task(
            client,
            proj_b.workflow_1_laui,
            proj_b.python_operator_1_laui,
            proj_b.python_connection_1_laui,
            proj_b.task_config_laui,
            proj_b.project_laui,
            proj_b.account_laui,
            f"projB_wf1_scheduled_{i}",
        )
        proj_b_tasks.append(laui)

    create_adhoc_task(
        client,
        proj_b.workflow_1_laui,
        proj_b.python_operator_1_laui,
        proj_b.python_connection_1_laui,
        proj_b.project_laui,
        proj_b.account_laui,
        "projB_wf1_adhoc_0",
    )

    # Project B - Workflow 2: 4 scheduled + 1 ADHOC
    for i in range(4):
        laui = create_scheduled_task(
            client,
            proj_b.workflow_2_laui,
            proj_b.python_operator_2_laui,
            proj_b.python_connection_2_laui,
            proj_b.task_config_laui,
            proj_b.project_laui,
            proj_b.account_laui,
            f"projB_wf2_scheduled_{i}",
        )
        proj_b_tasks.append(laui)

    create_adhoc_task(
        client,
        proj_b.workflow_2_laui,
        proj_b.python_operator_2_laui,
        proj_b.python_connection_2_laui,
        proj_b.project_laui,
        proj_b.account_laui,
        "projB_wf2_adhoc_0",
    )

    # Setup Project C
    proj_c = setup_project_with_workflows(client=client, project_suffix="C")
    proj_c_tasks = []

    # Project C - Workflow 1: 2 scheduled + 3 ADHOC
    for i in range(2):
        laui = create_scheduled_task(
            client,
            proj_c.workflow_1_laui,
            proj_c.python_operator_1_laui,
            proj_c.python_connection_1_laui,
            proj_c.task_config_laui,
            proj_c.project_laui,
            proj_c.account_laui,
            f"projC_wf1_scheduled_{i}",
        )
        proj_c_tasks.append(laui)

    for i in range(3):
        create_adhoc_task(
            client,
            proj_c.workflow_1_laui,
            proj_c.python_operator_1_laui,
            proj_c.python_connection_1_laui,
            proj_c.project_laui,
            proj_c.account_laui,
            f"projC_wf1_adhoc_{i}",
        )

    # Project C - Workflow 2: 2 scheduled + 3 ADHOC
    for i in range(2):
        laui = create_scheduled_task(
            client,
            proj_c.workflow_2_laui,
            proj_c.python_operator_2_laui,
            proj_c.python_connection_2_laui,
            proj_c.task_config_laui,
            proj_c.project_laui,
            proj_c.account_laui,
            f"projC_wf2_scheduled_{i}",
        )
        proj_c_tasks.append(laui)

    for i in range(3):
        create_adhoc_task(
            client,
            proj_c.workflow_2_laui,
            proj_c.python_operator_2_laui,
            proj_c.python_connection_2_laui,
            proj_c.project_laui,
            proj_c.account_laui,
            f"projC_wf2_adhoc_{i}",
        )

    # Query for Project B tasks only
    resp = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/catalog/get/tasks_ready_to_run/{proj_b.project_laui}", method="get"
        ),
    )
    assert resp.status_code == 200
    tasks_ready = resp.json()

    # Should return only 8 scheduled tasks from Project B (4 from wf1 + 4 from wf2)
    assert len(tasks_ready) == 8, (
        f"Expected 8 scheduled tasks from Project B only, got {len(tasks_ready)}"
    )

    ready_task_lauis = [task["laui"] for task in tasks_ready]

    # Verify all Project B scheduled tasks are returned
    for task in proj_b_tasks:
        assert task in ready_task_lauis, f"Project B scheduled task {task} not found in ready tasks"

    # Verify NO tasks from Project A are returned
    for task in proj_a_tasks:
        assert task not in ready_task_lauis, (
            f"Project A task {task} should NOT be in Project B's ready tasks"
        )

    # Verify NO tasks from Project C are returned
    for task in proj_c_tasks:
        assert task not in ready_task_lauis, (
            f"Project C task {task} should NOT be in Project B's ready tasks"
        )


async def test_multiple_projects_mixed_workflow_states(client: TestClient):
    """Test project isolation with mixed workflow states across projects."""
    # Setup Project A (workflow 1 active, workflow 2 paused)
    proj_a = setup_project_with_workflows(
        client=client, project_suffix="A", workflow_1_state="active", workflow_2_state="PAUSE"
    )
    proj_a_wf1_tasks = []
    proj_a_wf2_tasks = []

    for i in range(5):
        laui = create_scheduled_task(
            client,
            proj_a.workflow_1_laui,
            proj_a.python_operator_1_laui,
            proj_a.python_connection_1_laui,
            proj_a.task_config_laui,
            proj_a.project_laui,
            proj_a.account_laui,
            f"projA_wf1_active_{i}",
        )
        proj_a_wf1_tasks.append(laui)

    for i in range(5):
        laui = create_scheduled_task(
            client,
            proj_a.workflow_2_laui,
            proj_a.python_operator_2_laui,
            proj_a.python_connection_2_laui,
            proj_a.task_config_laui,
            proj_a.project_laui,
            proj_a.account_laui,
            f"projA_wf2_paused_{i}",
        )
        proj_a_wf2_tasks.append(laui)

    # Setup Project B (workflow 1 paused, workflow 2 active)
    proj_b = setup_project_with_workflows(
        client=client, project_suffix="B", workflow_1_state="PAUSE", workflow_2_state="active"
    )
    proj_b_wf1_tasks = []
    proj_b_wf2_tasks = []

    for i in range(5):
        laui = create_scheduled_task(
            client,
            proj_b.workflow_1_laui,
            proj_b.python_operator_1_laui,
            proj_b.python_connection_1_laui,
            proj_b.task_config_laui,
            proj_b.project_laui,
            proj_b.account_laui,
            f"projB_wf1_paused_{i}",
        )
        proj_b_wf1_tasks.append(laui)

    for i in range(5):
        laui = create_scheduled_task(
            client,
            proj_b.workflow_2_laui,
            proj_b.python_operator_2_laui,
            proj_b.python_connection_2_laui,
            proj_b.task_config_laui,
            proj_b.project_laui,
            proj_b.account_laui,
            f"projB_wf2_active_{i}",
        )
        proj_b_wf2_tasks.append(laui)

    # Setup Project C (both workflows active)
    proj_c = setup_project_with_workflows(
        client=client, project_suffix="C", workflow_1_state="active", workflow_2_state="active"
    )
    proj_c_tasks = []

    for i in range(5):
        laui = create_scheduled_task(
            client,
            proj_c.workflow_1_laui,
            proj_c.python_operator_1_laui,
            proj_c.python_connection_1_laui,
            proj_c.task_config_laui,
            proj_c.project_laui,
            proj_c.account_laui,
            f"projC_wf1_active_{i}",
        )
        proj_c_tasks.append(laui)

    for i in range(5):
        laui = create_scheduled_task(
            client,
            proj_c.workflow_2_laui,
            proj_c.python_operator_2_laui,
            proj_c.python_connection_2_laui,
            proj_c.task_config_laui,
            proj_c.project_laui,
            proj_c.account_laui,
            f"projC_wf2_active_{i}",
        )
        proj_c_tasks.append(laui)

    # Test Project A: should get 5 tasks from active workflow 1 only
    resp_a = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/catalog/get/tasks_ready_to_run/{proj_a.project_laui}", method="get"
        ),
    )
    assert resp_a.status_code == 200
    tasks_a = resp_a.json()
    assert len(tasks_a) == 5, (
        f"Expected 5 tasks from Project A's active workflow, got {len(tasks_a)}"
    )

    ready_a_lauis = [task["laui"] for task in tasks_a]
    for task in proj_a_wf1_tasks:
        assert task in ready_a_lauis, f"Project A active workflow task {task} not found"
    for task in proj_a_wf2_tasks:
        assert task not in ready_a_lauis, (
            f"Project A paused workflow task {task} should NOT be returned"
        )

    # Test Project B: should get 5 tasks from active workflow 2 only
    resp_b = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/catalog/get/tasks_ready_to_run/{proj_b.project_laui}", method="get"
        ),
    )
    assert resp_b.status_code == 200
    tasks_b = resp_b.json()
    assert len(tasks_b) == 5, (
        f"Expected 5 tasks from Project B's active workflow, got {len(tasks_b)}"
    )

    ready_b_lauis = [task["laui"] for task in tasks_b]
    for task in proj_b_wf2_tasks:
        assert task in ready_b_lauis, f"Project B active workflow task {task} not found"
    for task in proj_b_wf1_tasks:
        assert task not in ready_b_lauis, (
            f"Project B paused workflow task {task} should NOT be returned"
        )

    # Test Project C: should get 10 tasks from both active workflows
    resp_c = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/catalog/get/tasks_ready_to_run/{proj_c.project_laui}", method="get"
        ),
    )
    assert resp_c.status_code == 200
    tasks_c = resp_c.json()
    assert len(tasks_c) == 10, (
        f"Expected 10 tasks from Project C's both active workflows, got {len(tasks_c)}"
    )

    ready_c_lauis = [task["laui"] for task in tasks_c]
    for task in proj_c_tasks:
        assert task in ready_c_lauis, f"Project C task {task} not found"

    # Verify no cross-project contamination
    for task in proj_a_wf1_tasks + proj_a_wf2_tasks:
        assert task not in ready_b_lauis, (
            f"Project A task {task} should NOT be in Project B results"
        )
        assert task not in ready_c_lauis, (
            f"Project A task {task} should NOT be in Project C results"
        )

    for task in proj_b_wf1_tasks + proj_b_wf2_tasks:
        assert task not in ready_a_lauis, (
            f"Project B task {task} should NOT be in Project A results"
        )
        assert task not in ready_c_lauis, (
            f"Project B task {task} should NOT be in Project C results"
        )

    for task in proj_c_tasks:
        assert task not in ready_a_lauis, (
            f"Project C task {task} should NOT be in Project A results"
        )
        assert task not in ready_b_lauis, (
            f"Project C task {task} should NOT be in Project B results"
        )
