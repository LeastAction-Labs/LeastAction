# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import asyncio
from datetime import datetime
from pathlib import Path

import pytest
from bson import ObjectId
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
    await test_database.items.drop()
    await test_database.links.delete_many({})
    yield  # Test runs here
    await test_database.items.drop()
    await test_database.links.drop()


async def setup(client: TestClient, test_database: MongoDatabase) -> list[str]:
    tasks = await test_database.items.find({"item_type": "task"}, {"_id": 1}).to_list(length=None)
    if len(tasks) == 1000:
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
        for i in range(1, 1001):
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
                        "state": TaskState.CREATED,
                        "frequency": "ADHOC",
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
    task_lauis = await setup(client, test_database)
    project_laui = (await test_database.items.find_one({"item_type": "folder.project"}))["_id"]
    request = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/cron/manage",
            method="post",
            json={"project_laui": str(project_laui), "action": "STOP"},
        ),
    )
    execute_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/multiple_tasks", method="post", json={"task_lauis": task_lauis}
        ),
    )
    assert execute_resp.status_code == 200

    connection = await test_database.items.find_one({"item_type": "connection.python"})
    connection_metrics = ConnectionMetrics(**connection)
    assert connection_metrics.in_queue == 980
    assert connection_metrics.current_parallelism <= 20

    while connection_metrics.current_parallelism != 0:
        await asyncio.sleep(1)
        connection = await test_database.items.find_one({"item_type": "connection.python"})
        connection_metrics = ConnectionMetrics(**connection)
        assert (
            connection_metrics.in_queue == 980
        )  # nothing picked from queue unless another run multiple tasks is sent
        assert connection_metrics.current_parallelism <= 20
        assert connection_metrics.current_parallelism >= 0
        assert connection_metrics.in_queue >= 0

    # we wont be adding any new tasks now just checking tasks which are in queued_for_connection state whether they get executed as expected or not
    # from this point onwards in_queue can only decrease
    request = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/cron/manage",
            method="post",
            json={"project_laui": str(project_laui), "action": "START"},
        ),
    )
    assert request.status_code == 200

    connection_metrics, cq_count = await get_connection_metrics_and_cq_count(test_database)

    total_queue_drain_events = 0  # Events where in_queue decreased
    total_task_completion_events = 0  # Events where tasks completed (cq_count decreased)
    successful_queue_drain_validations = 0
    successful_task_completion_validations = 0

    # Track failures with details
    queue_drain_failures = []
    task_completion_failures = []

    while connection_metrics.in_queue > 0:
        prev_connection_metrics = connection_metrics
        prev_cq_count = cq_count

        connection_metrics, cq_count = await get_connection_metrics_and_cq_count(test_database)
        assert connection_metrics.current_parallelism >= 0
        assert connection_metrics.in_queue >= 0

        cq_count_decrement = prev_cq_count - cq_count

        if prev_connection_metrics.in_queue != connection_metrics.in_queue:
            total_queue_drain_events += 1
            available_parallelism = (
                prev_connection_metrics.max_parallelism
                - prev_connection_metrics.current_parallelism
                + cq_count_decrement
            )
            if prev_connection_metrics.in_queue < available_parallelism:
                available_parallelism = prev_connection_metrics.in_queue

            expected_in_queue = prev_connection_metrics.in_queue - available_parallelism
            actual_in_queue = connection_metrics.in_queue
            in_queue_diff = actual_in_queue - expected_in_queue

            expected_current_parallelism = (
                prev_connection_metrics.current_parallelism
                - cq_count_decrement
                + available_parallelism
            )
            actual_current_parallelism = connection_metrics.current_parallelism
            parallelism_diff = actual_current_parallelism - expected_current_parallelism

            try:
                assert connection_metrics.in_queue == expected_in_queue
                assert connection_metrics.current_parallelism == expected_current_parallelism
                successful_queue_drain_validations += 1
            except AssertionError:
                queue_drain_failures.append(
                    {
                        "event_number": total_queue_drain_events,
                        "expected_in_queue": expected_in_queue,
                        "actual_in_queue": actual_in_queue,
                        "in_queue_diff": in_queue_diff,
                        "expected_current_parallelism": expected_current_parallelism,
                        "actual_current_parallelism": actual_current_parallelism,
                        "parallelism_diff": parallelism_diff,
                        "available_parallelism": available_parallelism,
                        "cq_count_decrement": cq_count_decrement,
                    }
                )
            continue

        if cq_count_decrement:
            total_task_completion_events += 1
            expected_current_parallelism = (
                prev_connection_metrics.current_parallelism - cq_count_decrement
            )
            actual_current_parallelism = connection_metrics.current_parallelism
            parallelism_diff = actual_current_parallelism - expected_current_parallelism

            try:
                assert connection_metrics.current_parallelism == expected_current_parallelism
                successful_task_completion_validations += 1
            except AssertionError:
                task_completion_failures.append(
                    {
                        "event_number": total_task_completion_events,
                        "expected_current_parallelism": expected_current_parallelism,
                        "actual_current_parallelism": actual_current_parallelism,
                        "parallelism_diff": parallelism_diff,
                        "cq_count_decrement": cq_count_decrement,
                    }
                )
            continue

    # Performance Analysis Report
    print("\n" + "=" * 80)
    print("PERFORMANCE ANALYSIS REPORT")
    print("=" * 80)

    # Queue Drain Events Analysis
    print("\nQUEUE DRAIN EVENTS (in_queue decreased)")
    print("-" * 80)
    if total_queue_drain_events > 0:
        success_rate = (successful_queue_drain_validations / total_queue_drain_events) * 100
        print(f"Total Events: {total_queue_drain_events}")
        print(f"Successful Validations: {successful_queue_drain_validations}")
        print(f"Failed Validations: {len(queue_drain_failures)}")
        print(f"Success Rate: {success_rate:.2f}%")

        if queue_drain_failures:
            print("\nFailed Events Breakdown:")
            for failure in queue_drain_failures:
                print(f"\n  Event #{failure['event_number']}:")
                print(
                    f"    in_queue: expected={failure['expected_in_queue']}, actual={failure['actual_in_queue']}, diff={failure['in_queue_diff']:+d}"
                )
                print(
                    f"    current_parallelism: expected={failure['expected_current_parallelism']}, actual={failure['actual_current_parallelism']}, diff={failure['parallelism_diff']:+d}"
                )
                print(
                    f"    available_parallelism: {failure['available_parallelism']}, cq_count_decrement: {failure['cq_count_decrement']}"
                )

            # Aggregate statistics
            avg_in_queue_diff = sum(abs(f["in_queue_diff"]) for f in queue_drain_failures) / len(
                queue_drain_failures
            )
            avg_parallelism_diff = sum(
                abs(f["parallelism_diff"]) for f in queue_drain_failures
            ) / len(queue_drain_failures)
            max_in_queue_diff = max(abs(f["in_queue_diff"]) for f in queue_drain_failures)
            max_parallelism_diff = max(abs(f["parallelism_diff"]) for f in queue_drain_failures)

            print("\n  Aggregate Deviation Metrics:")
            print(f"    Average in_queue deviation: {avg_in_queue_diff:.2f}")
            print(f"    Maximum in_queue deviation: {max_in_queue_diff}")
            print(f"    Average parallelism deviation: {avg_parallelism_diff:.2f}")
            print(f"    Maximum parallelism deviation: {max_parallelism_diff}")
    else:
        print("No queue drain events occurred")

    # Task Completion Events Analysis
    print("\n TASK COMPLETION EVENTS (cq_count decreased)")
    print("-" * 80)
    if total_task_completion_events > 0:
        success_rate = (successful_task_completion_validations / total_task_completion_events) * 100
        print(f"Total Events: {total_task_completion_events}")
        print(f"Successful Validations: {successful_task_completion_validations}")
        print(f"Failed Validations: {len(task_completion_failures)}")
        print(f"Success Rate: {success_rate:.2f}%")

        if task_completion_failures:
            print("\n Failed Events Breakdown:")
            for failure in task_completion_failures:
                print(f"\n  Event #{failure['event_number']}:")
                print(
                    f"    current_parallelism: expected={failure['expected_current_parallelism']}, actual={failure['actual_current_parallelism']}, diff={failure['parallelism_diff']:+d}"
                )
                print(f"    cq_count_decrement: {failure['cq_count_decrement']}")

            # Aggregate statistics
            avg_parallelism_diff = sum(
                abs(f["parallelism_diff"]) for f in task_completion_failures
            ) / len(task_completion_failures)
            max_parallelism_diff = max(abs(f["parallelism_diff"]) for f in task_completion_failures)

            print("\n  Aggregate Deviation Metrics:")
            print(f"    Average parallelism deviation: {avg_parallelism_diff:.2f}")
            print(f"    Maximum parallelism deviation: {max_parallelism_diff}")
    else:
        print("No task completion events occurred")

    # Overall Summary
    print("\nOVERALL SUMMARY")
    print("-" * 80)
    total_events = total_queue_drain_events + total_task_completion_events
    total_successes = successful_queue_drain_validations + successful_task_completion_validations
    overall_success_rate = (total_successes / total_events * 100) if total_events > 0 else 0
    print(f"Total Events Monitored: {total_events}")
    print(f"Total Successful Validations: {total_successes}")
    print(f"Total Failed Validations: {len(queue_drain_failures) + len(task_completion_failures)}")
    print(f"Overall Success Rate: {overall_success_rate:.2f}%")
    print("=" * 80 + "\n")

    while connection_metrics.current_parallelism != 0:
        await asyncio.sleep(1)
        connection = await test_database.items.find_one({"item_type": "connection.python"})
        connection_metrics = ConnectionMetrics(**connection)
        assert connection_metrics.in_queue == 0
        assert connection_metrics.current_parallelism <= 20
        assert connection_metrics.current_parallelism >= 0

    connection = await test_database.items.find_one({"item_type": "connection.python"})
    connection_metrics = ConnectionMetrics(**connection)
    assert connection_metrics.current_parallelism == 0
    assert connection_metrics.in_queue == 0

    # there should be no connection queues
    connection_queues = await test_database.items.find({"item_type": "connection_queue"}).to_list(
        length=None
    )
    assert len(connection_queues) == 0

    for task_laui in task_lauis:
        task = await test_database.items.find_one({"_id": ObjectId(task_laui)})
        assert task["state"] in ["success", "error"]


def load_code_block():
    path = Path(__file__)
    codeblock_path = path.parent / "celery/task-test-data/operator.py"

    return codeblock_path.read_text(encoding="utf-8")


codeblock = load_code_block()

connection = {"type": "docker"}
