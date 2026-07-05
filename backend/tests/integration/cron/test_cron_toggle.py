# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from src.core.catalog.api_request import CreateItemResponse
from src.core.db.types import MongoDatabase
from src.core.task.connection.schema import SortOrder
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

    project_laui: str = ""
    account_laui: str = ""
    workflow_laui: str = ""
    operator_laui: str = ""
    connection_laui: str = ""
    python_operator_laui: str = ""
    task_config_laui: str = ""
    workflow_config_laui: str = ""
    pass_payload_laui: str = ""
    fail_payload_laui: str = ""
    task_lauis: list = field(default_factory=list)
    task_with_retry_lauis: list = field(default_factory=list)
    task_without_retry_lauis: list = field(default_factory=list)


async def get_test_context(client: TestClient) -> TestContext:
    ctx: TestContext = TestContext()
    base_folders = create_base_folders(client)
    ctx.account_laui = base_folders.account_folder_laui
    ctx.project_laui = base_folders.project_folder_laui
    wf_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.workflow",
                "name": f"workflow_{datetime.now().timestamp()}",
                "parent_laui": ctx.project_laui,
                "folder_metadata": {"state": "active"},
            },
        ),
    )
    assert wf_resp.status_code == 200
    ctx.workflow_laui = CreateItemResponse(**wf_resp.json()).item_laui
    op_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "operator.python",
                "name": f"python_operator_{datetime.now().timestamp()}",
                "parent_laui": ctx.workflow_laui,
                "codeblock": {"main.py": codeblock},
                "bashblock": {"main.sh": bashblock},
            },
        ),
    )
    assert op_resp.status_code == 200
    ctx.operator_laui = CreateItemResponse(**op_resp.json()).item_laui
    connection_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "connection.python",
                "name": f"python_connection_{datetime.now().timestamp()}",
                "parent_laui": ctx.workflow_laui,
                "content": {},
                "max_parallelism": 20,
                "sort_dict": {"priority": SortOrder.ASC},
            },
        ),
    )
    assert connection_resp.status_code == 200
    ctx.connection_laui = CreateItemResponse(**connection_resp.json()).item_laui
    payload_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "payload.json",
                "name": f"payload_{datetime.now().timestamp()}",
                "parent_laui": ctx.workflow_laui,
                "content": '"fail"',
            },
        ),
    )
    assert payload_resp.status_code == 200
    ctx.fail_payload_laui = CreateItemResponse(**payload_resp.json()).item_laui
    payload_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "payload.json",
                "name": f"payload_{datetime.now().timestamp()}",
                "parent_laui": ctx.workflow_laui,
                "content": '"pass"',
            },
        ),
    )
    assert payload_resp.status_code == 200
    ctx.pass_payload_laui = CreateItemResponse(**payload_resp.json()).item_laui
    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "config",
                "name": "task_config",
                "parent_laui": ctx.workflow_laui,
                "config_type": "task",
                "content": {
                    "total_retries": 5,
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
                "name": "workflow_config",
                "parent_laui": ctx.workflow_laui,
                "config_type": "system",
                "content": {"parameters": {"LOG_LEVEL": "INFO", "TIMEOUT": "300"}},
            },
        ),
    )
    assert resp.status_code == 200
    ctx.workflow_config_laui = CreateItemResponse(**resp.json()).item_laui
    ctx.task_with_retry_lauis = []
    ctx.task_without_retry_lauis = []
    now = datetime.now(UTC)
    start = now - timedelta(minutes=1)
    for i in range(0, 20):
        task_resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/task/run",
                method="post",
                json={
                    "item_type": "task",
                    "name": f"task_scheduled_{i}",
                    "project_laui": ctx.project_laui,
                    "account_laui": ctx.account_laui,
                    "parent_laui": ctx.workflow_laui,
                    "operator_laui": ctx.operator_laui,
                    "connection_laui": ctx.connection_laui,
                    "payload_laui": ctx.fail_payload_laui,
                    "start_date": start.isoformat(),
                    "end_date": (now + timedelta(days=365)).isoformat(),
                    "state": "scheduled",
                    "frequency": "*/15 * * * *",
                    "attached_config_lauis": [ctx.task_config_laui]
                    if i < 10
                    else [ctx.workflow_config_laui],
                },
            ),
        )
        assert task_resp.status_code == 200
        if i < 10:
            ctx.task_with_retry_lauis.append(
                ObjectId(CreateItemResponse(**task_resp.json()).item_laui)
            )
        else:
            ctx.task_without_retry_lauis.append(
                ObjectId(CreateItemResponse(**task_resp.json()).item_laui)
            )
    ctx.task_with_retry_lauis = sorted(ctx.task_with_retry_lauis)
    ctx.task_without_retry_lauis = sorted(ctx.task_without_retry_lauis)
    ctx.task_lauis = ctx.task_without_retry_lauis + ctx.task_with_retry_lauis
    return ctx


def manage_cron(client: TestClient, project_laui: str, action: str):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/cron/manage",
            method="post",
            json={"project_laui": project_laui, "action": action},
        ),
    )
    assert response.status_code == 200


async def test_retry(
    client: TestClient,
    test_database: MongoDatabase,
):
    ctx: TestContext = await get_test_context(client)
    count = 1
    while count < 100:
        print(f"checking cron toggle:- iteration {count}")

        manage_cron(client, ctx.project_laui, "START")
        print("starting cron")
        start_cron_iteration = 1
        current_time = datetime.now(UTC)
        cron_latest_heartbeat = (
            await test_database.items.find_one({"_id": ObjectId(ctx.project_laui)})
        )["folder_metadata"]["latest_heartbeat"]
        while datetime.fromisoformat(cron_latest_heartbeat) < current_time:
            print(f"checking cron started or not , time passed :{start_cron_iteration} seconds")
            cron_latest_heartbeat = (
                await test_database.items.find_one({"_id": ObjectId(ctx.project_laui)})
            )["folder_metadata"]["latest_heartbeat"]
            start_cron_iteration += 1
            await asyncio.sleep(1)
        print("cron started")

        manage_cron(client, ctx.project_laui, "STOP")
        print("stopping cron")
        stop_cron_iteration = 1
        cron_status = (await test_database.items.find_one({"_id": ObjectId(ctx.project_laui)}))[
            "folder_metadata"
        ]["cron_status"]
        while cron_status != "STOPPED":
            print(f"checking cron stopped or not , time passed :{stop_cron_iteration} seconds")
            cron_status = (await test_database.items.find_one({"_id": ObjectId(ctx.project_laui)}))[
                "folder_metadata"
            ]["cron_status"]
            stop_cron_iteration += 1
            await asyncio.sleep(1)
        print("cron stopped")

        count += 1

        await test_database.items.update_many(
            {"_id": {"$in": ctx.task_lauis}},
            {
                "$set": {
                    "state": "scheduled",
                    "start_date": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
                }
            },
        )

        await asyncio.sleep(5)


def load_code_block():
    path = Path(__file__)
    codeblock_path = path.parent.parent / "task/celery/task-test-data/conditional_fail_operator.py"

    return codeblock_path.read_text(encoding="utf-8")


codeblock = load_code_block()

bashblock = """
pip install requests==2.31.*
python3 -c "import requests; print(f'requests version: {requests.__version__}')"
echo "Dependencies installed successfully"
"""
