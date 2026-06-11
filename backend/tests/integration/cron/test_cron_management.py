# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from dataclasses import dataclass
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from src.core.catalog.api_request import CreateItemResponse
from src.core.cron.schema import CronAction
from src.core.db.types import MongoDatabase
from tests.integration.schema import TestRequest
from tests.integration.utils import create_base_folders, execute_request

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def database_cleanup(test_database: MongoDatabase):
    await test_database.items.drop()
    await test_database.links.delete_many({})
    yield  # Test runs here
    await test_database.items.drop()
    await test_database.links.drop()


@dataclass
class TestContext:
    """Container for all test resources"""

    account_laui: str = ""
    project_laui: str = ""
    workflow_1_laui: str = ""
    workflow_2_laui: str = ""


def setup_test_environment(client: TestClient, include_workflows: bool = True) -> TestContext:
    """
    Create test environment with configurable components.
    """
    ctx = TestContext()
    ts = datetime.now().timestamp()
    base_folders = create_base_folders(client)
    ctx.account_laui = base_folders.account_folder_laui
    ctx.project_laui = base_folders.project_folder_laui

    print(f"\n[Setup] Created project: {ctx.project_laui}")

    if not include_workflows:
        return ctx

    # Create workflows
    for i, attr in enumerate(["workflow_1_laui", "workflow_2_laui"], 1):
        resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/catalog/create",
                method="post",
                json={
                    "item_type": "folder.workflow",
                    "name": f"workflow_{i}_{ts}",
                    "parent_laui": ctx.project_laui,
                    "account_laui": ctx.account_laui,
                    "project_laui": ctx.project_laui,
                    "folder_metadata": {"state": "active"},
                },
            ),
        )
        assert resp.status_code == 200
        setattr(ctx, attr, CreateItemResponse(**resp.json()).item_laui)
        print(f"[Setup] Created workflow {i}: {getattr(ctx, attr)}")

    return ctx


async def test_start_cron_for_project_pass(client: TestClient):
    """Test successfully starting cron for a project."""
    ctx = setup_test_environment(client=client, include_workflows=False)

    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/cron/manage",
            method="post",
            json={
                "project_laui": ctx.project_laui,
                "action": CronAction.START,
            },
        ),
    )

    if resp.status_code != 200:
        print(f"\nError response: {resp.status_code}")
        print(f"Error body: {resp.json()}")

    assert resp.status_code == 200
    assert resp.json()["success"] is True
    assert resp.json()["action"] == CronAction.START


async def test_stop_cron_for_project_pass(client: TestClient):
    """Test successfully stopping cron for a project."""
    import asyncio

    ctx = setup_test_environment(client=client, include_workflows=False)

    # Start first
    start_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/cron/manage",
            method="post",
            json={"project_laui": ctx.project_laui, "action": CronAction.START},
        ),
    )
    assert start_resp.status_code == 200
    await asyncio.sleep(2)

    # Stop - this will set status to STOP
    stop_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/cron/manage",
            method="post",
            json={
                "project_laui": ctx.project_laui,
                "action": CronAction.STOP,
            },
        ),
    )
    if stop_resp.status_code != 200:
        print(f"\nStop error response: {stop_resp.status_code}")
        print(f"Stop error body: {stop_resp.json()}")
    assert stop_resp.status_code == 200

    # Poll for STOPPED status (executor will update STOP -> STOPPED)
    # Wait for up to 15 seconds (executor runs every 5 seconds by default)
    max_attempts = 20
    for attempt in range(max_attempts):
        resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/catalog/get", method="get", params={"item_laui": ctx.project_laui}
            ),
        )
        assert resp.status_code == 200
        folder_metadata = resp.json()["folder_metadata"]
        cron_status = folder_metadata["cron_status"]
        print(
            f"\nAttempt {attempt}: status={cron_status}, heartbeat={folder_metadata.get('latest_heartbeat')}, error={folder_metadata.get('error')}"
        )
        if attempt == 0 or attempt == max_attempts - 1:
            print(
                f"\nAttempt {attempt}: status={cron_status}, heartbeat={folder_metadata.get('latest_heartbeat')}, error={folder_metadata.get('error')}"
            )

        if cron_status == "STOPPED":
            break

        if attempt == max_attempts - 1:
            raise AssertionError(
                f"Expected STOPPED status, but got {cron_status} after {max_attempts} attempts"
            )

        await asyncio.sleep(2)  # Check every 2 seconds

    assert resp.json()["folder_metadata"]["cron_status"] == "STOPPED"


async def test_start_cron_already_running_fail(client: TestClient):
    """Test that starting cron twice fails with 409 Conflict."""
    ctx = setup_test_environment(client=client, include_workflows=False)

    execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/cron/manage",
            method="post",
            json={"project_laui": ctx.project_laui, "action": CronAction.START},
        ),
    )
    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/cron/manage",
            method="post",
            json={"project_laui": ctx.project_laui, "action": CronAction.START},
        ),
    )

    assert resp.status_code == 409


async def test_stop_cron_not_running_fail(client: TestClient):
    """Test that stopping a non-running cron fails with 404 Not Found."""
    ctx = setup_test_environment(client=client, include_workflows=False)

    resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/cron/manage",
            method="post",
            json={
                "project_laui": ctx.project_laui,
                "action": CronAction.STOP,
            },
        ),
    )

    assert resp.status_code == 404
