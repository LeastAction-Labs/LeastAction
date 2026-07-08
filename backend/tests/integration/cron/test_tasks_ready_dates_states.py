# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
"""Date and state filtering tests for find_tasks_ready_to_run endpoint."""

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

    project_laui: str = ""
    account_laui: str = ""
    workflow_laui: str = ""
    python_operator_laui: str = ""
    python_connection_laui: str = ""
    task_config_laui: str = ""


def setup_test_environment(client: TestClient) -> TestContext:
    """Create test environment with project, workflow, operator, connection, and config."""
    ctx = TestContext()
    ts = datetime.now().timestamp()

    # Account
    base_folders = create_base_folders(client)
    ctx.account_laui = base_folders.account_folder_laui
    ctx.project_laui = base_folders.project_folder_laui

    # Workflow
    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.workflow",
                "name": f"workflow_{ts}",
                "parent_laui": ctx.project_laui,
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
                "folder_metadata": {"state": "active"},
            },
        ),
    )
    assert resp.status_code == 200
    ctx.workflow_laui = CreateItemResponse(**resp.json()).item_laui

    # Python operator
    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "operator.python",
                "name": f"python_operator_{ts}",
                "parent_laui": ctx.workflow_laui,
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
                "parent_laui": ctx.workflow_laui,
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
                "parent_laui": ctx.workflow_laui,
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


# INCORRECT TEST CASE
# async def test_all_future_logical_date_returns_empty(client: TestClient):
#     """Test case 8: All scheduled tasks with future logical_date, return empty list."""
#     ctx = setup_test_environment(client=client)
#     now = datetime.now(timezone.utc)
#     ts = datetime.now().timestamp()
#
#     # Create 10 tasks with future logical_date
#     future_tasks = []
#     for i in range(10):
#         resp = execute_request(client=client, request=TestRequest(url="/api/v1/catalog/create", method="post", json={
#                 "item_type": "task",
#                 "name": f"task_{i}_{ts}",
#                 "project_laui": ctx.project_laui,
#                 "account_laui": ctx.account_laui,
#                 "parent_laui": ctx.workflow_laui,
#                 "operator_laui": ctx.python_operator_laui,
#                 "connection_laui": ctx.python_connection_laui,
#                 "state": "scheduled",
#                 "frequency": "15 * * * *",
#                 "start_date": (now - timedelta(days=1)).isoformat(),
#                 "end_date": (now + timedelta(days=365)).isoformat(),
#                 "logical_date": (now + timedelta(hours=1)).isoformat(),  # Future logical_date
#                 "attached_config_lauis": [ctx.task_config_laui],
#             }))
#         assert resp.status_code == 200
#         future_tasks.append(CreateItemResponse(**resp.json()).item_laui)
#
#     # Query for tasks ready to run
#     resp = execute_request(
#         client=client,
#         request=TestRequest(url=f"/api/v1/catalog/get/tasks_ready_to_run/{ctx.project_laui}",method='get')
#     )
#     assert resp.status_code == 200
#     tasks_ready = resp.json()
#
#     assert (
#         len(tasks_ready) == 0
#     ), f"Expected 0 tasks when all have future logical_date, got {len(tasks_ready)}"

# INCORRECT TEST CASE
# async def test_half_past_half_future_logical_date(client: TestClient):
#     """Test case 9: Half tasks with past logical_date, half with future, return only past tasks."""
#     ctx = setup_test_environment(client=client)
#     now = datetime.now(timezone.utc)
#     ts = datetime.now().timestamp()
#
#     # Create 5 tasks with past logical_date
#     past_tasks = []
#     for i in range(5):
#         resp = execute_request(client=client, request=TestRequest(url="/api/v1/catalog/create", method="post", json={
#                 "item_type": "task",
#                 "name": f"past_task_{i}_{ts}",
#                 "project_laui": ctx.project_laui,
#                 "account_laui": ctx.account_laui,
#                 "parent_laui": ctx.workflow_laui,
#                 "operator_laui": ctx.python_operator_laui,
#                 "connection_laui": ctx.python_connection_laui,
#                 "state": "scheduled",
#                 "frequency": "0 * * * *",
#                 "start_date": (now - timedelta(days=1)).isoformat(),
#                 "end_date": (now + timedelta(days=365)).isoformat(),
#                 "logical_date": (now - timedelta(minutes=30)).isoformat(),  # Past logical_date
#                 "attached_config_lauis": [ctx.task_config_laui],
#             }))
#         assert resp.status_code == 200
#         past_tasks.append(CreateItemResponse(**resp.json()).item_laui)
#
#     # Create 5 tasks with future logical_date
#     future_tasks = []
#     for i in range(5):
#         resp = execute_request(client=client, request=TestRequest(url="/api/v1/catalog/create", method="post", json={
#                 "item_type": "task",
#                 "name": f"future_task_{i}_{ts}",
#                 "project_laui": ctx.project_laui,
#                 "account_laui": ctx.account_laui,
#                 "parent_laui": ctx.workflow_laui,
#                 "operator_laui": ctx.python_operator_laui,
#                 "connection_laui": ctx.python_connection_laui,
#                 "state": "scheduled",
#                 "frequency": "0 * * * *",
#                 "start_date": (now - timedelta(days=1)).isoformat(),
#                 "end_date": (now + timedelta(days=365)).isoformat(),
#                 "logical_date": (now + timedelta(hours=1)).isoformat(),  # Future logical_date
#                 "attached_config_lauis": [ctx.task_config_laui],
#             }))
#         assert resp.status_code == 200
#         future_tasks.append(CreateItemResponse(**resp.json()).item_laui)
#
#     # Query for tasks ready to run
#     resp = execute_request(
#         client=client,
#         request=TestRequest(url=f"/api/v1/catalog/get/tasks_ready_to_run/{ctx.project_laui}",method='get')
#     )
#     assert resp.status_code == 200
#     tasks_ready = resp.json()
#
#     assert (
#         len(tasks_ready) == 5
#     ), f"Expected 5 tasks with past logical_date, got {len(tasks_ready)}"
#
#     ready_task_lauis = [task["laui"] for task in tasks_ready]
#
#     # Verify only past tasks are returned
#     for task in past_tasks:
#         assert (
#             task in ready_task_lauis
#         ), f"Past task {task} not found in ready tasks"
#
#     # Verify future tasks are NOT returned
#     for task in future_tasks:
#         assert (
#             task not in ready_task_lauis
#         ), f"Future task {task} should NOT be in ready tasks"


# async def test_state_filtering_error_vs_scheduled_success(client: TestClient):
#     """Test case 10: Tasks with state=['error', 'scheduled', 'success'], return only ['scheduled', 'success','created']."""
#     ctx = setup_test_environment(client=client)
#     now = datetime.now(timezone.utc)
#     ts = datetime.now().timestamp()

#     # Create 3 tasks with state='error'
#     error_tasks = []
#     for i in range(3):
#         resp = execute_request(client=client, request=TestRequest(url="/api/v1/catalog/create", method="post", json={
#                 "item_type": "task",
#                 "name": f"error_task_{i}_{ts}",
#                 "project_laui": ctx.project_laui,
#                 "account_laui": ctx.account_laui,
#                 "parent_laui": ctx.workflow_laui,
#                 "operator_laui": ctx.python_operator_laui,
#                 "connection_laui": ctx.python_connection_laui,
#                 "state": "error",
#                 "frequency": "0 * * * *",
#                 "start_date": (now - timedelta(days=1)).isoformat(),
#                 "end_date": (now + timedelta(days=365)).isoformat(),
#                 "logical_date": (now - timedelta(minutes=30)).isoformat(),
#                 "attached_config_lauis": [ctx.task_config_laui],
#             }))
#         assert resp.status_code == 200
#         error_tasks.append(CreateItemResponse(**resp.json()).item_laui)

#     # Create 4 tasks with state='scheduled'
#     scheduled_tasks = []
#     for i in range(4):
#         resp = execute_request(client=client, request=TestRequest(url="/api/v1/catalog/create", method="post", json={
#                 "item_type": "task",
#                 "name": f"scheduled_task_{i}_{ts}",
#                 "project_laui": ctx.project_laui,
#                 "account_laui": ctx.account_laui,
#                 "parent_laui": ctx.workflow_laui,
#                 "operator_laui": ctx.python_operator_laui,
#                 "connection_laui": ctx.python_connection_laui,
#                 "state": "scheduled",
#                 "frequency": "0 * * * *",
#                 "start_date": (now - timedelta(days=1)).isoformat(),
#                 "end_date": (now + timedelta(days=365)).isoformat(),
#                 "logical_date": (now - timedelta(minutes=30)).isoformat(),
#                 "attached_config_lauis": [ctx.task_config_laui],
#             }))
#         assert resp.status_code == 200
#         scheduled_tasks.append(CreateItemResponse(**resp.json()).item_laui)

#     # Create 3 tasks with state='success'
#     success_tasks = []
#     for i in range(3):
#         resp = execute_request(client=client, request=TestRequest(url="/api/v1/catalog/create", method="post", json={
#                 "item_type": "task",
#                 "name": f"success_task_{i}_{ts}",
#                 "project_laui": ctx.project_laui,
#                 "account_laui": ctx.account_laui,
#                 "parent_laui": ctx.workflow_laui,
#                 "operator_laui": ctx.python_operator_laui,
#                 "connection_laui": ctx.python_connection_laui,
#                 "state": "success",
#                 "frequency": "0 * * * *",
#                 "start_date": (now - timedelta(days=1)).isoformat(),
#                 "end_date": (now + timedelta(days=365)).isoformat(),
#                 "logical_date": (now - timedelta(minutes=30)).isoformat(),
#                 "attached_config_lauis": [ctx.task_config_laui],
#             }))
#         assert resp.status_code == 200
#         success_tasks.append(CreateItemResponse(**resp.json()).item_laui)

#     # Query for tasks ready to run
#     resp = execute_request(
#         client=client,
#         request=TestRequest(url=f"/api/v1/catalog/get/tasks_ready_to_run/{ctx.project_laui}",method='get')
#     )
#     assert resp.status_code == 200
#     tasks_ready = resp.json()

#     # Should return 7 tasks (4 scheduled + 3 success, excluding 3 error)
#     assert (
#         len(tasks_ready) == 7
#     ), f"Expected 7 tasks (scheduled + success), got {len(tasks_ready)}"

#     ready_task_lauis = [task["laui"] for task in tasks_ready]

#     # Verify scheduled and success tasks are returned
#     for task in scheduled_tasks + success_tasks:
#         assert (
#             task in ready_task_lauis
#         ), f"Task {task} with valid state not found in ready tasks"

#     # Verify error tasks are NOT returned
#     for task in error_tasks:
#         assert (
#             task not in ready_task_lauis
#         ), f"Error task {task} should NOT be in ready tasks"


async def test_user_set_state_cancel_excluded(client: TestClient):
    """Test case 11: Tasks with user_set_state='cancel' should not be returned."""
    ctx = setup_test_environment(client=client)
    now = datetime.now(UTC)
    ts = datetime.now().timestamp()

    # Create 5 normal scheduled tasks (no user_set_state)
    normal_tasks = []
    for i in range(5):
        resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/task",
                method="post",
                json={
                    "item_type": "task",
                    "name": f"normal_task_{i}_{ts}",
                    "project_laui": ctx.project_laui,
                    "account_laui": ctx.account_laui,
                    "parent_laui": ctx.workflow_laui,
                    "operator_laui": ctx.python_operator_laui,
                    "connection_laui": ctx.python_connection_laui,
                    "state": "scheduled",
                    "frequency": "0 * * * *",
                    "start_date": (now - timedelta(days=1)).isoformat(),
                    "end_date": (now + timedelta(days=365)).isoformat(),
                    "logical_date": (now - timedelta(minutes=30)).isoformat(),
                    "attached_config_lauis": [ctx.task_config_laui],
                },
            ),
        )
        assert resp.status_code == 200
        normal_tasks.append(CreateItemResponse(**resp.json()).item_laui)

    # Create 5 cancelled tasks (user_set_state='cancel')
    cancelled_tasks = []
    for i in range(5):
        resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/task",
                method="post",
                json={
                    "item_type": "task",
                    "name": f"cancelled_task_{i}_{ts}",
                    "project_laui": ctx.project_laui,
                    "account_laui": ctx.account_laui,
                    "parent_laui": ctx.workflow_laui,
                    "operator_laui": ctx.python_operator_laui,
                    "connection_laui": ctx.python_connection_laui,
                    "state": "scheduled",
                    "frequency": "0 * * * *",
                    "start_date": (now - timedelta(days=1)).isoformat(),
                    "end_date": (now + timedelta(days=365)).isoformat(),
                    "logical_date": (now - timedelta(minutes=30)).isoformat(),
                    "user_set_state": "cancel",  # User cancelled
                    "attached_config_lauis": [ctx.task_config_laui],
                },
            ),
        )
        assert resp.status_code == 200
        cancelled_tasks.append(CreateItemResponse(**resp.json()).item_laui)

    # Query for tasks ready to run
    resp = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/catalog/get/tasks_ready_to_run/{ctx.project_laui}", method="get"
        ),
    )
    assert resp.status_code == 200
    tasks_ready = resp.json()

    # Should return only 5 normal tasks
    assert len(tasks_ready) == 5, (
        f"Expected 5 normal tasks (cancelled excluded), got {len(tasks_ready)}"
    )

    ready_task_lauis = [task["laui"] for task in tasks_ready]

    # Verify normal tasks are returned
    for task in normal_tasks:
        assert task in ready_task_lauis, f"Normal task {task} not found in ready tasks"

    # Verify cancelled tasks are NOT returned
    for task in cancelled_tasks:
        assert task not in ready_task_lauis, f"Cancelled task {task} should NOT be in ready tasks"


async def test_deleted_tasks_not_returned(client: TestClient):
    """Test case 12: Soft-deleted tasks should not be returned."""

    ctx = setup_test_environment(client=client)
    now = datetime.now(UTC)
    ts = datetime.now().timestamp()

    # Create 5 normal tasks
    normal_tasks = []
    for i in range(5):
        resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/task",
                method="post",
                json={
                    "item_type": "task",
                    "name": f"normal_task_{i}_{ts}",
                    "project_laui": ctx.project_laui,
                    "account_laui": ctx.account_laui,
                    "parent_laui": ctx.workflow_laui,
                    "operator_laui": ctx.python_operator_laui,
                    "connection_laui": ctx.python_connection_laui,
                    "state": "scheduled",
                    "frequency": "0 * * * *",
                    "start_date": (now - timedelta(days=1)).isoformat(),
                    "end_date": (now + timedelta(days=365)).isoformat(),
                    "logical_date": (now - timedelta(minutes=30)).isoformat(),
                    "attached_config_lauis": [ctx.task_config_laui],
                },
            ),
        )
        assert resp.status_code == 200
        normal_tasks.append(CreateItemResponse(**resp.json()).item_laui)

    # Create 5 tasks and delete them
    deleted_tasks = []
    for i in range(5):
        resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/task",
                method="post",
                json={
                    "item_type": "task",
                    "name": f"deleted_task_{i}_{ts}",
                    "project_laui": ctx.project_laui,
                    "account_laui": ctx.account_laui,
                    "parent_laui": ctx.workflow_laui,
                    "operator_laui": ctx.python_operator_laui,
                    "connection_laui": ctx.python_connection_laui,
                    "state": "scheduled",
                    "frequency": "0 * * * *",
                    "start_date": (now - timedelta(days=1)).isoformat(),
                    "end_date": (now + timedelta(days=365)).isoformat(),
                    "logical_date": (now - timedelta(minutes=30)).isoformat(),
                    "attached_config_lauis": [ctx.task_config_laui],
                },
            ),
        )
        assert resp.status_code == 200
        task_laui = CreateItemResponse(**resp.json()).item_laui
        deleted_tasks.append(task_laui)

        # Delete the task
        delete_resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/catalog/delete",
                method="post",
                json={"item_laui": task_laui, "parent_laui": ctx.workflow_laui},
            ),
        )
        assert delete_resp.status_code == 200

    # Query for tasks ready to run
    resp = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/catalog/get/tasks_ready_to_run/{ctx.project_laui}", method="get"
        ),
    )
    assert resp.status_code == 200
    tasks_ready = resp.json()

    # Should return only 5 normal tasks
    assert len(tasks_ready) == 5, (
        f"Expected 5 normal tasks (deleted excluded), got {len(tasks_ready)}"
    )

    ready_task_lauis = [task["laui"] for task in tasks_ready]

    # Verify normal tasks are returned
    for task in normal_tasks:
        assert task in ready_task_lauis, f"Normal task {task} not found in ready tasks"

    # Verify deleted tasks are NOT returned
    for task in deleted_tasks:
        assert task not in ready_task_lauis, f"Deleted task {task} should NOT be in ready tasks"


# INCORRECT TEST CASE
# async def test_past_end_date_not_returned(client: TestClient):
#     """Test case 13: Tasks past end_date should not be returned."""
#     ctx = setup_test_environment(client=client)
#     now = datetime.now(timezone.utc)
#     ts = datetime.now().timestamp()
#
#     # Create 5 tasks with valid end_date
#     valid_tasks = []
#     for i in range(5):
#         resp = execute_request(client=client, request=TestRequest(url="/api/v1/catalog/create", method="post", json={
#                 "item_type": "task",
#                 "name": f"valid_task_{i}_{ts}",
#                 "project_laui": ctx.project_laui,
#                 "account_laui": ctx.account_laui,
#                 "parent_laui": ctx.workflow_laui,
#                 "operator_laui": ctx.python_operator_laui,
#                 "connection_laui": ctx.python_connection_laui,
#                 "state": "scheduled",
#                 "frequency": "0 * * * *",
#                 "start_date": (now - timedelta(days=1)).isoformat(),
#                 "end_date": (now + timedelta(days=365)).isoformat(),  # Future end_date
#                 "logical_date": (now - timedelta(minutes=30)).isoformat(),
#                 "attached_config_lauis": [ctx.task_config_laui],
#             }))
#         assert resp.status_code == 200
#         valid_tasks.append(CreateItemResponse(**resp.json()).item_laui)
#
#     # Create 5 tasks with past end_date
#     expired_tasks = []
#     for i in range(5):
#         resp = execute_request(client=client, request=TestRequest(url="/api/v1/catalog/create", method="post", json={
#                 "item_type": "task",
#                 "name": f"expired_task_{i}_{ts}",
#                 "project_laui": ctx.project_laui,
#                 "account_laui": ctx.account_laui,
#                 "parent_laui": ctx.workflow_laui,
#                 "operator_laui": ctx.python_operator_laui,
#                 "connection_laui": ctx.python_connection_laui,
#                 "state": "scheduled",
#                 "frequency": "0 * * * *",
#                 "start_date": (now - timedelta(days=10)).isoformat(),
#                 "end_date": (now - timedelta(days=1)).isoformat(),  # Past end_date
#                 "logical_date": (now - timedelta(minutes=30)).isoformat(),
#                 "attached_config_lauis": [ctx.task_config_laui],
#             }))
#         assert resp.status_code == 200
#         expired_tasks.append(CreateItemResponse(**resp.json()).item_laui)
#
#     # Query for tasks ready to run
#     resp = execute_request(
#         client=client,
#         request=TestRequest(url=f"/api/v1/catalog/get/tasks_ready_to_run/{ctx.project_laui}",method='get')
#     )
#     assert resp.status_code == 200
#     tasks_ready = resp.json()
#
#     # Should return only 5 valid tasks
#     assert (
#         len(tasks_ready) == 5
#     ), f"Expected 5 valid tasks (expired excluded), got {len(tasks_ready)}"
#
#     ready_task_lauis = [task["laui"] for task in tasks_ready]
#
#     # Verify valid tasks are returned
#     for task in valid_tasks:
#         assert (
#             task in ready_task_lauis
#         ), f"Valid task {task} not found in ready tasks"
#
#     # Verify expired tasks are NOT returned
#     for task in expired_tasks:
#         assert (
#             task not in ready_task_lauis
#         ), f"Expired task {task} should NOT be in ready tasks"


async def test_future_start_date_not_returned(client: TestClient):
    """Test case 14: Tasks with future start_date should not be returned."""
    ctx = setup_test_environment(client=client)
    now = datetime.now(UTC)
    ts = datetime.now().timestamp()

    # Create 5 tasks with past start_date (already started)
    started_tasks = []
    for i in range(5):
        resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/task",
                method="post",
                json={
                    "item_type": "task",
                    "name": f"started_task_{i}_{ts}",
                    "project_laui": ctx.project_laui,
                    "account_laui": ctx.account_laui,
                    "parent_laui": ctx.workflow_laui,
                    "operator_laui": ctx.python_operator_laui,
                    "connection_laui": ctx.python_connection_laui,
                    "state": "scheduled",
                    "frequency": "0 * * * *",
                    "start_date": (now - timedelta(days=1)).isoformat(),  # Past start_date
                    "end_date": (now + timedelta(days=365)).isoformat(),
                    "logical_date": (now - timedelta(minutes=30)).isoformat(),
                    "attached_config_lauis": [ctx.task_config_laui],
                },
            ),
        )
        assert resp.status_code == 200
        started_tasks.append(CreateItemResponse(**resp.json()).item_laui)

    # Create 5 tasks with future start_date (not started yet)
    future_tasks = []
    for i in range(5):
        resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/task",
                method="post",
                json={
                    "item_type": "task",
                    "name": f"future_start_task_{i}_{ts}",
                    "project_laui": ctx.project_laui,
                    "account_laui": ctx.account_laui,
                    "parent_laui": ctx.workflow_laui,
                    "operator_laui": ctx.python_operator_laui,
                    "connection_laui": ctx.python_connection_laui,
                    "state": "scheduled",
                    "frequency": "0 * * * *",
                    "start_date": (now + timedelta(days=1)).isoformat(),  # Future start_date
                    "end_date": (now + timedelta(days=365)).isoformat(),
                    "logical_date": (now - timedelta(minutes=30)).isoformat(),
                    "attached_config_lauis": [ctx.task_config_laui],
                },
            ),
        )
        assert resp.status_code == 200
        future_tasks.append(CreateItemResponse(**resp.json()).item_laui)

    # Query for tasks ready to run
    resp = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/catalog/get/tasks_ready_to_run/{ctx.project_laui}", method="get"
        ),
    )
    assert resp.status_code == 200
    tasks_ready = resp.json()

    # Should return only 5 started tasks
    assert len(tasks_ready) == 5, (
        f"Expected 5 started tasks (future excluded), got {len(tasks_ready)}"
    )

    ready_task_lauis = [task["laui"] for task in tasks_ready]

    # Verify started tasks are returned
    for task in started_tasks:
        assert task in ready_task_lauis, f"Started task {task} not found in ready tasks"

    # Verify future tasks are NOT returned
    for task in future_tasks:
        assert task not in ready_task_lauis, f"Future task {task} should NOT be in ready tasks"
