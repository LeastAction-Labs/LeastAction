# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import asyncio
import time
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.core.catalog.api_request import CreateItemResponse, GetItemsFilter
from src.core.catalog.orchestrator import ItemOrchestrator
from src.core.db.types import MongoDatabase
from src.core.task.connection.schema import SortOrder
from tests.integration.schema import BaseFolders, TestRequest
from tests.integration.utils import create_base_folders, execute_request, get_item_orchestrator

# TODO : add test to check cancel for async task
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
                "codeblock": {"main.py": codeblock},
                "bashblock": {"main.sh": bashblock},
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
                "content": {},
                "max_parallelism": 10,
                "sort_dict": {"priority": SortOrder.ASC},
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
                "content": '{"seconds" : 40 }',
            },
        ),
    )
    assert payload_resp.status_code == 200
    return CreateItemResponse(**payload_resp.json()).item_laui


@pytest.fixture
async def action_laui(
    client: TestClient, workflow_laui: str, account_laui: str, project_laui: str
) -> str:
    """Create an action to cancel tasks"""
    action_code_block = load_action_code_block()

    action_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/action/run",
            method="post",
            json={
                "item_type": "action",
                "name": f"cancel_task_action_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "bashblock": {},
                "codeblock": {"main.py": action_code_block},
                "account_laui": account_laui,
                "project_laui": project_laui,
            },
        ),
    )
    assert action_resp.status_code == 200
    return CreateItemResponse(**action_resp.json()).item_laui


def load_code_block():
    path = Path(__file__)
    codeblock_path = path.parent / "celery/task-test-data/sleep_operator.py"

    return codeblock_path.read_text(encoding="utf-8")


def load_action_code_block():
    path = Path(__file__)
    codeblock_path = path.parent / "celery/task-test-data/task_control_action.py"

    return codeblock_path.read_text(encoding="utf-8")


codeblock = load_code_block()
bashblock = {}


@pytest.fixture
async def item_orchestrator(test_database: MongoDatabase):
    async for orchestrator in get_item_orchestrator(test_database):
        yield orchestrator


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
                "frequency": "ADHOC",
                "priority": TASK_PRIORITY,
            },
        ),
    )
    assert task_resp.status_code == 200, (
        f"Task creation failed with status {task_resp.status_code}: {task_resp.text}"
    )
    TASK_PRIORITY += 1
    return CreateItemResponse(**task_resp.json()).item_laui


async def test_execute_and_cancel_multiple_tasks(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
    payload_laui: str,
    action_laui: str,
    item_orchestrator: ItemOrchestrator,
):
    """
    Test creating 5tasks, executing them, canceling them via action, and verifying cancellation.

    Steps:
    1. Create 5tasks with sleep operator
    2. Execute all 5tasks via multiple_tasks API
    3. Immediately call run action 5times to cancel each task
    1. Poll for 30 seconds max to verify all tasks are cancelled
    5. Assert state="cancelled", user_set_state="cancel", and last_run_output["message"]="Task cancelled by user"
    """

    # Step 1: Create 5tasks and assert each creation is successful
    task_lauis = []
    task_names = []
    for i in range(5):
        task_name = f"task_to_cancel_{i}_{datetime.now().timestamp()}"
        task_laui = _create_task(
            client,
            operator_laui,
            connection_laui,
            workflow_laui,
            project_laui,
            account_laui,
            payload_laui,
        )
        assert task_laui is not None, f"Task {i} creation returned None"
        task_lauis.append(task_laui)
        task_names.append(task_name)
        await asyncio.sleep(0.1)

    # Assert all 5tasks were created successfully
    assert len(task_lauis) == 5, f"Expected 5tasks, but only {len(task_lauis)} were created"
    print(f"\n✓ Successfully created {len(task_lauis)} tasks")

    # Step 2: Execute all 5tasks via multiple_tasks API
    print("\n>>> Executing all 5tasks via multiple_tasks API...")
    execute_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/multiple_tasks", method="post", json={"task_lauis": task_lauis}
        ),
    )
    assert execute_resp.status_code == 200, f"Execute multiple tasks failed: {execute_resp.text}"
    print("✓ Tasks execution initiated successfully")
    await asyncio.sleep(0.5)  # Give tasks a moment to start

    # Step 3: Call run action 5times to cancel each task
    print("\n>>> Cancelling all 5tasks via action API...")
    for i, task_laui in enumerate(task_lauis):
        # Get task details first to get the name
        task = await item_orchestrator.get_items(request=GetItemsFilter(item_laui=task_laui))

        print(f"  Cancelling task {i}: {task['name']}")
        action_resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/action/run",
                method="post",
                json={
                    "item_type": "action",
                    "item_laui": action_laui,
                    "action_variables": {
                        "item_type": "task",
                        "task_laui": task_laui,
                        "name": task["name"],
                        "project_laui": project_laui,
                        "account_laui": account_laui,
                        "parent_laui": workflow_laui,
                        "operator_laui": operator_laui,
                        "connection_laui": connection_laui,
                        "user_set_state": "cancel",
                    },
                },
            ),
        )
        assert action_resp.status_code == 200, (
            f"Action run failed for task {task_laui}: {action_resp.text}"
        )
    print("✓ All cancellation actions sent successfully")

    # Step 1: Poll for 30 seconds max to verify all tasks are cancelled
    max_wait = 30
    poll_interval = 1
    start_time = time.time()

    all_cancelled = False
    poll_count = 0
    while time.time() - start_time < max_wait:
        all_cancelled = True
        poll_count += 1
        print(f"\nPolling iteration {poll_count} (elapsed: {time.time() - start_time:.1f}s)")

        for i, task_laui in enumerate(task_lauis):
            # Get task via API
            get_resp = execute_request(
                client=client,
                request=TestRequest(
                    url="/api/v1/catalog/get", method="get", params={"item_laui": task_laui}
                ),
            )
            assert get_resp.status_code == 200, f"Get task failed: {get_resp.text}"
            task_data = get_resp.json()

            # Print current status
            task_name = task_data.get("name", "Unknown")
            task_state = task_data.get("state", "Unknown")
            task_user_set_state = task_data.get("user_set_state", "Unknown")
            print(
                f"  Task {i} ({task_name}): state={task_state}, user_set_state={task_user_set_state}"
            )

            # Check if task has reached cancelled state
            if task_data.get("state") != "cancelled":
                all_cancelled = False

        if all_cancelled:
            print(f"\nAll tasks cancelled after {time.time() - start_time:.1f}s")
            break

        await asyncio.sleep(poll_interval)

    # Step 5: Assert state="cancelled", user_set_state="cancel", and last_run_output["message"]="Task cancelled by user"
    print("\n>>> Final verification of all task states...")
    for i, task_laui in enumerate(task_lauis):
        get_resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/catalog/get", method="get", params={"item_laui": task_laui}
            ),
        )
        assert get_resp.status_code == 200, f"Get task failed: {get_resp.text}"
        task_data = get_resp.json()

        # Print task details for visibility
        task_name = task_data.get("name", "Unknown")
        task_state = task_data.get("state", "Unknown")
        task_user_set_state = task_data.get("user_set_state", "Unknown")
        print(
            f"Task {i}: name={task_name}, state={task_state}, user_set_state={task_user_set_state}"
        )

        # Assert state is "cancelled"
        assert task_data.get("state") == "cancelled", (
            f"Task {task_laui} state is {task_data.get('state')}, expected 'cancelled'"
        )

        # Assert user_set_state is "cancel"
        assert task_data.get("user_set_state") == "cancel", (
            f"Task {task_laui} user_set_state is {task_data.get('user_set_state')}, expected 'cancel'"
        )

        # Assert last_run_output message
        last_run_output = task_data.get("last_run_output", {})
        assert last_run_output.get("message") == "Task cancelled by user", (
            f"Task {task_laui} last_run_output message is {last_run_output.get('message')}, expected 'Task cancelled by user'"
        )

    print("\n✓ All 5tasks successfully cancelled and verified!")
    print("  - state: cancelled")
    print("  - user_set_state: cancel")
    print('  - last_run_output["message"]: Task cancelled by user')
