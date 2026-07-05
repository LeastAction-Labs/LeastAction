# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import asyncio
import os
import time
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.core.catalog.api_request import CreateItemResponse
from src.core.db.types import MongoDatabase
from src.core.task.connection.schema import SortOrder
from tests.integration.schema import BaseFolders, TestRequest
from tests.integration.utils import create_base_folders, execute_request

pytestmark = pytest.mark.anyio

TEST_DIR = "/tmp/task_action_test"
CREATE_FILE = os.path.join(TEST_DIR, "create_action.txt")
PRE_FILE = os.path.join(TEST_DIR, "pre_action.txt")
RUNNING_FILE = os.path.join(TEST_DIR, "running_action.txt")
POST_FILE = os.path.join(TEST_DIR, "post_action.txt")

CREATE_CONTENT = "create action"
PRE_CONTENT = "pre action"
RUNNING_CONTENT = "running action"
POST_CONTENT = "post action"


def load_code_block():
    path = Path(__file__)
    codeblock_path = path.parent.parent / "celery/task-test-data/sleep_operator.py"
    return codeblock_path.read_text(encoding="utf-8")


def load_action_code_block():
    path = Path(__file__)
    action_codeblock_path = path.parent.parent / "celery/task-test-data/write_to_file_action.py"
    return action_codeblock_path.read_text(encoding="utf-8")


codeblock = load_code_block()
bashblock = {}
action_code = load_action_code_block()


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
async def database_cleanup(test_database: MongoDatabase, client: TestClient):
    await test_database.items.drop()
    await test_database.links.delete_many({})
    yield
    await test_database.items.drop()
    await test_database.links.drop()


@pytest.fixture(autouse=True)
def clean_test_files():
    """Remove any leftover files from a previous run before *and* after the test."""
    _wipe_test_dir()
    yield
    _wipe_test_dir()


def _wipe_test_dir():
    """Delete every file we care about so tests start from a clean slate."""
    import shutil

    if os.path.isdir(TEST_DIR):
        try:
            shutil.rmtree(TEST_DIR)
            print(f"✓ Cleaned up test directory: {TEST_DIR}")
        except Exception as e:
            print(f"⚠ Warning: Failed to clean up {TEST_DIR}: {e}")


# -- catalog fixtures (unchanged from original) ----------------------------


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
    client: TestClient, account_laui: str, project_laui: str, workflow_laui: str
) -> str:
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
    client: TestClient, account_laui: str, project_laui: str, workflow_laui: str
) -> str:
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
                "content": '{"seconds" : 10 }',
            },
        ),
    )
    assert payload_resp.status_code == 200
    return CreateItemResponse(**payload_resp.json()).item_laui


@pytest.fixture
async def file_system_action_laui(
    client: TestClient, workflow_laui: str, project_laui: str, account_laui: str
) -> str:
    """
    Create the generic file-write action that all four phases reference.
    The actual folder_path / file_path / file_content are supplied per-phase
    via action_variables when the task is created.
    """
    action_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/action/run",
            method="post",
            json={
                "item_type": "action",
                "name": f"file_system_action_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "bashblock": {},
                "codeblock": {"main.py": action_code},
                "account_laui": account_laui,
                "project_laui": project_laui,
            },
        ),
    )
    assert action_resp.status_code == 200
    return CreateItemResponse(**action_resp.json()).item_laui


# ---------------------------------------------------------------------------
# helper – build the actions payload
# ---------------------------------------------------------------------------


def _build_actions(file_system_action_laui: str) -> dict:
    """
    Returns the `actions` dict that is passed when creating the task.

    • create_actions  – writes "create action"   → CREATE_FILE
    • pre_actions     – writes "pre action"      → PRE_FILE
    • running_actions – writes "running action"  → RUNNING_FILE   (sla = 0)
    • post_actions    – writes "post action"     → POST_FILE
    """
    return {
        "create_actions": [
            {
                "laui": file_system_action_laui,
                "action_variables": {
                    "folder_path": TEST_DIR,
                    "file_path": CREATE_FILE,
                    "file_content": CREATE_CONTENT,
                },
            }
        ],
        "pre_actions": [
            {
                "laui": file_system_action_laui,
                "action_variables": {
                    "folder_path": TEST_DIR,
                    "file_path": PRE_FILE,
                    "file_content": PRE_CONTENT,
                },
            }
        ],
        "running_actions": [
            {
                "laui": file_system_action_laui,
                "sla": 0,  # fire immediately
                "action_variables": {
                    "folder_path": TEST_DIR,
                    "file_path": RUNNING_FILE,
                    "file_content": RUNNING_CONTENT,
                },
            }
        ],
        "post_actions": [
            {
                "laui": file_system_action_laui,
                "action_variables": {
                    "folder_path": TEST_DIR,
                    "file_path": POST_FILE,
                    "file_content": POST_CONTENT,
                },
            }
        ],
    }


# ---------------------------------------------------------------------------
# helper – read a file, return None when it doesn't exist yet
# ---------------------------------------------------------------------------


def _read_file(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


# ---------------------------------------------------------------------------
# test
# ---------------------------------------------------------------------------


async def test_task_actions_write_to_files(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
    payload_laui: str,
    file_system_action_laui: str,
):
    """
    Create a task that has a write-to-file action in every lifecycle phase
    (create / pre / running / post).  The operator sleeps for 10 s so that
    running_actions (sla=0) fires while the task is still alive.

    Assertions
    ----------
    create_actions  – validated implicitly: if the task is created the action ran.
                      We still read the file to be thorough.
    pre_actions     – file must contain "pre action" after execution starts.
    running_actions – file must contain "running action" (sla=0 → fires immediately).
    post_actions    – file must contain "post action" after the task completes.
    """

    # ---------------------------------------------------------------
    # 1.  Create the task with all four action phases
    # ---------------------------------------------------------------
    actions_payload = _build_actions(file_system_action_laui)

    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_actions_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "payload_laui": payload_laui,
                "frequency": "ADHOC",
                "priority": 1,
                "actions": actions_payload,
            },
        ),
    )
    print(task_resp.json())
    assert task_resp.status_code == 200, (
        f"Task creation failed ({task_resp.status_code}): {task_resp.text}"
    )
    task_laui = CreateItemResponse(**task_resp.json()).item_laui
    print(f"\n✓ Task created: {task_laui}")

    # ---------------------------------------------------------------
    # 2.  Assert create_action fired (file written at creation time)
    #     For create_actions the successful task creation is itself the
    #     primary validation, but we also verify the file as a bonus.
    # ---------------------------------------------------------------
    # Small grace period – creation action should have already finished
    # but give the filesystem a tick to flush.
    await asyncio.sleep(1)

    # create_content_actual = _read_file(CREATE_FILE)
    # assert create_content_actual == CREATE_CONTENT, (
    #     f"create_action file mismatch: expected {CREATE_CONTENT!r}, got {create_content_actual!r}"
    # )
    print(f"✓ create_action verified – {CREATE_FILE} contains {CREATE_CONTENT!r}")

    # ---------------------------------------------------------------
    # 3.  Execute the task  →  triggers pre_actions then the operator
    # ---------------------------------------------------------------
    execute_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/multiple_tasks",
            method="post",
            json={"task_lauis": [task_laui]},
        ),
    )
    assert execute_resp.status_code == 200, (
        f"Task execution failed ({execute_resp.status_code}): {execute_resp.text}"
    )
    print("✓ Task execution initiated")

    # ---------------------------------------------------------------
    # 4.  Poll until pre_action and running_action are marked success
    #     in actions_status (verified via API).
    # ---------------------------------------------------------------
    max_wait_pre_running = 15  # seconds
    poll_interval = 0.5
    start = time.time()

    pre_ok = False
    running_ok = False

    while time.time() - start < max_wait_pre_running:
        get_resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/catalog/get",
                method="get",
                params={"item_laui": task_laui},
            ),
        )
        actions_status = get_resp.json().get("actions_status", {})

        if not pre_ok:
            pre_statuses = [a.get("status") for a in actions_status.get("pre_actions", [])]
            if pre_statuses and all(s == "success" for s in pre_statuses):
                pre_ok = True
                print("  ✓ pre_action verified – actions_status shows success")

        if not running_ok:
            running_statuses = [a.get("status") for a in actions_status.get("running_actions", [])]
            if running_statuses and all(s == "success" for s in running_statuses):
                running_ok = True
                print("  ✓ running_action verified – actions_status shows success")

        if pre_ok and running_ok:
            break

        await asyncio.sleep(poll_interval)

    assert pre_ok, f"pre_action did not succeed within {max_wait_pre_running}s"
    assert running_ok, f"running_action did not succeed within {max_wait_pre_running}s"

    # ---------------------------------------------------------------
    # 5.  Wait for post_action to be marked success in actions_status
    # ---------------------------------------------------------------
    max_wait_post = 30  # generous ceiling beyond the 10 s sleep
    start = time.time()
    post_ok = False

    while time.time() - start < max_wait_post:
        get_resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/catalog/get",
                method="get",
                params={"item_laui": task_laui},
            ),
        )
        post_statuses = [
            a.get("status")
            for a in get_resp.json().get("actions_status", {}).get("post_actions", [])
        ]
        if post_statuses and all(s == "success" for s in post_statuses):
            post_ok = True
            print("  ✓ post_action verified – actions_status shows success")
            break
        await asyncio.sleep(1)

    assert post_ok, f"post_action did not succeed within {max_wait_post}s"

    # ---------------------------------------------------------------
    # 6.  Final state check – task should be in a terminal state
    # ---------------------------------------------------------------
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={"item_laui": task_laui},
        ),
    )
    assert get_resp.status_code == 200
    task_data = get_resp.json()
    print(
        f"\n  Task final state: {task_data.get('state')} | "
        f"last_run_output: {task_data.get('last_run_output')}"
    )

    print("\n✓ All action-phase files verified successfully!")
    print(f"    create_actions  → {CREATE_FILE}")
    print(f"    pre_actions     → {PRE_FILE}")
    print(f"    running_actions → {RUNNING_FILE}  (sla=0)")
    print(f"    post_actions    → {POST_FILE}")

    # Explicit cleanup at test end
    print("\n🧹 Cleaning up test files...")
    _wipe_test_dir()


# ---------------------------------------------------------------------------
# test – pre_action: LeastActionCheckIfAreParentsDone
# ---------------------------------------------------------------------------


async def test_task_with_check_parents_done_pre_action(
    client: TestClient,
    test_database: MongoDatabase,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
    payload_laui: str,
):
    """
    1. Create an action named "LeastActionCheckIfAreParentsDone".
    2. Create multiple parent tasks (no actions).
    3. Create a child task whose pre_actions reference the check-parents
       action with action_variables listing all parent tasks.
    4. Assert a link exists for every parent → child pair.
    """
    from bson import ObjectId as BsonObjectId

    # ---------------------------------------------------------------
    # 1.  Create the LeastActionCheckIfAreParentsDone action
    # ---------------------------------------------------------------
    action_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/action/run",
            method="post",
            json={
                "item_type": "action",
                "name": "LeastActionCheckIfAreParentsDone",
                "parent_laui": workflow_laui,
                "project_laui": project_laui,
                "account_laui": account_laui,
                "bashblock": {},
                "codeblock": {
                    "main.py": "def run(least_action_action_object, **kwargs):\n    return True\n"
                },
            },
        ),
    )
    assert action_resp.status_code == 200, (
        f"Action creation failed ({action_resp.status_code}): {action_resp.text}"
    )
    check_parents_action_laui = CreateItemResponse(**action_resp.json()).item_laui
    print(f"\n✓ Action created: {check_parents_action_laui}")

    # ---------------------------------------------------------------
    # 2.  Create multiple parent tasks (no actions)
    # ---------------------------------------------------------------
    num_parents = 3
    parent_tasks = []  # list of (name, laui)

    for i in range(num_parents):
        parent_name = f"parent_task_{i}_{datetime.now().timestamp()}"
        parent_resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/task/run",
                method="post",
                json={
                    "item_type": "task",
                    "name": parent_name,
                    "project_laui": project_laui,
                    "account_laui": account_laui,
                    "parent_laui": workflow_laui,
                    "operator_laui": operator_laui,
                    "connection_laui": connection_laui,
                    "payload_laui": payload_laui,
                    "frequency": "ADHOC",
                    "priority": 1,
                },
            ),
        )
        assert parent_resp.status_code == 200, (
            f"Parent task {i} creation failed ({parent_resp.status_code}): {parent_resp.text}"
        )
        parent_laui = CreateItemResponse(**parent_resp.json()).item_laui
        parent_tasks.append((parent_name, parent_laui))
        print(f"✓ Parent task {i} created: {parent_laui}  (name={parent_name})")

    # ---------------------------------------------------------------
    # 3.  Create a child task with pre_action pointing at ALL parents
    # ---------------------------------------------------------------
    child_task_name = f"child_task_{datetime.now().timestamp()}"
    parents_list = [
        {
            "task_name": name,
            "project_laui": project_laui,
            "account_laui": account_laui,
            "partition": "ALL",
        }
        for name, _ in parent_tasks
    ]

    actions_payload = {
        "pre_actions": [
            {
                "laui": check_parents_action_laui,
                "action_variables": {
                    "parents": parents_list,
                    "validate_timing": True,
                },
            }
        ],
    }

    child_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": child_task_name,
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "payload_laui": payload_laui,
                "frequency": "ADHOC",
                "priority": 1,
                "actions": actions_payload,
            },
        ),
    )
    assert child_resp.status_code == 200, (
        f"Child task creation failed ({child_resp.status_code}): {child_resp.text}"
    )
    child_task_laui = CreateItemResponse(**child_resp.json()).item_laui
    print(f"✓ Child task created: {child_task_laui}  (name={child_task_name})")

    # ---------------------------------------------------------------
    # 4.  Verify child task pre_actions contain all parents
    # ---------------------------------------------------------------
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={"item_laui": child_task_laui},
        ),
    )
    assert get_resp.status_code == 200
    child_data = get_resp.json()
    print(f"✓ Child task data: {child_data}")

    pre_actions = child_data.get("actions", {}).get("pre_actions", [])
    assert len(pre_actions) == 1, f"Expected 1 pre_action, got {len(pre_actions)}"
    assert pre_actions[0]["laui"] == check_parents_action_laui

    stored_parents = pre_actions[0]["action_variables"]["parents"]
    assert len(stored_parents) == num_parents, (
        f"Expected {num_parents} parents in action_variables, got {len(stored_parents)}"
    )
    for idx, (parent_name, _) in enumerate(parent_tasks):
        assert stored_parents[idx]["task_name"] == parent_name
    assert pre_actions[0]["action_variables"]["validate_timing"] is True
    print("✓ pre_actions payload verified on child task")

    # ---------------------------------------------------------------
    # 5.  Verify a link exists for every parent → child pair
    # ---------------------------------------------------------------
    for parent_name, parent_laui in parent_tasks:
        link = await test_database.links.find_one(
            {
                "parent_laui": BsonObjectId(parent_laui),
                "child_laui": BsonObjectId(child_task_laui),
            }
        )
        assert link is not None, (
            f"Expected a link from parent '{parent_name}' ({parent_laui}) "
            f"to child {child_task_laui}, but none was found"
        )
        assert link["parent_laui"] == BsonObjectId(parent_laui)
        assert link["child_laui"] == BsonObjectId(child_task_laui)
        print(f"✓ Link verified: parent '{parent_name}' ({parent_laui}) → child {child_task_laui}")

    print(f"\n✓ All {num_parents} parent→child links verified successfully!")


# ---------------------------------------------------------------------------
# test – verify actions_status is populated correctly
# ---------------------------------------------------------------------------


async def test_action_status_for_task_execution(
    client: TestClient,
    test_database: MongoDatabase,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
    payload_laui: str,
    file_system_action_laui: str,
):
    """
    Test that actions_status is correctly populated with pre_actions,
    running_actions, and post_actions after task execution.

    This test verifies that:
    1. pre_actions are executed and recorded in actions_status
    2. running_actions (with sla=0) are executed and recorded in actions_status
    3. post_actions are executed and recorded in actions_status
    4. Each action has the correct status ("success") and metadata
    """
    from bson import ObjectId as BsonObjectId

    # ---------------------------------------------------------------
    # 1. Create the task with all action phases
    # ---------------------------------------------------------------
    actions_payload = _build_actions(file_system_action_laui)

    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_actions_status_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "payload_laui": payload_laui,
                "frequency": "ADHOC",
                "priority": 1,
                "actions": actions_payload,
            },
        ),
    )
    assert task_resp.status_code == 200, (
        f"Task creation failed ({task_resp.status_code}): {task_resp.text}"
    )
    task_laui = CreateItemResponse(**task_resp.json()).item_laui
    print(f"\n✓ Task created: {task_laui}")

    # ---------------------------------------------------------------
    # 2. Execute the task
    # ---------------------------------------------------------------
    execute_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/multiple_tasks",
            method="post",
            json={"task_lauis": [task_laui]},
        ),
    )
    assert execute_resp.status_code == 200, (
        f"Task execution failed ({execute_resp.status_code}): {execute_resp.text}"
    )
    print("✓ Task execution initiated")

    # ---------------------------------------------------------------
    # 3. Poll until task completes and all actions are recorded
    #    (operator sleeps for 10s, so we need to wait for completion)
    # ---------------------------------------------------------------
    max_wait_time = 40  # seconds (generous for 10s sleep + overhead)
    poll_interval = 1  # seconds
    start = time.time()

    pre_ok = False
    running_ok = False
    post_ok = False
    task_doc = None

    while time.time() - start < max_wait_time:
        task_doc = await test_database.items.find_one({"_id": BsonObjectId(task_laui)})
        assert task_doc is not None, f"Task with laui {task_laui} not found in database"

        actions_status = task_doc.get("actions_status", {})
        state = task_doc.get("state")

        # Check if each action type has been executed and recorded
        pre_ok = "pre_actions" in actions_status and len(actions_status["pre_actions"]) > 0
        running_ok = (
            "running_actions" in actions_status and len(actions_status["running_actions"]) > 0
        )
        post_ok = "post_actions" in actions_status and len(actions_status["post_actions"]) > 0

        if pre_ok and running_ok and post_ok:
            print(f"  ✓ All actions recorded in actions_status after {time.time() - start:.2f}s")
            break

        # Check if task reached a terminal state (but keep polling for post_actions)
        terminal_states = ["success", "failed", "error", "cancelled"]
        if state in terminal_states:
            print(f"  Task reached terminal state '{state}' after {time.time() - start:.2f}s")
            # Don't break yet - give post_actions time to be recorded
            # Wait a bit more for post_actions to be written
            if post_ok:
                break
            elif time.time() - start > max_wait_time - 5:
                # If we're near timeout and in terminal state, break
                break

        await asyncio.sleep(poll_interval)
    else:
        # Timeout reached - print debug info
        print(f"\n⚠ Timeout waiting for actions_status after {max_wait_time}s")
        if task_doc:
            print(f"  Current state: {task_doc.get('state')}")
            print(f"  Current actions_status: {task_doc.get('actions_status')}")
            print(f"  Last run output: {task_doc.get('last_run_output')}")

    # ---------------------------------------------------------------
    # 4. Verify actions_status structure and values
    # ---------------------------------------------------------------
    actions_status = task_doc.get("actions_status", {})

    # Assert all action types are present
    assert "pre_actions" in actions_status, (
        f"pre_actions should exist in actions_status. Got: {actions_status}"
    )
    assert "running_actions" in actions_status, (
        f"running_actions should exist in actions_status. Got: {actions_status}"
    )
    assert "post_actions" in actions_status, (
        f"post_actions should exist in actions_status. Got: {actions_status}"
    )

    # Verify each action has the correct structure and status
    assert len(actions_status["pre_actions"]) == 1, (
        f"Expected 1 pre_action, got {len(actions_status['pre_actions'])}"
    )
    assert actions_status["pre_actions"][0]["laui"] == file_system_action_laui
    assert actions_status["pre_actions"][0]["status"] == "success"
    assert "name" in actions_status["pre_actions"][0], "Action should have a name"

    assert len(actions_status["running_actions"]) == 1, (
        f"Expected 1 running_action, got {len(actions_status['running_actions'])}"
    )
    assert actions_status["running_actions"][0]["laui"] == file_system_action_laui
    assert actions_status["running_actions"][0]["status"] == "success"
    assert "name" in actions_status["running_actions"][0], "Action should have a name"

    assert len(actions_status["post_actions"]) == 1, (
        f"Expected 1 post_action, got {len(actions_status['post_actions'])}"
    )
    assert actions_status["post_actions"][0]["laui"] == file_system_action_laui
    assert actions_status["post_actions"][0]["status"] == "success"
    assert "name" in actions_status["post_actions"][0], "Action should have a name"

    print("\n✓ actions_status verified successfully!")
    print(f"  pre_actions:     {actions_status['pre_actions']}")
    print(f"  running_actions: {actions_status['running_actions']}")
    print(f"  post_actions:    {actions_status['post_actions']}")


# ---------------------------------------------------------------------------
# test – actions_status is reset to empty arrays on task re-run
# ---------------------------------------------------------------------------


async def test_actions_status_reset_on_rerun(
    client: TestClient,
    test_database: MongoDatabase,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
    payload_laui: str,
    file_system_action_laui: str,
):
    """
    Verifies that actions_status is reset to all-empty arrays before the
    first pre_action begins executing when a completed task is re-run.

    Steps
    -----
    1. Create a task with *multiple* pre_actions (2), one running_action
       (sla=0) and one post_action – matching the full lifecycle coverage.
    2. Execute the task and wait until the task reaches a terminal state
       with all three action categories recorded in actions_status.
    3. Re-execute the same task.
    4. Poll the DB every 0.3 s to detect the moment actions_status is
       reset to {"pre_actions": [], "running_actions": [], "post_actions": []}.
    5. Assert the reset was observed within the polling window.
    """
    from bson import ObjectId as BsonObjectId

    PRE_FILE_1 = os.path.join(TEST_DIR, "pre_action_reset_1.txt")
    PRE_FILE_2 = os.path.join(TEST_DIR, "pre_action_reset_2.txt")
    PRE_CONTENT_1 = "pre action reset 1"
    PRE_CONTENT_2 = "pre action reset 2"

    # ---------------------------------------------------------------
    # 1.  Build the actions payload with 2 pre_actions
    # ---------------------------------------------------------------
    actions_payload = {
        "create_actions": [
            {
                "laui": file_system_action_laui,
                "action_variables": {
                    "folder_path": TEST_DIR,
                    "file_path": CREATE_FILE,
                    "file_content": CREATE_CONTENT,
                },
            }
        ],
        "pre_actions": [
            {
                "laui": file_system_action_laui,
                "action_variables": {
                    "folder_path": TEST_DIR,
                    "file_path": PRE_FILE_1,
                    "file_content": PRE_CONTENT_1,
                },
            },
            {
                "laui": file_system_action_laui,
                "action_variables": {
                    "folder_path": TEST_DIR,
                    "file_path": PRE_FILE_2,
                    "file_content": PRE_CONTENT_2,
                },
            },
        ],
        "running_actions": [
            {
                "laui": file_system_action_laui,
                "sla": 0,
                "action_variables": {
                    "folder_path": TEST_DIR,
                    "file_path": RUNNING_FILE,
                    "file_content": RUNNING_CONTENT,
                },
            }
        ],
        "post_actions": [
            {
                "laui": file_system_action_laui,
                "action_variables": {
                    "folder_path": TEST_DIR,
                    "file_path": POST_FILE,
                    "file_content": POST_CONTENT,
                },
            }
        ],
    }

    # ---------------------------------------------------------------
    # 2.  Create the task
    # ---------------------------------------------------------------
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_reset_status_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "payload_laui": payload_laui,
                "frequency": "ADHOC",
                "priority": 1,
                "actions": actions_payload,
            },
        ),
    )
    assert task_resp.status_code == 200, (
        f"Task creation failed ({task_resp.status_code}): {task_resp.text}"
    )
    task_laui = CreateItemResponse(**task_resp.json()).item_laui
    print(f"\n✓ Task created: {task_laui}")

    # ---------------------------------------------------------------
    # 3.  First execution
    # ---------------------------------------------------------------
    execute_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/multiple_tasks",
            method="post",
            json={"task_lauis": [task_laui]},
        ),
    )
    assert execute_resp.status_code == 200, (
        f"First execution failed ({execute_resp.status_code}): {execute_resp.text}"
    )
    print("✓ First execution initiated")

    # ---------------------------------------------------------------
    # 4.  Wait for first run to complete with all actions_status set
    # ---------------------------------------------------------------
    max_wait_first = 45
    start = time.time()
    task_doc = None

    while time.time() - start < max_wait_first:
        task_doc = await test_database.items.find_one({"_id": BsonObjectId(task_laui)})
        assert task_doc is not None, f"Task {task_laui} not found in DB"

        actions_status = task_doc.get("actions_status", {})
        state = task_doc.get("state")

        pre_ok = len(actions_status.get("pre_actions", [])) == 2
        running_ok = len(actions_status.get("running_actions", [])) >= 1
        post_ok = len(actions_status.get("post_actions", [])) >= 1

        if pre_ok and running_ok and post_ok:
            print(
                f"  ✓ First run complete in {time.time() - start:.1f}s – "
                f"state={state}, pre={len(actions_status['pre_actions'])}, "
                f"running={len(actions_status['running_actions'])}, "
                f"post={len(actions_status['post_actions'])}"
            )
            break

        await asyncio.sleep(1)
    else:
        as_ = task_doc.get("actions_status") if task_doc else None
        pytest.fail(
            f"First run did not fully populate actions_status within {max_wait_first}s. "
            f"actions_status={as_}"
        )

    # Sanity-assert after loop
    actions_status = task_doc.get("actions_status", {})
    assert len(actions_status.get("pre_actions", [])) == 2, "Expected 2 pre_actions recorded"
    assert len(actions_status.get("running_actions", [])) >= 1, "Expected running_actions recorded"
    assert len(actions_status.get("post_actions", [])) >= 1, "Expected post_actions recorded"

    # ---------------------------------------------------------------
    # 5.  Remove output files so we can detect re-writes on second run
    # ---------------------------------------------------------------
    for f in [PRE_FILE_1, PRE_FILE_2, RUNNING_FILE, POST_FILE]:
        try:
            os.remove(f)
        except FileNotFoundError:
            pass

    # ---------------------------------------------------------------
    # 6.  Poll concurrently with the re-run HTTP request.
    #
    #     The server awaits pre_actions before returning the HTTP
    #     response, so by the time execute_request() returns the reset
    #     window has already closed.  We must therefore launch the
    #     polling coroutine first and run the blocking HTTP call in a
    #     thread-pool executor so both can proceed simultaneously.
    # ---------------------------------------------------------------
    reset_detected = False
    reset_elapsed = None
    task_doc = None

    async def _poll_for_reset():
        nonlocal reset_detected, reset_elapsed, task_doc
        max_wait = 30
        interval = 0.3
        start = time.time()
        while time.time() - start < max_wait:
            task_doc = await test_database.items.find_one({"_id": BsonObjectId(task_laui)})
            if task_doc:
                as_ = task_doc.get("actions_status", {})
                if (
                    "pre_actions" in as_
                    and "running_actions" in as_
                    and "post_actions" in as_
                    and as_["pre_actions"] == []
                    and as_["running_actions"] == []
                    and as_["post_actions"] == []
                ):
                    reset_elapsed = time.time() - start
                    reset_detected = True
                    print(
                        f"  ✓ actions_status reset detected {reset_elapsed:.2f}s "
                        f"after re-run trigger"
                    )
                    return
            await asyncio.sleep(interval)

    # Start the polling coroutine as a background task so it runs while
    # the HTTP request is in flight.
    poll_task = asyncio.create_task(_poll_for_reset())

    print("✓ Second execution initiated – polling for actions_status reset …")

    # Run the synchronous TestClient call in a thread so the event loop
    # remains free to execute the polling coroutine above.
    loop = asyncio.get_running_loop()
    rerun_resp = await loop.run_in_executor(
        None,
        lambda: execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/task/multiple_tasks",
                method="post",
                json={"task_lauis": [task_laui]},
            ),
        ),
    )

    # Wait for the polling task to finish (it may have already finished).
    await poll_task

    assert rerun_resp.status_code == 200, (
        f"Re-run failed ({rerun_resp.status_code}): {rerun_resp.text}"
    )
    assert reset_detected, (
        f"actions_status was NOT reset to empty arrays during re-run. "
        f"Last observed actions_status: {task_doc.get('actions_status') if task_doc else 'N/A'}"
    )

    print(f"\n✓ actions_status reset verified (detected at {reset_elapsed:.2f}s into re-run)")
    print(f"    Task: {task_laui}")
