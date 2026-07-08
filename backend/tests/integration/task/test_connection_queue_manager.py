# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic_mongo import PydanticObjectId

from src.common.context_vars.user_context import set_user_laui
from src.core.catalog.api_request import CreateItemResponse
from src.core.catalog.item.schema import Item
from src.core.db.transaction import (
    TransactionManager,
    transaction_manager_context,
)
from src.core.db.types import MongoDatabase
from src.core.task.connection.connection_queue_manager import ConnectionQueueManager
from src.core.task.connection.connection_queue_repo import ConnectionQueueRepository
from src.core.task.connection.schema import ConnectionMetrics, SortOrder
from src.core.task.schema import TaskState
from tests.integration.schema import BaseFolders, TestRequest
from tests.integration.utils import create_base_folders, execute_request, get_user_laui

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def database_cleanup(test_database: MongoDatabase, client: TestClient):
    """Clean database before and after each test"""
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
                "content": {"type": "docker"},
            },
        ),
    )
    assert connection_resp.status_code == 200
    return CreateItemResponse(**connection_resp.json()).item_laui


@pytest.fixture
async def payload_laui(
    client: TestClient, workflow_laui: str, account_laui: str, project_laui: str
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
                "content": '{"test": "data"}',
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
            url="/api/v1/task",
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


@pytest.fixture
async def tasks(
    test_database: MongoDatabase,
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
    payload_laui: str,
):
    global TASK_PRIORITY
    TASK_PRIORITY = 1
    task_lauis = []
    for _ in range(0, 3):
        task_lauis.append(
            PydanticObjectId(
                _create_task(
                    client,
                    operator_laui,
                    connection_laui,
                    workflow_laui,
                    project_laui,
                    account_laui,
                    payload_laui,
                )
            )
        )
    items = await test_database.items.find({"_id": {"$in": task_lauis}}).to_list(length=None)
    tasks = []
    for item in items:
        tasks.append(Item(**item))
    return tasks


@pytest.fixture
async def connection_queue_repo(test_database: MongoDatabase):
    user_laui = await get_user_laui()
    set_user_laui(user_laui)
    transaction_manager = TransactionManager(client=test_database)
    transaction_manager_context.set(transaction_manager)
    return ConnectionQueueRepository(test_database)


@pytest.fixture
async def connection_queue_manager(connection_queue_repo):
    """Create a ConnectionQueueManager instance"""
    return ConnectionQueueManager(connection_queue_repo)


async def test_priority_descending(test_database, connection_queue_manager, connection_laui, tasks):
    connection_laui = PydanticObjectId(connection_laui)
    await test_database.items.update_one(
        {"_id": connection_laui}, {"$set": {"sort_dict": {"priority": SortOrder.DESC}}}
    )
    result = await connection_queue_manager.load_balance_tasks(tasks)
    assert len(result) == 3
    # Should be sorted by priority descending
    assert result[0].priority == 3
    assert result[1].priority == 2
    assert result[2].priority == 1


async def test_priority_ascending(test_database, connection_queue_manager, connection_laui, tasks):
    connection_laui = PydanticObjectId(connection_laui)
    await test_database.items.update_one(
        {"_id": connection_laui}, {"$set": {"sort_dict": {"priority": SortOrder.ASC}}}
    )
    result = await connection_queue_manager.load_balance_tasks(tasks)
    assert len(result) == 3
    # Should be sorted by priority ascending
    assert result[0].priority == 1
    assert result[1].priority == 2
    assert result[2].priority == 3


async def test_max_parallelism_limit(
    connection_queue_manager, tasks, connection_laui, test_database: MongoDatabase
):
    max_parallelism = 2
    connection_laui = PydanticObjectId(connection_laui)
    await test_database.items.update_one({"_id": connection_laui}, {"$set": {"max_parallelism": 2}})
    result = await connection_queue_manager.load_balance_tasks(tasks)
    assert len(result) == max_parallelism
    connection = ConnectionMetrics(**await test_database.items.find_one({"_id": connection_laui}))
    assert connection.current_parallelism == 2
    assert connection.in_queue == 1
    assert connection.max_parallelism == max_parallelism
