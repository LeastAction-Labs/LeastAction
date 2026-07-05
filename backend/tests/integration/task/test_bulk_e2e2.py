# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.core.catalog.api_request import CreateItemResponse
from src.core.db.types import MongoDatabase
from src.core.task.connection.schema import ConnectionMetrics, SortOrder
from src.core.task.schema import TaskState
from tests.integration.schema import TestRequest
from tests.integration.utils import create_base_folders, execute_request

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def database_cleanup(test_database: MongoDatabase, client: TestClient):
    # await test_database.items.drop()
    # await test_database.links.delete_many({})
    yield  # Test runs here
    # await test_database.items.drop()
    # await test_database.links.drop()


async def setup(client: TestClient, test_database: MongoDatabase) -> list[str]:
    tasks = await test_database.items.find({"item_type": "task"}, {"_id": 1}).to_list(length=None)
    if len(tasks) != 0:
        return [str(task["_id"]) for task in tasks]
    else:
        base_folders = create_base_folders(client)
        account_laui = base_folders.account_folder_laui
        project_laui = base_folders.project_folder_laui
        wf_resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/catalog/create",
                method="post",
                json={
                    "item_type": "folder.workflow",
                    "name": f"workflow_{datetime.now().timestamp()}",
                    "parent_laui": project_laui,
                    "folder_metadata": {"state": "active"},
                },
            ),
        )
        assert wf_resp.status_code == 200
        workflow_laui = CreateItemResponse(**wf_resp.json()).item_laui
        op_resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/catalog/create",
                method="post",
                json={
                    "item_type": "operator.python",
                    "name": f"python_operator_{datetime.now().timestamp()}",
                    "parent_laui": workflow_laui,
                    "codeblock": {"main.py": codeblock},
                    "bashblock": {},
                },
            ),
        )
        assert op_resp.status_code == 200
        operator_laui = CreateItemResponse(**op_resp.json()).item_laui
        connection_resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/catalog/create",
                method="post",
                json={
                    "item_type": "connection.python",
                    "name": f"python_connection_{datetime.now().timestamp()}",
                    "parent_laui": workflow_laui,
                    "content": connection,
                    "max_parallelism": 20,
                    "sort_dict": {"priority": SortOrder.ASC},
                },
            ),
        )
        assert connection_resp.status_code == 200
        connection_laui = CreateItemResponse(**connection_resp.json()).item_laui
        payload_resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/catalog/create",
                method="post",
                json={
                    "item_type": "payload.json",
                    "name": f"payload_{datetime.now().timestamp()}",
                    "parent_laui": workflow_laui,
                    "content": '{"path": "/tmp/e2e_test_output.txt", "message": "e2e testing", "append": false}',
                },
            ),
        )
        assert payload_resp.status_code == 200
        payload_laui = CreateItemResponse(**payload_resp.json()).item_laui
        task_lauis = []
        for i in range(1, 101):
            task_resp = execute_request(
                client=client,
                request=TestRequest(
                    url="/api/v1/task/run",
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
                        "frequency": "* * * * *",
                        "start_date": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
                        "end_date": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
                        "priority": i,
                    },
                ),
            )
            assert task_resp.status_code == 200
            task_lauis.append(CreateItemResponse(**task_resp.json()).item_laui)
        return task_lauis


async def get_connection_metrics_and_cq_count(
    test_database: MongoDatabase,
) -> tuple[ConnectionMetrics, int]:
    from pymongo.read_concern import ReadConcern

    async with test_database.client_ref.start_session() as session:
        async with await session.start_transaction(read_concern=ReadConcern("majority")):
            connection = await test_database.items.find_one(
                {"item_type": "connection.python"}, session=session
            )
            cq_count = len(
                await (
                    test_database.items.find({"item_type": "connection_queue"}, session=session)
                ).to_list(length=None)
            )
            return (ConnectionMetrics(**connection), cq_count)


async def test_bulk(
    client: TestClient,
    test_database: MongoDatabase,
):
    await setup(client, test_database)
    project_laui = (await test_database.items.find_one({"item_type": "folder.project"}))["_id"]
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/cron/manage",
            method="post",
            json={"project_laui": str(project_laui), "action": "START"},
        ),
    )

    connection_metrics, cq_count = await get_connection_metrics_and_cq_count(test_database)

    while connection_metrics.in_queue == 0:
        print(connection_metrics)
        connection_metrics, cq_count = await get_connection_metrics_and_cq_count(test_database)
        await asyncio.sleep(5)

    while connection_metrics.in_queue > 0:
        print(connection_metrics)
        await asyncio.sleep(5)
        connection_metrics, cq_count = await get_connection_metrics_and_cq_count(test_database)
        assert connection_metrics.current_parallelism >= 0
        assert connection_metrics.in_queue >= 0

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/cron/manage",
            method="post",
            json={"project_laui": str(project_laui), "action": "STOP"},
        ),
    )
    assert response.status_code == 200


def load_code_block():
    path = Path(__file__)
    codeblock_path = path.parent / "celery/task-test-data/operator.py"

    return codeblock_path.read_text(encoding="utf-8")


codeblock = load_code_block()

connection = {"type": "docker"}
