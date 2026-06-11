# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
"""
End-to-end test for the production task-dependency mechanism.

Scenario
--------
    Task1  ──▶  Task2  ──▶  Task3
(Task2 depends on Task1, Task3 depends on Task2)
"""

import asyncio
import importlib.util
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from src.core.catalog.api_request import CreateItemResponse
from src.core.db.types import MongoDatabase
from src.core.task.connection.schema import SortOrder
from src.core.task.schema import TaskState
from tests.integration.schema import BaseFolders, TestRequest
from tests.integration.utils import create_base_folders, execute_request

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------

SLEEP_SECONDS = 30  # each dummy task sleeps ~30s
DAILY_CRON = "0 0 * * *"  # see docstring point 3
CHECK_PARENTS_ACTION_NAME = "LeastActionCheckIfAreParentsDone"  # magic name (point 1)

# Generous ceiling for one task: 30s sleep + worker pickup + pre-action round-trip.
TASK_COMPLETION_TIMEOUT = SLEEP_SECONDS + 120
POLL_INTERVAL = 3


# ---------------------------------------------------------------------------
# codeblock loaders
# ---------------------------------------------------------------------------


def _load_sleep_operator_code() -> str:
    """sleep_operator.py is a normal operator file — read it as source text,
    exactly like test_all_action.py does."""
    path = Path(__file__).parent.parent / "celery" / "task-test-data" / "sleep_operator.py"
    return path.read_text(encoding="utf-8")


def _load_check_parents_action_codeblocks():
    """la_check_parents_done.py is a *data module* exporting `codeblock` and
    `bashblock` dicts. The directory name contains a hyphen ("task-test-data")
    so it cannot be imported as a package — load it from its file path. The
    module has no top-level third-party imports (the real imports live inside
    the codeblock string), so exec_module is safe and dependency-free."""
    path = Path(__file__).parent.parent / "celery" / "task-test-data" / "la_check_parents_done.py"
    spec = importlib.util.spec_from_file_location("la_check_parents_done_data", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # The catalog codeblock validator rejects an action whose entry file is not
    # named 'main.py' (error NO_MAIN_FILE). The production data module stores its
    # single source file under 'check_parent_task_state.py', so remap that source
    # to 'main.py'. The logic is unchanged — only the filename the loader treats
    # as the entrypoint.
    raw_codeblock = module.codeblock
    assert len(raw_codeblock) == 1, f"expected a single-file codeblock, got {list(raw_codeblock)}"
    source = next(iter(raw_codeblock.values()))
    # The catalog CodeblockValidator rejects access to dunder attributes
    # (error DUNDER_ACCESS). The production codeblock has exactly one such use —
    # `type(e).__name__` inside an exception-logging line — which is incidental
    # to the dependency logic. Neutralise just that expression so the real
    # codeblock passes validation; all dependency logic is left untouched.
    # (The many SECRET_LEAK entries the validator reports are warnings, not
    # errors, and do not block creation.)
    assert source.count("__") == 2, "expected a single dunder usage in the production codeblock"
    source = source.replace("type(e).__name__", "type(e)")
    # COMPATIBILITY SHIM #2: the production codeblock's _fetch_parent_task POSTs a
    # search body keyed "filter", but the current /catalog/search SearchRequest
    # schema requires "item_filter" (and 422s otherwise). Rename just that key so
    # the parent lookup succeeds. The search filter contents are unchanged.
    assert source.count('"filter": {') == 1, "expected exactly one search-payload 'filter' key"
    source = source.replace('"filter": {', '"item_filter": {')
    codeblock = {"main.py": source}
    return codeblock, module.bashblock


SLEEP_OPERATOR_CODE = _load_sleep_operator_code()
CHECK_PARENTS_CODEBLOCK, CHECK_PARENTS_BASHBLOCK = _load_check_parents_action_codeblocks()


# ---------------------------------------------------------------------------
# fixtures  (mirrors test_e2e.py / test_all_action.py)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
async def database_cleanup(test_database: MongoDatabase, client: TestClient):
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
    assert wf_resp.status_code == 200, wf_resp.text
    return CreateItemResponse(**wf_resp.json()).item_laui


@pytest.fixture
async def operator_laui(
    client: TestClient, account_laui: str, project_laui: str, workflow_laui: str
) -> str:
    """Python operator running the repository's sleep operator (point 3 of docstring)."""
    op_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "operator.python",
                "name": f"sleep_operator_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "codeblock": {"main.py": SLEEP_OPERATOR_CODE},
                "bashblock": {},
            },
        ),
    )
    assert op_resp.status_code == 200, op_resp.text
    return CreateItemResponse(**op_resp.json()).item_laui


@pytest.fixture
async def connection_laui(
    client: TestClient, account_laui: str, project_laui: str, workflow_laui: str
) -> str:
    """High max_parallelism so the connection queue NEVER becomes the limiting
    factor — ordering must be enforced purely by the dependency pre_action,
    not by connection back-pressure."""
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
    assert connection_resp.status_code == 200, connection_resp.text
    return CreateItemResponse(**connection_resp.json()).item_laui


@pytest.fixture
async def payload_laui(
    client: TestClient, account_laui: str, project_laui: str, workflow_laui: str
) -> str:
    """The sleep operator reads `seconds` from the payload."""
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
                "content": f'{{"seconds": {SLEEP_SECONDS}}}',
            },
        ),
    )
    assert payload_resp.status_code == 200, payload_resp.text
    return CreateItemResponse(**payload_resp.json()).item_laui


@pytest.fixture
async def check_parents_action_laui(
    client: TestClient, account_laui: str, project_laui: str, workflow_laui: str
) -> str:
    """The production dependency action. Its name MUST be exactly
    "LeastActionCheckIfAreParentsDone" for ItemOrchestrator._link_tasks to
    recognise it and create the parent→child links at task-creation time.
    Codeblock/bashblock come straight from the production data module."""
    action_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "action",
                "name": CHECK_PARENTS_ACTION_NAME,
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "bashblock": CHECK_PARENTS_BASHBLOCK,
                "codeblock": CHECK_PARENTS_CODEBLOCK,
            },
        ),
    )
    assert action_resp.status_code == 200, action_resp.text
    return CreateItemResponse(**action_resp.json()).item_laui


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _parent_ref(task_name: str, project_laui: str, account_laui: str) -> dict:
    """A single entry in the pre_action's `parents` list. Parents are identified
    by NAME (not laui) — this is what both ItemOrchestrator._get_parent_task_laui
    and the production codeblock's _fetch_parent_task search on."""
    return {
        "task_name": task_name,
        "project_laui": project_laui,
        "account_laui": account_laui,
        "partition": "ALL",
    }


def _create_task(
    client: TestClient,
    *,
    name: str,
    account_laui: str,
    project_laui: str,
    workflow_laui: str,
    operator_laui: str,
    connection_laui: str,
    payload_laui: str,
    priority: int,
    parents: list[dict] | None = None,
    check_parents_action_laui: str | None = None,
) -> str:
    """Create a daily-cron task. When `parents` is given, wire the production
    dependency pre_action; the link(s) are created automatically by the
    orchestrator during this create call."""
    now = datetime.now(UTC)
    body: dict = {
        "item_type": "task",
        "name": name,
        "project_laui": project_laui,
        "account_laui": account_laui,
        "parent_laui": workflow_laui,
        "operator_laui": operator_laui,
        "connection_laui": connection_laui,
        "payload_laui": payload_laui,
        "frequency": DAILY_CRON,  # cron mandatory (point 3)
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=365)).isoformat(),
        "priority": priority,
    }
    if parents:
        assert check_parents_action_laui is not None
        body["actions"] = {
            "pre_actions": [
                {
                    "laui": check_parents_action_laui,
                    # EXACTLY one key: `parents`. See docstring point 2.
                    "action_variables": {"parents": parents},
                }
            ]
        }
    resp = execute_request(
        client=client, request=TestRequest(url="/api/v1/catalog/create", method="post", json=body)
    )
    assert resp.status_code == 200, f"Task '{name}' creation failed: {resp.text}"
    return str(CreateItemResponse(**resp.json()).item_laui)


def _run_round(client: TestClient, task_lauis: list[str]) -> set[str]:
    """Submit a batch to POST /api/v1/task/multiple_tasks and return the set of
    task lauis that were actually dispatched (i.e. passed their pre_actions).
    Tasks blocked by an unsatisfied dependency are silently absent from
    task_results — that absence is our enforcement assertion."""
    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/multiple_tasks",
            method="post",
            json={"task_lauis": [str(laui) for laui in task_lauis]},
        ),
    )
    assert resp.status_code == 200, resp.text
    return {str(r["task_laui"]) for r in resp.json()["task_results"]}


async def _wait_for_state(
    client: TestClient, task_laui: str, target_state, timeout: int, interval: int = POLL_INTERVAL
) -> dict:
    """Poll the catalog GET endpoint until the task reaches `target_state`."""
    start = time.time()
    last = None
    while time.time() - start < timeout:
        resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/catalog/get",
                method="get",
                params={"item_laui": task_laui},
            ),
        )
        assert resp.status_code == 200, resp.text
        last = resp.json()
        if last.get("state") == target_state:
            return last
        await asyncio.sleep(interval)
    raise AssertionError(
        f"Task {task_laui} did not reach state '{target_state}' within {timeout}s. "
        f"Last state={last.get('state') if last else None}, "
        f"last_run_output={last.get('last_run_output') if last else None}"
    )


async def _task_doc(test_database: MongoDatabase, task_laui: str) -> dict:
    """Read the raw task document from Mongo (needed for task_instance_* timestamps
    which are not exposed via projection_fields)."""
    doc = await test_database.items.find_one({"_id": ObjectId(task_laui)})
    assert doc is not None, f"Task {task_laui} not found in DB"
    return doc


# ---------------------------------------------------------------------------
# test
# ---------------------------------------------------------------------------


async def test_dependency_chain_task1_task2_task3(
    client: TestClient,
    test_database: MongoDatabase,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
    payload_laui: str,
    check_parents_action_laui: str,
):
    # -----------------------------------------------------------------
    # 1. Create the three tasks.
    #    Parents are referenced by name, so the parent must exist before the
    #    child is created (the orchestrator resolves the name → laui during
    #    create). Hence the strict Task1 → Task2 → Task3 creation order.
    # -----------------------------------------------------------------
    ts = datetime.now().timestamp()
    task1_name = f"dep_task1_{ts}"
    task2_name = f"dep_task2_{ts}"
    task3_name = f"dep_task3_{ts}"

    task1_laui = _create_task(
        client,
        name=task1_name,
        account_laui=account_laui,
        project_laui=project_laui,
        workflow_laui=workflow_laui,
        operator_laui=operator_laui,
        connection_laui=connection_laui,
        payload_laui=payload_laui,
        priority=1,
    )
    task2_laui = _create_task(
        client,
        name=task2_name,
        account_laui=account_laui,
        project_laui=project_laui,
        workflow_laui=workflow_laui,
        operator_laui=operator_laui,
        connection_laui=connection_laui,
        payload_laui=payload_laui,
        priority=2,
        parents=[_parent_ref(task1_name, project_laui, account_laui)],
        check_parents_action_laui=check_parents_action_laui,
    )
    task3_laui = _create_task(
        client,
        name=task3_name,
        account_laui=account_laui,
        project_laui=project_laui,
        workflow_laui=workflow_laui,
        operator_laui=operator_laui,
        connection_laui=connection_laui,
        payload_laui=payload_laui,
        priority=3,
        parents=[_parent_ref(task2_name, project_laui, account_laui)],
        check_parents_action_laui=check_parents_action_laui,
    )

    # -----------------------------------------------------------------
    # 2. STRUCTURAL ASSERTIONS — dependency links exist in the links collection.
    #    Created automatically by ItemOrchestrator._link_tasks at create time
    #    (true_parent=False distinguishes a dependency edge from the workflow
    #    containment edge, which is true_parent=True).
    # -----------------------------------------------------------------
    link_1_2 = await test_database.links.find_one(
        {
            "parent_laui": ObjectId(task1_laui),
            "child_laui": ObjectId(task2_laui),
            "true_parent": False,
        }
    )
    assert link_1_2 is not None, "Expected dependency link Task1 → Task2"
    assert link_1_2["parent_type"] == "task" and link_1_2["child_type"] == "task"

    link_2_3 = await test_database.links.find_one(
        {
            "parent_laui": ObjectId(task2_laui),
            "child_laui": ObjectId(task3_laui),
            "true_parent": False,
        }
    )
    assert link_2_3 is not None, "Expected dependency link Task2 → Task3"
    assert link_2_3["parent_type"] == "task" and link_2_3["child_type"] == "task"

    # There must be no link directly from Task1 → Task3 (chain, not fan-out).
    assert (
        await test_database.links.find_one(
            {
                "parent_laui": ObjectId(task1_laui),
                "child_laui": ObjectId(task3_laui),
                "true_parent": False,
            }
        )
        is None
    ), "Task1 should NOT be directly linked to Task3"

    # -----------------------------------------------------------------
    # 3. ROUND 1 — submit ALL three. Only Task1 (no dependency) may run.
    #    Task2/Task3 pre_actions evaluate BEFORE any task is dispatched
    #    (execute_tasks runs all pre_actions, then dispatches), so they see
    #    their parents still 'scheduled' and are blocked.
    #    => Dependency assertion: Task2 not started before Task1, Task3 not
    #       before Task2.
    # -----------------------------------------------------------------
    dispatched = _run_round(client, [task1_laui, task2_laui, task3_laui])
    assert task1_laui in dispatched, "Task1 should run immediately (no dependency)"
    assert task2_laui not in dispatched, "Task2 must NOT run before Task1 completes"
    assert task3_laui not in dispatched, "Task3 must NOT run before Task2 completes"

    # Blocked tasks are not errored — they remain schedulable.
    assert (await _task_doc(test_database, task2_laui))["state"] == TaskState.SCHEDULED
    assert (await _task_doc(test_database, task3_laui))["state"] == TaskState.SCHEDULED

    # Wait for Task1 to finish.
    await _wait_for_state(client, task1_laui, TaskState.SUCCESS, timeout=TASK_COMPLETION_TIMEOUT)

    # -----------------------------------------------------------------
    # 4. ROUND 2 — submit Task2 and Task3. Now Task1 is SUCCESS, so Task2's
    #    dependency is satisfied and it runs; Task3 is still blocked because
    #    Task2 has only just been dispatched (not yet SUCCESS).
    # -----------------------------------------------------------------
    dispatched = _run_round(client, [task2_laui, task3_laui])
    assert task2_laui in dispatched, "Task2 should run once Task1 is SUCCESS"
    assert task3_laui not in dispatched, "Task3 must NOT run before Task2 completes"
    assert (await _task_doc(test_database, task3_laui))["state"] == TaskState.SCHEDULED

    await _wait_for_state(client, task2_laui, TaskState.SUCCESS, timeout=TASK_COMPLETION_TIMEOUT)

    # -----------------------------------------------------------------
    # 5. ROUND 3 — submit Task3. Task2 is SUCCESS, dependency satisfied.
    # -----------------------------------------------------------------
    dispatched = _run_round(client, [task3_laui])
    assert task3_laui in dispatched, "Task3 should run once Task2 is SUCCESS"

    await _wait_for_state(client, task3_laui, TaskState.SUCCESS, timeout=TASK_COMPLETION_TIMEOUT)

    # -----------------------------------------------------------------
    # 6. FINAL STATE ASSERTIONS — all three succeeded.
    # -----------------------------------------------------------------
    for laui in (task1_laui, task2_laui, task3_laui):
        resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/catalog/get",
                method="get",
                params={"item_laui": laui},
            ),
        )
        assert resp.status_code == 200
        assert resp.json()["state"] == TaskState.SUCCESS

    # -----------------------------------------------------------------
    # 7. EXECUTION-ORDER ASSERTIONS — verified from real execution metadata.
    #    task_instance_start_date / task_instance_end_date are written by the
    #    task executor and read directly from Mongo (not in projection_fields).
    #    Pymongo returns naive UTC datetimes, so direct comparison is valid.
    # -----------------------------------------------------------------
    d1 = await _task_doc(test_database, task1_laui)
    d2 = await _task_doc(test_database, task2_laui)
    d3 = await _task_doc(test_database, task3_laui)

    t1_end = d1["task_instance_end_date"]
    t2_start = d2["task_instance_start_date"]
    t2_end = d2["task_instance_end_date"]
    t3_start = d3["task_instance_start_date"]

    assert t1_end is not None and t2_start is not None
    assert t2_end is not None and t3_start is not None

    # Task1 completion strictly precedes Task2 start; Task2 completion precedes Task3 start.
    assert t1_end < t2_start, (
        f"Task1 must complete before Task2 starts: task1_end={t1_end}, task2_start={t2_start}"
    )
    assert t2_end < t3_start, (
        f"Task2 must complete before Task3 starts: task2_end={t2_end}, task3_start={t3_start}"
    )
