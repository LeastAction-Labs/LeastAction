# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from fastmcp import Client as MCPClient

from src.common.context_vars.user_context import (
    set_allowed_mcp_tools,
    set_current_token,
    set_root_user_laui,
    set_user_laui,
)
from src.core.db.types import MongoDatabase
from src.core.mcp.server import ALL_MCP_TOOLS, _check_tool_access, create_mcp_server
from tests.integration.schema import BaseFolders
from tests.integration.utils import (
    create_base_folders,
    get_session_service,
)

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def database_cleanup(test_database: MongoDatabase):
    await test_database.items.drop()
    await test_database.links.delete_many({})
    yield
    await test_database.items.drop()
    await test_database.links.drop()


@pytest.fixture(autouse=True)
def base_folders_setup(client: TestClient, database_cleanup):
    base_folders = create_base_folders(client)
    yield base_folders


@pytest.fixture()
def mcp_ctx(client: TestClient):
    cookie = client.headers.get("Cookie", "")
    token = cookie.split("frontend_token=")[1].split(";")[0]
    print(token)
    claims = get_session_service().verify_jwt_token(token)
    user_laui = claims.sub
    print(user_laui)
    set_user_laui(user_laui)
    set_root_user_laui(user_laui)
    set_current_token(token)
    set_allowed_mcp_tools(None)

    mcp = create_mcp_server(client.app.state.item_orchestrator)
    return mcp


def _patch_mcp_api(client: TestClient):
    async def patched_mcp_api(method: str, path: str, **kwargs):
        url = f"/api/v1/{path}"
        response = client.request(method, url, **kwargs)
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            return {"error": detail}
        return response.json()

    return patch("src.core.mcp.server.mcp_api", side_effect=patched_mcp_api)


async def _call_tool(mcp_server, name: str, args: dict | None = None) -> dict:
    async with MCPClient(mcp_server) as c:
        result = await c.call_tool(name, args or {})
    content = result.content if hasattr(result, "content") else result
    text = content[0].text if content else "{}"
    return json.loads(text)


async def test_tool_access_restriction(mcp_ctx, client: TestClient):
    mcp = mcp_ctx
    restricted_tools = ["get_my_access", "search_catalog"]
    set_allowed_mcp_tools(restricted_tools)

    with _patch_mcp_api(client):
        data = await _call_tool(mcp, "get_my_access")
        assert data["has_full_access"] is False
        assert set(data["allowed_tools"]) == set(restricted_tools)

        data = await _call_tool(
            mcp,
            "search_catalog",
            {
                "item_type": "folder.account",
                "page": 1,
                "per_page": 5,
            },
        )
        assert "not enabled" not in json.dumps(data)

        blocked_tools = [t for t in ALL_MCP_TOOLS if t not in restricted_tools]
        for tool_name in blocked_tools:
            result = _check_tool_access(tool_name)
            assert result is not None, f"{tool_name} should be blocked"
            assert "not enabled" in result["error"], f"{tool_name} missing error message"

        data = await _call_tool(mcp, "get_item_schema", {"item_type": "task"})
        assert "error" in data and "not enabled" in data["error"]

        data = await _call_tool(mcp, "run_task", {"task_laui": "fake"})
        assert "error" in data and "not enabled" in data["error"]

        data = await _call_tool(mcp, "delete_item", {"item_laui": "fake", "parent_laui": "fake"})
        assert "error" in data and "not enabled" in data["error"]

        data = await _call_tool(
            mcp,
            "create_catalog_item",
            {
                "name": "x",
                "item_type": "folder",
                "parent_laui": "fake",
            },
        )
        assert "error" in data and "not enabled" in data["error"]

        data = await _call_tool(mcp, "run_action", {"action_laui": "fake"})
        assert "error" in data and "not enabled" in data["error"]


async def test_all_tools_accessible_with_full_access(
    mcp_ctx,
    client: TestClient,
    base_folders_setup: BaseFolders,
):
    mcp = mcp_ctx
    base_folders = base_folders_setup
    set_allowed_mcp_tools(None)

    with _patch_mcp_api(client):
        # ── Verify all tools are registered and accessible ──────────────
        async with MCPClient(mcp) as c:
            tools = await c.list_tools()
        registered = [t.name for t in tools]
        assert len(registered) > 0

        for tool_name in registered:
            assert _check_tool_access(tool_name) is None, (
                f"'{tool_name}' should be allowed with full access"
            )

        # ── get_my_access ───────────────────────────────────────────────
        data = await _call_tool(mcp, "get_my_access")
        assert data["has_full_access"] is True
        assert "user_laui" in data
        assert "is_root_user" in data
        assert set(data["allowed_tools"]) == set(ALL_MCP_TOOLS)

        # ── get_item_schema ─────────────────────────────────────────────
        data = await _call_tool(mcp, "get_item_schema", {"item_type": "task"})
        assert "error" not in data
        assert "columns" in data
        assert isinstance(data["columns"], list)
        assert len(data["columns"]) > 0
        assert "unique_constraints" in data

        # ── list_docs ───────────────────────────────────────────────────
        data = await _call_tool(mcp, "list_docs")
        assert "error" not in data
        assert "docs" in data
        assert "ai_prompts" in data
        assert isinstance(data["docs"], list)
        assert isinstance(data["ai_prompts"], list)

        # ── search_catalog ──────────────────────────────────────────────
        data = await _call_tool(
            mcp,
            "search_catalog",
            {
                "item_type": "folder.account",
                "page": 1,
                "per_page": 5,
            },
        )
        assert "error" not in data
        assert "items" in data
        assert isinstance(data["items"], list)
        assert "pagination" in data
        assert data["pagination"]["current_page"] == 1
        assert "has_next" in data["pagination"]

        # ── get_root_items ──────────────────────────────────────────────
        data = await _call_tool(mcp, "get_root_items", {"page": 1, "per_page": 5})
        assert "error" not in data
        assert "items" in data
        assert isinstance(data["items"], list)
        assert "pagination" in data

        # ── create_catalog_item ─────────────────────────────────────────
        data = await _call_tool(
            mcp,
            "create_catalog_item",
            {
                "name": "mcp_test_folder",
                "item_type": "folder.workflow",
                "parent_laui": base_folders.project_folder_laui,
                "extra_fields": {
                    "account_laui": base_folders.account_folder_laui,
                    "project_laui": base_folders.project_folder_laui,
                },
            },
        )
        assert "error" not in data
        assert "item_laui" in data
        created_laui = data["item_laui"]
        assert isinstance(created_laui, str)
        assert len(created_laui) > 0

        # ── get_catalog_item ────────────────────────────────────────────
        data = await _call_tool(mcp, "get_catalog_item", {"item_laui": created_laui})
        assert "error" not in data
        assert "name" in data
        assert data["name"] == "mcp_test_folder"
        assert "item_type" in data

        # ── get_children ────────────────────────────────────────────────
        data = await _call_tool(
            mcp,
            "get_children",
            {
                "parent_laui": base_folders.project_folder_laui,
                "page": 1,
                "per_page": 5,
            },
        )
        assert "error" not in data
        assert "items" in data
        assert isinstance(data["items"], list)
        assert "pagination" in data
        child_names = [item["item"]["name"] for item in data["items"]]
        assert "mcp_test_folder" in child_names

        # ── get_item_by_pk ──────────────────────────────────────────────
        data = await _call_tool(
            mcp,
            "get_item_by_pk",
            {
                "item_type": "folder",
                "pk_fields": {
                    "name": "mcp_test_folder",
                    "parent_laui": base_folders.project_folder_laui,
                },
            },
        )
        assert "error" not in data
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) == 1

        # ── delete_item (soft) ──────────────────────────────────────────
        data = await _call_tool(
            mcp,
            "delete_item",
            {
                "item_laui": created_laui,
                "parent_laui": base_folders.project_folder_laui,
                "hard_delete": False,
            },
        )
        assert "error" not in data
        assert data.get("message") == "Item deleted successfully"

        # ── restore_item ────────────────────────────────────────────────
        data = await _call_tool(mcp, "restore_item", {"item_laui": created_laui})
        assert "error" not in data
        assert data.get("message") == "Item restored successfully"

        # ── create_link ─────────────────────────────────────────────────
        # Create a config item under the workflow folder, then link it
        # to a second workflow folder
        data = await _call_tool(
            mcp,
            "create_catalog_item",
            {
                "name": "mcp_link_config",
                "item_type": "config",
                "parent_laui": created_laui,
                "extra_fields": {
                    "content": {},
                    "config_type": "system",
                    "account_laui": base_folders.account_folder_laui,
                    "project_laui": base_folders.project_folder_laui,
                },
            },
        )
        assert "error" not in data
        config_laui = data["item_laui"]

        # Create a second workflow folder to link the config into
        data = await _call_tool(
            mcp,
            "create_catalog_item",
            {
                "name": "mcp_link_target_folder",
                "item_type": "folder.workflow",
                "parent_laui": base_folders.project_folder_laui,
                "extra_fields": {
                    "account_laui": base_folders.account_folder_laui,
                    "project_laui": base_folders.project_folder_laui,
                },
            },
        )
        assert "error" not in data
        link_parent_laui = data["item_laui"]

        data = await _call_tool(
            mcp,
            "create_link",
            {
                "parent_laui": link_parent_laui,
                "child_laui": config_laui,
            },
        )
        assert "error" not in data
        assert "link_laui" in data
        assert isinstance(data["link_laui"], str)

        # ── Task tools with nonexistent laui (expect errors, not "not enabled") ──
        data = await _call_tool(mcp, "get_task_status", {"task_laui": "nonexistent"})
        assert "not enabled" not in json.dumps(data)
        assert "error" in data

        data = await _call_tool(
            mcp,
            "update_task",
            {
                "task_laui": "nonexistent",
                "updates": {"priority": 1},
            },
        )
        assert "not enabled" not in json.dumps(data)
        assert "error" in data

        data = await _call_tool(mcp, "reset_task", {"task_laui": "nonexistent"})
        assert "not enabled" not in json.dumps(data)
        assert "error" in data

        data = await _call_tool(mcp, "run_task", {"task_laui": "nonexistent"})
        assert "not enabled" not in json.dumps(data)
        assert "error" in data

        data = await _call_tool(mcp, "run_action", {"action_laui": "nonexistent"})
        assert "not enabled" not in json.dumps(data)
        assert "error" in data

        # ── get_task_history (no log files for nonexistent → empty entries) ──
        data = await _call_tool(mcp, "get_task_history", {"task_laui": "nonexistent"})
        assert "error" not in data
        assert data["task_laui"] == "nonexistent"
        assert "total" in data
        assert isinstance(data["total"], int)
        assert "entries" in data
        assert isinstance(data["entries"], list)
        assert "date_from" in data
        assert "date_to" in data

        # ── Marketplace tools (expect errors since no marketplace in test) ──
        data = await _call_tool(
            mcp,
            "search_marketplace",
            {
                "item_type": "operator",
                "page": 1,
                "per_page": 5,
            },
        )
        assert "not enabled" not in json.dumps(data)
        assert "error" in data

        data = await _call_tool(mcp, "get_marketplace_item", {"item_laui": "nonexistent"})
        assert "not enabled" not in json.dumps(data)
        assert "error" in data
