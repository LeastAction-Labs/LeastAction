# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from src.core.catalog.api_request import CreateItemResponse
from src.core.cron.schema import CronAction
from src.core.db.types import MongoDatabase
from tests.integration.schema import TestRequest
from tests.integration.utils import create_base_folders, execute_request

pytestmark = pytest.mark.anyio

# Track projects that need cleanup
_projects_to_cleanup = []


def register_project_for_cleanup(project_laui: str):
    """Register a project for cleanup after test"""
    global _projects_to_cleanup
    if project_laui not in _projects_to_cleanup:
        _projects_to_cleanup.append(project_laui)


@pytest.fixture(autouse=True)
async def cron_cleanup(client):
    """Cleanup cron jobs before database cleanup - runs BEFORE database_cleanup"""
    import asyncio

    global _projects_to_cleanup
    _projects_to_cleanup = []  # Reset for this test

    yield  # Test runs here

    # Stop all cron jobs that were started during the test
    for project_laui in _projects_to_cleanup:
        await cleanup_cron(client, project_laui)

    # Extra wait to ensure all Celery workers have stopped
    await asyncio.sleep(1.0)


@pytest.fixture(autouse=True)
async def database_cleanup(test_database: MongoDatabase, cron_cleanup, client: TestClient):
    """Clean database - depends on cron_cleanup to run first"""
    import asyncio

    # Cleanup before test
    await test_database.items.drop()
    await test_database.links.delete_many({})
    # Small delay to ensure cleanup is complete
    await asyncio.sleep(0.1)
    yield  # Test runs here (cron_cleanup already completed)
    # Cleanup after test
    await test_database.items.drop()
    await test_database.links.drop()


@dataclass
class TestContext:
    """Container for all test resources"""

    project_laui: str = ""
    account_laui: str = ""
    workflow_1_laui: str = ""
    workflow_2_laui: str = ""
    python_operator_laui: str = ""
    spark_operator_laui: str = ""
    python_connection_laui: str = ""
    spark_connection_laui: str = ""
    task_config_laui: str = ""
    workflow_config_laui: str = ""
    payload_laui: str = ""
    runtime_param_config_laui: str = ""
    task_lauis: list = field(default_factory=list)


def setup_test_environment(
    client: TestClient,
    include_workflows: bool = True,
    include_operators: bool = True,
    include_connections: bool = True,
    include_configs: bool = False,
    include_payload: bool = False,
) -> TestContext:
    """
    Create test environment with configurable components.
    """
    ctx = TestContext()
    ts = datetime.now().timestamp()

    base_folders = create_base_folders(client)
    ctx.account_laui = base_folders.account_folder_laui
    ctx.project_laui = base_folders.project_folder_laui

    if not include_workflows:
        return ctx

    # Workflows
    for i, attr in enumerate(["workflow_1_laui", "workflow_2_laui"], 1):
        resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/catalog/create",
                method="post",
                json={
                    "item_type": "folder.workflow",
                    "name": f"workflow_{i}_{ts}",
                    "parent_laui": ctx.project_laui,
                    "account_laui": ctx.account_laui,
                    "project_laui": ctx.project_laui,
                    "folder_metadata": {"state": "active"},
                },
            ),
        )
        assert resp.status_code == 200
        setattr(ctx, attr, CreateItemResponse(**resp.json()).item_laui)

    if include_operators:
        for op_type, attr in [
            ("python", "python_operator_laui"),
            ("spark", "spark_operator_laui"),
        ]:
            resp = execute_request(
                client=client,
                request=TestRequest(
                    url="/api/v1/catalog/create",
                    method="post",
                    json={
                        "item_type": f"operator.{op_type}",
                        "name": f"{op_type}_operator_{ts}",
                        "parent_laui": ctx.workflow_1_laui,
                        "account_laui": ctx.account_laui,
                        "project_laui": ctx.project_laui,
                        "codeblock": {
                            "main.py": "def initialize(self):\n    return {}\ndef run(self, ctx):\n    return {'status': 'ok', 'execution_type': 'sync'}\ndef check_completion(self, ctx, state):\n    return {'status': 'done'}\ndef finish(self, ctx, state, result):\n    return None\n"
                        },
                        "bashblock": {
                            "main.sh": (
                                "echo 'test'" if op_type == "python" else "spark-submit test.py"
                            )
                        },
                    },
                ),
            )
            assert resp.status_code == 200
            setattr(ctx, attr, CreateItemResponse(**resp.json()).item_laui)

    if include_connections:
        for conn_type, _content, attr in [
            ("python", {"type": "docker"}, "python_connection_laui"),
            ("spark", {"type": "kubernetes"}, "spark_connection_laui"),
        ]:
            resp = execute_request(
                client=client,
                request=TestRequest(
                    url="/api/v1/catalog/create",
                    method="post",
                    json={
                        "item_type": f"connection.{conn_type}",
                        "name": f"{conn_type}_connection_{ts}",
                        "parent_laui": ctx.workflow_1_laui,
                        "account_laui": ctx.account_laui,
                        "project_laui": ctx.project_laui,
                        "content": {"a": "b"},
                    },
                ),
            )
            print(resp.json())
            assert resp.status_code == 200
            setattr(ctx, attr, CreateItemResponse(**resp.json()).item_laui)

    if include_configs:
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
                    "content": {
                        "total_retries": 3,
                        "retry_interval": 1,
                        "parameters": {"DB_HOST": "localhost", "DB_PORT": "5432"},
                    },
                },
            ),
        )
        assert resp.status_code == 200
        ctx.task_config_laui = CreateItemResponse(**resp.json()).item_laui

        # Workflow config
        resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/catalog/create",
                method="post",
                json={
                    "item_type": "config",
                    "name": f"workflow_config_{ts}",
                    "parent_laui": ctx.workflow_1_laui,
                    "account_laui": ctx.account_laui,
                    "project_laui": ctx.project_laui,
                    "config_type": "system",
                    "content": {"parameters": {"LOG_LEVEL": "INFO", "TIMEOUT": "300"}},
                },
            ),
        )
        assert resp.status_code == 200
        ctx.workflow_config_laui = CreateItemResponse(**resp.json()).item_laui

    if include_payload:
        resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/catalog/create",
                method="post",
                json={
                    "item_type": "payload.json",
                    "name": f"payload_{ts}",
                    "parent_laui": ctx.workflow_1_laui,
                    "account_laui": ctx.account_laui,
                    "project_laui": ctx.project_laui,
                    "content": '{"user": "{{username}}", "db": "{{DB_HOST}}"}',
                },
            ),
        )
        assert resp.status_code == 200
        ctx.payload_laui = CreateItemResponse(**resp.json()).item_laui

    # Register project for automatic cleanup if cron gets started
    register_project_for_cleanup(ctx.project_laui)

    return ctx


def create_scheduled_task(
    client: TestClient,
    ctx: TestContext,
    workflow_laui: str = None,
    operator_laui: str = None,
    connection_laui: str = None,
    name_suffix: str = "",
    frequency: str = "*/15 * * * *",
    attached_config_lauis: list = None,
) -> str:
    """Create a scheduled task using context defaults"""
    now = datetime.now(UTC)
    start = now - timedelta(minutes=1)
    ts = datetime.now().timestamp()

    data = {
        "item_type": "task",
        "name": f"task_{name_suffix}_{ts}",
        "project_laui": ctx.project_laui,
        "account_laui": ctx.account_laui,
        "parent_laui": workflow_laui or ctx.workflow_1_laui,
        "operator_laui": operator_laui or ctx.python_operator_laui,
        "connection_laui": connection_laui or ctx.python_connection_laui,
        "state": "scheduled",
        "frequency": frequency,
        "start_date": start.isoformat(),
        "end_date": (now + timedelta(days=365)).isoformat(),
    }
    if attached_config_lauis:
        data["attached_config_lauis"] = attached_config_lauis

    resp = execute_request(
        client=client, request=TestRequest(url="/api/v1/task", method="post", json=data)
    )
    assert resp.status_code == 200
    return CreateItemResponse(**resp.json()).item_laui


def create_adhoc_task(client: TestClient, ctx: TestContext, name_suffix: str = "") -> str:
    """Create an ADHOC task"""
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


async def cleanup_cron(client: TestClient, project_laui: str):
    """Helper to stop cron scheduler and wait for completion"""
    import asyncio

    # Track that we've cleaned this project
    global _projects_to_cleanup
    if project_laui in _projects_to_cleanup:
        _projects_to_cleanup.remove(project_laui)

    try:
        # Check if project still exists before trying to stop cron
        proj_check = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/catalog/get", method="get", params={"item_laui": project_laui}
            ),
        )

        # If project doesn't exist (404), nothing to clean up
        if proj_check.status_code == 404:
            await asyncio.sleep(1)
            return

        # Send stop signal (ignore 404 errors - project might have been deleted)
        stop_resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/cron/manage",
                method="post",
                json={"project_laui": project_laui, "action": CronAction.STOP},
            ),
        )

        # If stop returns 404, the cron isn't running or project is gone
        if stop_resp.status_code == 404:
            await asyncio.sleep(1)
            return

        # Poll for STOPPED status with timeout
        max_attempts = 20  # Increased from implicit 15 elsewhere
        for _attempt in range(max_attempts):
            try:
                proj_resp = execute_request(
                    client=client,
                    request=TestRequest(
                        url="/api/v1/catalog/get", method="get", params={"item_laui": project_laui}
                    ),
                )
                if proj_resp.status_code == 404:
                    # Project was deleted, we're done
                    await asyncio.sleep(0.5)
                    return
                if proj_resp.status_code == 200:
                    cron_status = proj_resp.json().get("folder_metadata", {}).get("cron_status")
                    if cron_status == "STOPPED":
                        # Give a bit more time for Celery cleanup
                        await asyncio.sleep(0.5)
                        return
            except Exception:
                pass
            await asyncio.sleep(0.5)

        # If we get here, timeout occurred - give extra buffer time
        await asyncio.sleep(2)
    except Exception:
        # Even if stop fails, wait to let any running tasks finish
        await asyncio.sleep(3)


async def test_get_tasks_ready_to_run_api(client: TestClient):
    """Test the tasks ready to run API endpoint returns correct tasks."""
    ctx = setup_test_environment(client=client, include_configs=True)
    datetime.now().timestamp()

    # Create valid scheduled tasks (5 per workflow)
    valid_tasks = []
    for wf in [ctx.workflow_1_laui, ctx.workflow_2_laui]:
        for i in range(5):
            laui = create_scheduled_task(
                client=client,
                ctx=ctx,
                workflow_laui=wf,
                name_suffix=f"valid_{i}",
                attached_config_lauis=[ctx.task_config_laui],
            )
            valid_tasks.append(laui)

    # Create ADHOC tasks (should NOT be in tasks_ready_to_run)
    for wf in [ctx.workflow_1_laui, ctx.workflow_2_laui]:
        for i in range(10):
            create_adhoc_task(client=client, ctx=ctx, name_suffix=f"{wf}_{i}")

    # Test find_tasks_ready_to_run API
    tasks_ready_resp = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/catalog/get/tasks_ready_to_run/{ctx.project_laui}", method="get"
        ),
    )
    assert tasks_ready_resp.status_code == 200
    tasks_ready = tasks_ready_resp.json()

    # Should find 10 valid scheduled tasks (ADHOC tasks should be excluded)
    assert len(tasks_ready) == 10, f"Expected 10 tasks ready to run, got {len(tasks_ready)}"

    # Verify all valid tasks are in the list
    ready_task_lauis = [task["laui"] for task in tasks_ready]
    for valid_task in valid_tasks:
        assert valid_task in ready_task_lauis, (
            f"Valid task {valid_task} not found in tasks ready to run"
        )
    await cleanup_cron(client, ctx.project_laui)


async def test_tasks_ready_excludes_deleted_dependencies(client: TestClient):
    """Test that tasks with deleted operators/connections are still returned."""
    ctx = setup_test_environment(client=client, include_configs=True)
    ts = datetime.now().timestamp()

    # Create valid task
    valid_task = create_scheduled_task(
        client=client, ctx=ctx, name_suffix="valid", attached_config_lauis=[ctx.task_config_laui]
    )

    # Create task with operator that will be deleted
    op_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "operator.python",
                "name": f"temp_op_{ts}",
                "parent_laui": ctx.workflow_1_laui,
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
                "codeblock": {
                    "main.py": "def initialize(self):\n    return {}\ndef run(self, ctx):\n    return {'status': 'ok', 'execution_type': 'sync'}\ndef check_completion(self, ctx, state):\n    return {'status': 'done'}\ndef finish(self, ctx, state, result):\n    return None\n"
                },
                "bashblock": {"main.sh": "echo 'temp'"},
            },
        ),
    )
    temp_op = CreateItemResponse(**op_resp.json()).item_laui
    deleted_op_task = create_scheduled_task(
        client=client, ctx=ctx, operator_laui=temp_op, name_suffix="deleted_op"
    )
    execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/delete",
            method="post",
            json={"item_laui": temp_op, "parent_laui": ctx.workflow_1_laui},
        ),
    )

    # Create task with connection that will be deleted
    conn_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "connection.python",
                "name": f"temp_conn_{ts}",
                "parent_laui": ctx.workflow_1_laui,
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
                "content": {"type": "docker"},
            },
        ),
    )
    temp_conn = CreateItemResponse(**conn_resp.json()).item_laui
    deleted_conn_task = create_scheduled_task(
        client=client, ctx=ctx, connection_laui=temp_conn, name_suffix="deleted_conn"
    )
    execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/delete",
            method="post",
            json={"item_laui": temp_conn, "parent_laui": ctx.workflow_1_laui},
        ),
    )

    # Get tasks ready to run
    tasks_ready_resp = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/catalog/get/tasks_ready_to_run/{ctx.project_laui}", method="get"
        ),
    )
    assert tasks_ready_resp.status_code == 200
    tasks_ready = tasks_ready_resp.json()

    # All 3 tasks should be returned (validation happens later in the pipeline)
    assert len(tasks_ready) == 3, f"Expected 3 tasks ready to run, got {len(tasks_ready)}"

    ready_task_lauis = [task["laui"] for task in tasks_ready]
    assert valid_task in ready_task_lauis
    assert deleted_op_task in ready_task_lauis
    assert deleted_conn_task in ready_task_lauis
    await cleanup_cron(client, ctx.project_laui)


async def test_paused_workflow_tasks_not_ready(client: TestClient):
    """Test that scheduled tasks from paused workflows are not returned as ready to run."""
    ctx = setup_test_environment(client=client, include_configs=True)
    ts = datetime.now().timestamp()

    # Create a paused workflow
    paused_workflow_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.workflow",
                "name": f"paused_workflow_{ts}",
                "parent_laui": ctx.project_laui,
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
                "folder_metadata": {"state": "PAUSE"},
            },
        ),
    )
    assert paused_workflow_resp.status_code == 200
    paused_workflow_laui = CreateItemResponse(**paused_workflow_resp.json()).item_laui

    # Create operator for paused workflow
    paused_op_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "operator.python",
                "name": f"paused_op_{ts}",
                "parent_laui": paused_workflow_laui,
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
                "codeblock": {
                    "main.py": "def initialize(self):\n    return {}\ndef run(self, ctx):\n    return {'status': 'ok', 'execution_type': 'sync'}\ndef check_completion(self, ctx, state):\n    return {'status': 'done'}\ndef finish(self, ctx, state, result):\n    return None\n"
                },
                "bashblock": {"main.sh": "echo 'paused'"},
            },
        ),
    )
    assert paused_op_resp.status_code == 200
    paused_operator_laui = CreateItemResponse(**paused_op_resp.json()).item_laui

    # Create connection for paused workflow
    paused_conn_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "connection.python",
                "name": f"paused_conn_{ts}",
                "parent_laui": paused_workflow_laui,
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
                "content": {"type": "docker"},
            },
        ),
    )
    assert paused_conn_resp.status_code == 200
    paused_connection_laui = CreateItemResponse(**paused_conn_resp.json()).item_laui

    # Create 10 scheduled tasks in the PAUSED workflow
    paused_tasks = []
    for i in range(10):
        now = datetime.now(UTC)
        start = now - timedelta(minutes=1)

        resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/task",
                method="post",
                json={
                    "item_type": "task",
                    "name": f"paused_task_{i}_{ts}",
                    "project_laui": ctx.project_laui,
                    "account_laui": ctx.account_laui,
                    "parent_laui": paused_workflow_laui,
                    "operator_laui": paused_operator_laui,
                    "connection_laui": paused_connection_laui,
                    "state": "scheduled",
                    "frequency": "0 * * * *",
                    "start_date": start.isoformat(),
                    "end_date": (now + timedelta(days=365)).isoformat(),
                    "attached_config_lauis": [ctx.task_config_laui],
                },
            ),
        )
        assert resp.status_code == 200
        paused_tasks.append(CreateItemResponse(**resp.json()).item_laui)

    # Create 5 valid scheduled tasks in an ACTIVE workflow (for comparison)
    valid_tasks = []
    for i in range(5):
        laui = create_scheduled_task(
            client=client,
            ctx=ctx,
            workflow_laui=ctx.workflow_1_laui,
            name_suffix=f"active_{i}",
            attached_config_lauis=[ctx.task_config_laui],
        )
        valid_tasks.append(laui)

    # Test find_tasks_ready_to_run API
    tasks_ready_resp = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/catalog/get/tasks_ready_to_run/{ctx.project_laui}", method="get"
        ),
    )
    assert tasks_ready_resp.status_code == 200
    tasks_ready = tasks_ready_resp.json()

    # Should only find 5 tasks from active workflow (none from paused workflow)
    assert len(tasks_ready) == 5, (
        f"Expected 5 tasks ready to run (from active workflow only), got {len(tasks_ready)}"
    )

    # Verify only active workflow tasks are in the list
    ready_task_lauis = [task["laui"] for task in tasks_ready]
    for valid_task in valid_tasks:
        assert valid_task in ready_task_lauis, (
            f"Active task {valid_task} not found in tasks ready to run"
        )

    # Verify NO paused workflow tasks are in the list
    for paused_task in paused_tasks:
        assert paused_task not in ready_task_lauis, (
            f"Paused task {paused_task} should NOT be in tasks ready to run"
        )
    await cleanup_cron(client, ctx.project_laui)
