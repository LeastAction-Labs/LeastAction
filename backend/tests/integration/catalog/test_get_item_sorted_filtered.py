# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
"""Integration tests for sorted and filtered get on task items."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from src.core.catalog.api_request import CreateItemResponse
from src.core.db.types import MongoDatabase
from tests.integration.schema import TestRequest
from tests.integration.utils import create_base_folders, execute_request

pytestmark = pytest.mark.anyio


@dataclass
class TaskTestContext:
    account_laui: str = ""
    project_laui: str = ""
    sort_workflow_laui: str = ""
    filter_workflow_laui: str = ""
    empty_workflow_laui: str = ""
    operator_laui: str = ""
    connection_laui: str = ""


def _create_item(client: TestClient, json: dict) -> str:
    url = "/api/v1/task/run" if json["item_type"] == "task" else "/api/v1/catalog/create"
    resp = execute_request(
        client=client,
        request=TestRequest(url=url, method="post", json=json),
    )
    assert resp.status_code == 200
    return CreateItemResponse(**resp.json()).item_laui


def _get_items(client: TestClient, item_laui: str, **extra_params) -> dict:
    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={
                "item_laui": item_laui,
                "item_type": "task",
                "parent_or_child": "child",
                **extra_params,
            },
        ),
    )
    assert resp.status_code == 200
    return resp.json()


def setup_test_environment(client: TestClient) -> TaskTestContext:
    ctx = TaskTestContext()
    ts = datetime.now().timestamp()

    base_folders = create_base_folders(client)

    ctx.account_laui = base_folders.account_folder_laui
    ctx.project_laui = base_folders.project_folder_laui
    ctx.sort_workflow_laui = _create_item(
        client,
        {
            "item_type": "folder.workflow",
            "name": f"sort_workflow_{ts}",
            "parent_laui": ctx.project_laui,
            "account_laui": ctx.account_laui,
            "project_laui": ctx.project_laui,
            "folder_metadata": {"state": "active"},
        },
    )
    ctx.filter_workflow_laui = _create_item(
        client,
        {
            "item_type": "folder.workflow",
            "name": f"filter_workflow_{ts}",
            "parent_laui": ctx.project_laui,
            "account_laui": ctx.account_laui,
            "project_laui": ctx.project_laui,
            "folder_metadata": {"state": "active"},
        },
    )
    ctx.empty_workflow_laui = _create_item(
        client,
        {
            "item_type": "folder.workflow",
            "name": f"empty_workflow_{ts}",
            "parent_laui": ctx.project_laui,
            "account_laui": ctx.account_laui,
            "project_laui": ctx.project_laui,
            "folder_metadata": {"state": "active"},
        },
    )
    ctx.operator_laui = _create_item(
        client,
        {
            "item_type": "operator.python",
            "name": f"operator_{ts}",
            "parent_laui": ctx.sort_workflow_laui,
            "codeblock": {
                "main.py": "def initialize(self):\n    return {}\ndef run(self, ctx):\n    return {'status': 'ok', 'execution_type': 'sync'}\ndef check_completion(self, ctx, state):\n    return {'status': 'done'}\ndef finish(self, ctx, state, result):\n    return None\n"
            },
            "bashblock": {"main.sh": "echo 'test'"},
            "account_laui": ctx.account_laui,
            "project_laui": ctx.project_laui,
        },
    )
    ctx.connection_laui = _create_item(
        client,
        {
            "item_type": "connection.python",
            "name": f"connection_{ts}",
            "parent_laui": ctx.sort_workflow_laui,
            "content": {"type": "docker"},
            "account_laui": ctx.account_laui,
            "project_laui": ctx.project_laui,
        },
    )
    return ctx


@pytest.fixture(autouse=True)
async def setup_catalog(client: TestClient, test_database: MongoDatabase):
    await test_database.items.drop()
    await test_database.links.delete_many({})

    ctx = setup_test_environment(client)
    now = datetime.now(UTC)

    # Sort workflow: 5 tasks with distinct logical_date and partition values
    # Creation order doesn't match sort order to verify sorting is applied
    sort_task_specs = [
        {"logical_date": (now - timedelta(days=4)).isoformat(), "partition": "C"},  # t0
        {"logical_date": (now - timedelta(days=2)).isoformat(), "partition": "A"},  # t1
        {"logical_date": (now - timedelta(days=3)).isoformat(), "partition": "E"},  # t2
        {"logical_date": (now - timedelta(days=1)).isoformat(), "partition": "B"},  # t3
        {"logical_date": (now - timedelta(days=5)).isoformat(), "partition": "D"},  # t4
    ]
    for i, spec in enumerate(sort_task_specs):
        _create_item(
            client,
            {
                "item_type": "task",
                "name": f"sort_task_{i}",
                "parent_laui": ctx.sort_workflow_laui,
                "project_laui": ctx.project_laui,
                "account_laui": ctx.account_laui,
                "operator_laui": ctx.operator_laui,
                "connection_laui": ctx.connection_laui,
                "state": "scheduled",
                **spec,
            },
        )

    # Filter workflow: needs its own operator + connection
    ts = datetime.now().timestamp()
    filter_operator_laui = _create_item(
        client,
        {
            "item_type": "operator.python",
            "name": f"filter_operator_{ts}",
            "parent_laui": ctx.filter_workflow_laui,
            "codeblock": {
                "main.py": "def initialize(self):\n    return {}\ndef run(self, ctx):\n    return {'status': 'ok', 'execution_type': 'sync'}\ndef check_completion(self, ctx, state):\n    return {'status': 'done'}\ndef finish(self, ctx, state, result):\n    return None\n"
            },
            "bashblock": {"main.sh": "echo 'test'"},
            "account_laui": ctx.account_laui,
            "project_laui": ctx.project_laui,
        },
    )
    filter_connection_laui = _create_item(
        client,
        {
            "item_type": "connection.python",
            "name": f"filter_connection_{ts}",
            "parent_laui": ctx.filter_workflow_laui,
            "content": {"type": "docker"},
            "account_laui": ctx.account_laui,
            "project_laui": ctx.project_laui,
        },
    )
    for i, state in enumerate(["scheduled", "scheduled", "scheduled", "success", "success"]):
        _create_item(
            client,
            {
                "item_type": "task",
                "name": f"filter_task_{i}",
                "parent_laui": ctx.filter_workflow_laui,
                "project_laui": ctx.project_laui,
                "account_laui": ctx.account_laui,
                "operator_laui": filter_operator_laui,
                "connection_laui": filter_connection_laui,
                "state": state,
            },
        )

    yield {
        "sort_workflow_laui": ctx.sort_workflow_laui,
        "filter_workflow_laui": ctx.filter_workflow_laui,
        "empty_workflow_laui": ctx.empty_workflow_laui,
    }

    await test_database.items.drop()
    await test_database.links.drop()


async def test_get_sorted(client: TestClient, setup_catalog: dict):
    sort_wf = setup_catalog["sort_workflow_laui"]
    empty_wf = setup_catalog["empty_workflow_laui"]

    # Sort by logical_date ascending — dates should be monotonically increasing
    result = _get_items(client, sort_wf, sort_by="logical_date", sort_order="asc")
    dates_asc = [item["item"]["logical_date"] for item in result["items"]]
    assert len(dates_asc) == 5
    assert dates_asc == sorted(dates_asc)

    # Sort by logical_date descending — dates should be monotonically decreasing
    result = _get_items(client, sort_wf, sort_by="logical_date", sort_order="desc")
    dates_desc = [item["item"]["logical_date"] for item in result["items"]]
    assert len(dates_desc) == 5
    assert dates_desc == sorted(dates_desc, reverse=True)

    # Sort by partition ascending — expect alphabetical order A, B, C, D, E
    result = _get_items(client, sort_wf, sort_by="partition", sort_order="asc")
    partitions = [item["item"]["partition"] for item in result["items"]]
    assert partitions == ["A", "B", "C", "D", "E"]

    # Empty workflow returns empty response
    result = _get_items(client, empty_wf, sort_by="logical_date", sort_order="asc")
    assert result["items"] == []
    assert result["pagination"]["has_next"] is False


async def test_get_filtered(client: TestClient, setup_catalog: dict):
    filter_wf = setup_catalog["filter_workflow_laui"]

    # Filter by state=scheduled — expect exactly 3 items
    result = _get_items(client, filter_wf, filter_state="scheduled")
    scheduled_items = result["items"]
    assert len(scheduled_items) == 3
    for item in scheduled_items:
        assert item["item"]["state"] == "scheduled"

    # Filter by state=success — expect exactly 2 items
    result = _get_items(client, filter_wf, filter_state="success")
    success_items = result["items"]
    assert len(success_items) == 2
    for item in success_items:
        assert item["item"]["state"] == "success"

    # Filter by nonexistent state — empty response
    result = _get_items(client, filter_wf, filter_state="nonexistent_xyz")
    assert result["items"] == []
    assert result["pagination"]["has_next"] is False
