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
    config_folder_laui: str = ""
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
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
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
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
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
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
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
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
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
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
                "content": '"pass"',
            },
        ),
    )
    assert payload_resp.status_code == 200
    ctx.pass_payload_laui = CreateItemResponse(**payload_resp.json()).item_laui
    # Create folder.config under project to hold configs
    config_folder_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.config",
                "name": f"config_folder_{datetime.now().timestamp()}",
                "parent_laui": ctx.project_laui,
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
            },
        ),
    )
    assert config_folder_resp.status_code == 200
    ctx.config_folder_laui = CreateItemResponse(**config_folder_resp.json()).item_laui
    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "config",
                "name": "task_config",
                "parent_laui": ctx.config_folder_laui,
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
                "config_type": "task",
                "content": {
                    "total_retries": 5,
                    "retry_interval": 5,
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
                "parent_laui": ctx.config_folder_laui,
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
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
                url="/api/v1/task",
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
                    "frequency": "0 0 * * *",
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


def get_tasks_ready_to_run(client: TestClient, ctx: TestContext):
    response = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/catalog/get/tasks_ready_to_run/{ctx.project_laui}", method="get"
        ),
    )
    assert response.status_code == 200
    return response.json()


async def test_retry(
    client: TestClient,
    test_database: MongoDatabase,
):
    ctx = await get_test_context(client)

    tasks_ready_to_run = get_tasks_ready_to_run(client, ctx)
    assert len(tasks_ready_to_run) == 20

    manage_cron(client, ctx.project_laui, "START")
    # cron started , cron will pick the tasks and both will fail
    # we will keep checking until both task will fail

    tasks = await test_database.items.find({"_id": {"$in": ctx.task_lauis}}, {"state": 1}).to_list(
        length=None
    )
    task_states = [task["state"] for task in tasks]
    while not all(state == "error" for state in task_states):
        await asyncio.sleep(0.1)
        tasks = await test_database.items.find({"item_type": "task"}, {"state": 1}).to_list(
            length=None
        )
        task_states = [task["state"] for task in tasks]

    count = 1
    total_retries = 5
    # first iteration we will just check if 10 tasks with retry come in response of get tasks ready to run if retry interval passes and assert their retry_count == 1
    # second iteration we will do same asserts as 1st iteration but we will update payload lauis of first 5 tasks in tasks_ready_to_run at the end before starting cron
    # third iteration , we should get only 5 tasks in response of ready to retry and we will assert their retry_count and then we will assert retry_count of the tasks whose payload laui we changed their retry count should be reset to 0.
    # 4th iteration same as 1 just len will be 5
    # 5th iteration len of tasks ready to run should be 0
    while count <= total_retries:
        print(count)

        # the tasks got into error state
        tasks_ready_to_run = get_tasks_ready_to_run(client, ctx)
        assert len(tasks_ready_to_run) == 0

        # decrease last_run_date of all the tasks by 1 min to mimic time has passed
        # lets stop the cron first or otherwise cron might pick them first
        manage_cron(client, ctx.project_laui, "STOP")
        cron_status = (await test_database.items.find_one({"_id": ObjectId(ctx.project_laui)}))[
            "folder_metadata"
        ]["cron_status"]
        stop_attempts = 0
        max_stop_attempts = 30  # 30 seconds timeout
        while cron_status != "STOPPED":
            print(
                f"stopping cron (attempt {stop_attempts + 1}/{max_stop_attempts}), current status: {cron_status}"
            )
            if stop_attempts >= max_stop_attempts:
                project_metadata = await test_database.items.find_one(
                    {"_id": ObjectId(ctx.project_laui)}
                )
                raise TimeoutError(
                    f"Cron failed to stop after {max_stop_attempts} attempts. Final status: {cron_status}, Project metadata: {project_metadata.get('folder_metadata')}"
                )
            cron_status = (await test_database.items.find_one({"_id": ObjectId(ctx.project_laui)}))[
                "folder_metadata"
            ]["cron_status"]
            await asyncio.sleep(1)
            stop_attempts += 1

        await test_database.items.update_many(
            {"_id": {"$in": ctx.task_lauis}},
            [
                {
                    "$set": {
                        "last_run_date": {
                            "$dateSubtract": {
                                "startDate": "$last_run_date",
                                "unit": "minute",
                                "amount": 5,  # retry interval
                            }
                        }
                    }
                }
            ],
        )

        tasks_ready_to_run = get_tasks_ready_to_run(client, ctx)

        if count in [1, 2]:
            assert len(tasks_ready_to_run) == 10
            tasks_ready_to_run = sorted(tasks_ready_to_run, key=lambda task: task["laui"])
            for i in range(0, 10):
                assert tasks_ready_to_run[i]["laui"] == str(ctx.task_with_retry_lauis[i])
                assert tasks_ready_to_run[i]["retry_number"] == count

        if count == 3:
            assert len(tasks_ready_to_run) == 5
            tasks_ready_to_run = sorted(tasks_ready_to_run, key=lambda task: task["laui"])
            for i in range(0, 5):
                assert tasks_ready_to_run[i]["laui"] == str(ctx.task_with_retry_lauis[i + 5])
                assert tasks_ready_to_run[i]["retry_number"] == count

            tasks = await test_database.items.find(
                {"_id": {"$in": ctx.task_with_retry_lauis[:5]}}, {"retry_number": 1, "state": 1}
            ).to_list(length=None)
            for task in tasks:
                assert task["state"] == "success"
                assert task["retry_number"] == 0

        if count == 4:
            assert len(tasks_ready_to_run) == 5
            tasks_ready_to_run = sorted(tasks_ready_to_run, key=lambda task: task["laui"])
            for i in range(0, 5):
                assert tasks_ready_to_run[i]["laui"] == str(ctx.task_with_retry_lauis[i + 5])
                assert tasks_ready_to_run[i]["retry_number"] == count

        if count == 5:
            assert len(tasks_ready_to_run) == 0
            break

        if count == 2:
            # change payload_laui of first 5 retry tasks to pass_payload_laui
            await test_database.items.update_many(
                {"_id": {"$in": ctx.task_with_retry_lauis[:5]}},
                {"$set": {"payload_laui": ObjectId(ctx.pass_payload_laui)}},
            )
            # these tasks will pass on next execution since payload_laui now points to pass payload

        manage_cron(client, ctx.project_laui, "START")
        current_time = datetime.now(UTC)
        cron_latest_heartbeat = (
            await test_database.items.find_one({"_id": ObjectId(ctx.project_laui)})
        )["folder_metadata"]["latest_heartbeat"]
        while datetime.fromisoformat(cron_latest_heartbeat) < current_time:
            print("starting cron")
            cron_latest_heartbeat = (
                await test_database.items.find_one({"_id": ObjectId(ctx.project_laui)})
            )["folder_metadata"]["latest_heartbeat"]
            await asyncio.sleep(1)

        tasks_to_monitor = ctx.task_with_retry_lauis
        if count > 2:
            tasks_to_monitor = ctx.task_with_retry_lauis[5:]

        tasks = await test_database.items.find(
            {"_id": {"$in": tasks_to_monitor}}, {"last_run_date": 1}
        ).to_list(length=None)
        task_last_run_dates = [task["last_run_date"].replace(tzinfo=UTC) for task in tasks]
        # no we wait until all of them run
        while not all(last_run_date > current_time for last_run_date in task_last_run_dates):
            await asyncio.sleep(0.1)
            tasks = await test_database.items.find(
                {"_id": {"$in": tasks_to_monitor}}, {"last_run_date": 1}
            ).to_list(length=None)
            task_last_run_dates = [task["last_run_date"].replace(tzinfo=UTC) for task in tasks]

        count += 1


async def test_retry_config_defaults_task_shape(
    client: TestClient,
    test_database: MongoDatabase,
):
    """
    Verify total_retries and retry_interval are populated from a config that stores
    those values under defaults.task (the canonical sample_placeholder shape), not
    just at the top level of content.
    """
    ctx = await get_test_context(client)
    now = datetime.now(UTC)
    start = now - timedelta(minutes=1)

    # Config with retry nested under defaults.task
    defaults_config_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "config",
                "name": "config_defaults_task_retry",
                "parent_laui": ctx.config_folder_laui,
                "account_laui": ctx.account_laui,
                "project_laui": ctx.project_laui,
                "config_type": "task",
                "content": {
                    "defaults": {"task": {"total_retries": 3, "retry_interval": 2}},
                    "parameters": {},
                },
            },
        ),
    )
    assert defaults_config_resp.status_code == 200
    defaults_config_laui = CreateItemResponse(**defaults_config_resp.json()).item_laui

    # Task attached to the defaults.task-shape config
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": "task_defaults_task_retry",
                "project_laui": ctx.project_laui,
                "account_laui": ctx.account_laui,
                "parent_laui": ctx.workflow_laui,
                "operator_laui": ctx.operator_laui,
                "connection_laui": ctx.connection_laui,
                "payload_laui": ctx.fail_payload_laui,
                "start_date": start.isoformat(),
                "end_date": (now + timedelta(days=365)).isoformat(),
                "state": "scheduled",
                "frequency": "0 0 * * *",
                "attached_config_lauis": [defaults_config_laui],
            },
        ),
    )
    assert task_resp.status_code == 200
    task_laui = CreateItemResponse(**task_resp.json()).item_laui
    task_doc = await test_database.items.find_one({"_id": ObjectId(task_laui)})
    assert task_doc["total_retries"] == 3
    assert task_doc["retry_interval"] == 2

    # Task-level fields should override config when both are present
    task_resp2 = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": "task_override_defaults_task_retry",
                "project_laui": ctx.project_laui,
                "account_laui": ctx.account_laui,
                "parent_laui": ctx.workflow_laui,
                "operator_laui": ctx.operator_laui,
                "connection_laui": ctx.connection_laui,
                "payload_laui": ctx.fail_payload_laui,
                "start_date": start.isoformat(),
                "end_date": (now + timedelta(days=365)).isoformat(),
                "state": "scheduled",
                "frequency": "0 0 * * *",
                "total_retries": 7,
                "retry_interval": 10,
                "attached_config_lauis": [defaults_config_laui],
            },
        ),
    )
    assert task_resp2.status_code == 200
    task2_laui = CreateItemResponse(**task_resp2.json()).item_laui
    task2_doc = await test_database.items.find_one({"_id": ObjectId(task2_laui)})
    assert task2_doc["total_retries"] == 7
    assert task2_doc["retry_interval"] == 10


def load_code_block():
    path = Path(__file__)
    codeblock_path = path.parent / "celery/task-test-data/conditional_fail_operator.py"

    return codeblock_path.read_text(encoding="utf-8")


codeblock = load_code_block()

bashblock = """
pip install requests==2.31.*
python3 -c "import requests; print(f'requests version: {requests.__version__}')"
echo "Dependencies installed successfully"
"""
