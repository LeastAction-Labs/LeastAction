# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
"""
Integration tests for the task run API endpoint (/api/v1/task/run).

These tests verify that:
1. Valid tasks can be executed successfully
2. Only tasks (item_type="task") can be executed
3. Task execution validates both creation and execution requirements
4. Proper error handling for invalid requests
5. Task is created and validated before execution

NOTE: The run API creates a task first, then validates task execution.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.core.catalog.api_request import CreateItemResponse, GetItemsResponse
from src.core.db.types import MongoDatabase
from src.core.task.connection.schema import ConnectionMetrics, SortOrder
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
async def workflow_laui(client: TestClient, account_laui: str, project_laui: str) -> str:
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
    client: TestClient, account_laui: str, project_laui: str, workflow_laui: str
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
                "codeblock": {"main.py": codeblock},
                "bashblock": {},
            },
        ),
    )
    assert op_resp.status_code == 200
    return CreateItemResponse(**op_resp.json()).item_laui


@pytest.fixture
async def connection_laui(
    client: TestClient, account_laui: str, project_laui: str, workflow_laui: str
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
                "content": connection,
                "max_parallelism": 2,
                "sort_dict": {"priority": SortOrder.ASC},
            },
        ),
    )
    assert connection_resp.status_code == 200
    return CreateItemResponse(**connection_resp.json()).item_laui


@pytest.fixture
async def payload_laui(
    client: TestClient, account_laui: str, project_laui: str, workflow_laui: str
) -> str:
    """Create a payload item in the workflow"""
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
                "content": '{"path": "/tmp/e2e_test_output.txt", "message": "e2e testing", "append": false}',
            },
        ),
    )
    assert payload_resp.status_code == 200
    return CreateItemResponse(**payload_resp.json()).item_laui


TASK_PRIORITY = 1


def _create_task(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
    payload_laui: str,
):
    global TASK_PRIORITY
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_scheduled_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "payload_laui": payload_laui,
                "state": TaskState.SCHEDULED,
                "frequency": "*/15 * * * *",
                "start_date": datetime.now(UTC).isoformat(),
                "end_date": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
                "priority": TASK_PRIORITY,
            },
        ),
    )
    assert task_resp.status_code == 200
    TASK_PRIORITY += 1
    return CreateItemResponse(**task_resp.json()).item_laui


async def test_run_task_with_adhoc_frequency_pass(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
    payload_laui: str,
):

    task_1_laui = _create_task(
        client,
        operator_laui,
        connection_laui,
        workflow_laui,
        project_laui,
        account_laui,
        payload_laui,
    )
    task_2_laui = _create_task(
        client,
        operator_laui,
        connection_laui,
        workflow_laui,
        project_laui,
        account_laui,
        payload_laui,
    )
    task_3_laui = _create_task(
        client,
        operator_laui,
        connection_laui,
        workflow_laui,
        project_laui,
        account_laui,
        payload_laui,
    )
    task_4_laui = _create_task(
        client,
        operator_laui,
        connection_laui,
        workflow_laui,
        project_laui,
        account_laui,
        payload_laui,
    )
    task_lauis = [task_1_laui, task_2_laui, task_3_laui, task_4_laui]

    tasks_ready_resp = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/catalog/get/tasks_ready_to_run/{project_laui}", method="get"
        ),
    )
    assert tasks_ready_resp.status_code == 200
    tasks_ready = tasks_ready_resp.json()
    assert len(tasks_ready) == 4

    # Execute multiple tasks via API endpoint
    execute_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/multiple_tasks",
            method="post",
            json={"task_lauis": [str(laui) for laui in task_lauis]},
        ),
    )
    assert execute_resp.status_code == 200

    for task_laui in task_lauis:
        task_resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/catalog/get", method="get", params={"item_laui": task_laui}
            ),
        )
        assert task_resp.status_code == 200
        task = task_resp.json()
        if task_laui in [task_1_laui, task_2_laui]:
            assert task["state"] in [TaskState.QUEUED_IN_REDIS, TaskState.RUNNING]
        else:
            assert task["state"] == TaskState.QUEUED_FOR_CONNECTION

    connection_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": connection_laui}
        ),
    )
    assert connection_resp.status_code == 200
    connection_metrics = ConnectionMetrics(**connection_resp.json())
    assert connection_metrics.current_parallelism == 2
    assert connection_metrics.in_queue == 2

    cq_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={
                "item_laui": connection_laui,
                "parent_or_child": "child",
                "item_type": "connection_queue",
            },
        ),
    )
    assert cq_resp.status_code == 200
    item_nodes = GetItemsResponse(**cq_resp.json()).items
    connection_queues = [item_node.item for item_node in item_nodes]
    assert len(connection_queues) == 4

    cq_task_lauis = [str(cq.task_laui) for cq in connection_queues]
    assert sorted(cq_task_lauis) == sorted(task_lauis)

    import time

    time.sleep(5)

    for task_laui in task_lauis:
        task_resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/catalog/get", method="get", params={"item_laui": task_laui}
            ),
        )
        assert task_resp.status_code == 200
        task = task_resp.json()
        if task_laui in [task_1_laui, task_2_laui]:
            assert task["state"] in [TaskState.SUCCESS, TaskState.ERROR]
        else:
            assert task["state"] == TaskState.QUEUED_FOR_CONNECTION

    connection_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": connection_laui}
        ),
    )
    assert connection_resp.status_code == 200
    connection_metrics = ConnectionMetrics(**connection_resp.json())
    assert connection_metrics.current_parallelism == 0
    assert connection_metrics.in_queue == 2

    cq_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={
                "item_laui": connection_laui,
                "parent_or_child": "child",
                "item_type": "connection_queue",
            },
        ),
    )
    assert cq_resp.status_code == 200
    item_nodes = GetItemsResponse(**cq_resp.json()).items
    connection_queues = [item_node.item for item_node in item_nodes]
    assert len(connection_queues) == 2
    cq_task_lauis = [str(cq.task_laui) for cq in connection_queues]
    assert sorted(cq_task_lauis) == sorted(task_lauis[2:])

    # Execute multiple tasks with empty list via API endpoint
    execute_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/multiple_tasks", method="post", json={"task_lauis": []}
        ),
    )
    assert execute_resp.status_code == 200

    time.sleep(5)

    for task_laui in task_lauis:
        task_resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/catalog/get", method="get", params={"item_laui": task_laui}
            ),
        )
        assert task_resp.status_code == 200
        assert task_resp.json()["state"] in [TaskState.SUCCESS, TaskState.ERROR]

    connection_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": connection_laui}
        ),
    )
    assert connection_resp.status_code == 200
    connection_metrics = ConnectionMetrics(**connection_resp.json())
    assert connection_metrics.current_parallelism == 0
    assert connection_metrics.in_queue == 0

    cq_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={
                "item_laui": connection_laui,
                "parent_or_child": "child",
                "item_type": "connection_queue",
            },
        ),
    )
    assert cq_resp.status_code == 200
    item_nodes = GetItemsResponse(**cq_resp.json()).items
    connection_queues = [item_node.item for item_node in item_nodes]
    assert len(connection_queues) == 0


def load_code_block():
    path = Path(__file__)
    codeblock_path = path.parent.parent / "celery/task-test-data/operator.py"

    return codeblock_path.read_text(encoding="utf-8")


codeblock = load_code_block()

connection = {"type": "docker"}
