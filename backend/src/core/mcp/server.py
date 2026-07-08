# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from src.common.context_vars.session_context import generate_session_id
from src.core.ai.prompts import AGENT_SYSTEM_PROMPT
from src.core.dataplane.executors import (
    _ROW_LIMIT,
    GCP_SERVICE_TOOLS,
    DataplaneError,
    _json_safe,
    gcp_read_call,
)
from src.core.dataplane.mcp_proxy import (
    AWS_MCP_SERVERS,
    AZURE_NAMESPACE_TOOLS,
    McpProxyManager,
    aws_env,
    azure_command_args,
    azure_env,
    execute_sql,
)
from src.core.mcp.api_client import mcp_api

CONFIG_SCHEMA_DIR = Path(__file__).resolve().parents[4] / "config" / "schema"


async def _resolve_connection_via_api(connection_laui: str) -> tuple[str, dict]:
    """Resolve a connection's (item_type, content) over the catalog HTTP API.

    MCP tools resolve connections via mcp_api (not the in-process orchestrator)
    because the /mcp request context lacks the request-scoped DB/transaction setup
    that the catalog repository needs — the same reason the other MCP tools call
    mcp_api. The cookie token carries the caller's identity, so access control and
    per-user scoping are enforced by the API.
    """
    item = await mcp_api("GET", "catalog/get", params={"item_laui": connection_laui})
    if not isinstance(item, dict) or item.get("error"):
        detail = item.get("error") if isinstance(item, dict) else str(item)
        raise DataplaneError(404, f"Connection item not found or access denied: {detail}")
    item_type = item.get("item_type") or ""
    if not item_type.startswith("connection."):
        raise DataplaneError(400, "Item is not a connection type.")
    raw = item.get("content") or item.get("data") or {}
    if isinstance(raw, str):
        raw = json.loads(raw or "{}")
    data: dict = raw if isinstance(raw, dict) else {}
    return item_type, data


# Native LeastAction platform tools (proxy the catalog API via mcp_api), plus the
# cross-cloud inspect_data SQL tool. Per-cloud service tools are added below from
# the executor/azure tables so the registry and admin UI can group them.
_LEASTACTION_TOOLS = [
    "get_my_access",
    "list_docs",
    "get_doc",
    "search_marketplace",
    "get_marketplace_item",
    "search_catalog",
    "get_catalog_item",
    "get_item_by_pk",
    "get_root_items",
    "get_children",
    "get_item_schema",
    "create_catalog_item",
    "create_link",
    "delete_item",
    "restore_item",
    "update_task",
    "create_task",
    "run_task",
    "create_action",
    "run_action",
    "reset_task",
    "get_task_status",
    "get_task_history",
    "list_session_log_files",
    "get_task_logs",
    "get_non_task_logs",
    "read_log_file",
    "query_logs",
    "inspect_data",
]

# Grouped tool registry, presented per-cloud in the admin UI and get_my_access.
# The wire format for allowed_mcp_tools stays a flat list[str]; this only adds
# grouping metadata. ALL_MCP_TOOLS is derived so every existing consumer works.
MCP_TOOL_GROUPS: dict[str, list[str]] = {
    "LeastAction": _LEASTACTION_TOOLS,
    "AWS": list(AWS_MCP_SERVERS),
    "GCP": list(GCP_SERVICE_TOOLS),
    "Azure": list(AZURE_NAMESPACE_TOOLS),
}

ALL_MCP_TOOLS = [tool for tools in MCP_TOOL_GROUPS.values() for tool in tools]


def _check_tool_access(tool_name: str) -> dict | None:
    """Returns an error dict if the tool is not permitted for the current user, or None if allowed."""
    from src.common.context_vars.user_context import get_allowed_mcp_tools

    allowed = get_allowed_mcp_tools()
    if allowed is None:
        return None
    if tool_name not in allowed:
        return {
            "error": f"Tool '{tool_name}' is not enabled for your account. Contact your administrator."
        }
    return None


def create_mcp_server(orchestrator, proxy: McpProxyManager | None = None) -> FastMCP:
    mcp = FastMCP("LeastAction Assistant", instructions=AGENT_SYSTEM_PROMPT)

    # Manager for proxied MCP subprocesses (awslabs servers + Azure MCP), one per
    # (connection, server) with the connection's creds injected as env. Shared with
    # the /query route (via app.state) so the Data Inspector reuses the same servers.
    if proxy is None:
        proxy = McpProxyManager()

    # ── Access info (always available, no restriction) ─────────────────

    @mcp.tool()
    def get_my_access() -> dict:
        """Returns the current user's MCP tool access. Shows which tools are enabled for your account."""
        from src.common.context_vars.user_context import (
            get_allowed_mcp_tools,
            get_user_laui,
            is_root_user,
        )

        allowed = get_allowed_mcp_tools()
        return {
            "user_laui": get_user_laui(),
            "is_root_user": is_root_user(),
            "has_full_access": allowed is None,
            "allowed_tools": ALL_MCP_TOOLS if allowed is None else allowed,
            "tool_groups": MCP_TOOL_GROUPS,
        }

    # ── Schema ─────────────────────────────────────────────────────────

    @mcp.tool()
    def get_item_schema(item_type: str) -> dict:
        """Get the full schema (fields, datatypes, required, constraints) for a given item type.
        Call this BEFORE create_catalog_item to know what fields to pass.

        item_type: one of task, operator, action, connection, payload, config, folder, chat, skill
        """
        if err := _check_tool_access("get_item_schema"):
            return err
        schema_path = CONFIG_SCHEMA_DIR / f"{item_type}.json"
        if not schema_path.exists():
            return {
                "error": f"No schema found for item_type '{item_type}'. Available: {[p.stem for p in CONFIG_SCHEMA_DIR.glob('*.json')]}"
            }
        schema = json.loads(schema_path.read_text())
        return {
            "columns": schema.get("columns", []),
            "unique_constraints": schema.get("unique_constraints", []),
        }

    # ── Docs ───────────────────────────────────────────────────────────

    @mcp.tool()
    async def list_docs() -> dict:
        """List all available documentation and AI prompt files.
        Returns relative paths to pass to get_doc().
        category 'docs' = /docs/ platform guides; 'ai_prompts' = /config/AI/ system prompts.
        """
        if err := _check_tool_access("list_docs"):
            return err
        return await mcp_api("GET", "docs/list")

    @mcp.tool()
    async def get_doc(path: str, category: str = "docs") -> dict:
        """Read a documentation or AI prompt file by its relative path.

        path: relative path returned by list_docs() (e.g. '04-concepts/07-workflow.md')
        category: 'docs' for platform docs, 'ai_prompts' for /config/AI/ files
        """
        if err := _check_tool_access("get_doc"):
            return err
        return await mcp_api("GET", "docs/get", params={"path": path, "category": category})

    # ── Search & Retrieve ──────────────────────────────────────────────

    @mcp.tool()
    async def search_catalog(
        item_type: str,
        name: str | None = None,
        parent_laui: str | None = None,
        page: int = 1,
        per_page: int = 10,
        sort_order: str = "asc",
        projection_include: list[str] | None = None,
        projection_exclude: list[str] | None = None,
        extra_filters: dict | None = None,
    ) -> dict:
        """Search for catalog items by type and optionally by name or parent.

        item_type: e.g. task, operator, action, connection, payload, config, folder.workflow, ai_skill, html_report
        name: optional name filter (partial match)
        parent_laui: optional parent item LAUI to scope search
        page: page number (default 1)
        per_page: results per page (default 10)
        sort_order: 'asc' or 'desc' (default 'asc')
        projection_include: list of fields to include in response (e.g. ['name', 'item_type'])
        projection_exclude: list of fields to exclude from response
        extra_filters: additional filter fields to merge into item_filter
        """
        if err := _check_tool_access("search_catalog"):
            return err
        item_filter: dict = {"item_type": item_type}
        if name:
            item_filter["name"] = name
        if parent_laui:
            item_filter["parent_laui"] = parent_laui
        if extra_filters:
            item_filter.update(extra_filters)
        projection: dict = {}
        if projection_include:
            projection["include"] = projection_include
        elif projection_exclude:
            projection["exclude"] = projection_exclude
        else:
            projection = {"include": ["name", "item_type", "action_variables"]}
        payload: dict = {
            "item_filter": item_filter,
            "projection": projection,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "sort_order": sort_order,
            },
        }
        return await mcp_api("POST", "catalog/search", json=payload)

    @mcp.tool()
    async def get_catalog_item(item_laui: str) -> dict:
        """Get a single item's full details by its LAUI (unique identifier)."""
        if err := _check_tool_access("get_catalog_item"):
            return err
        return await mcp_api("GET", "catalog/get", params={"item_laui": item_laui})

    @mcp.tool()
    async def get_item_by_pk(
        item_type: str,
        pk_fields: dict,
        projection_include: list[str] | None = None,
        projection_exclude: list[str] | None = None,
    ) -> dict:
        """Get a single item by its primary key fields. Faster than search_catalog.
        Only use when ALL pk fields are known. PK fields per type:
        - task: name, project_laui, account_laui, partition
        - action: name, project_laui, account_laui
        - operator/connection/folder/payload/config: name, parent_laui

        item_type: the item type (task, operator, action, etc.)
        pk_fields: dict of primary key fields, e.g. {"name": "MyTask", "project_laui": "...", "account_laui": "...", "partition": "ALL"}
        projection_include: optional list of fields to include in response
        projection_exclude: optional list of fields to exclude from response
        """
        if err := _check_tool_access("get_item_by_pk"):
            return err
        projection: dict = {}
        if projection_include:
            projection["include"] = projection_include
        elif projection_exclude:
            projection["exclude"] = projection_exclude
        payload: dict = {
            "item_filter": {
                "item_type": item_type,
                "get_by_pk": True,
                **pk_fields,
            },
        }
        if projection:
            payload["projection"] = projection
        return await mcp_api("POST", "catalog/search", json=payload)

    @mcp.tool()
    async def get_root_items(page: int = 1, per_page: int = 10) -> dict:
        """List top-level (root) items in the catalog.

        page: page number (default 1)
        per_page: results per page (default 10)
        """
        if err := _check_tool_access("get_root_items"):
            return err
        return await mcp_api(
            "GET",
            "catalog/get",
            params={
                "is_root": True,
                "page": page,
                "per_page": per_page,
            },
        )

    @mcp.tool()
    async def get_children(
        parent_laui: str,
        item_type: str | None = None,
        page: int = 1,
        per_page: int = 10,
    ) -> dict:
        """Get child items under a parent LAUI, optionally filtered by item_type.

        parent_laui: the parent item's LAUI
        item_type: optional filter (e.g. 'task', 'operator')
        page: page number (default 1)
        per_page: results per page (default 10, max 100)
        """
        if err := _check_tool_access("get_children"):
            return err
        clamped = max(1, min(per_page, 100))
        params: dict = {
            "item_laui": parent_laui,
            "parent_or_child": "child",
            "item_permission": "own",
            "page": page,
            "per_page": clamped,
        }
        if item_type:
            params["item_type"] = item_type
        return await mcp_api("GET", "catalog/get", params=params)

    # ── Create / Link / Delete ─────────────────────────────────────────

    @mcp.tool()
    async def create_catalog_item(
        name: str,
        item_type: str,
        parent_laui: str,
        extra_fields: dict | None = None,
    ) -> dict:
        """Create a new catalog item. BEFORE calling this, read the creation rules:
        get_doc(path="item_creation_rules.md", category="ai_prompts") for naming, required fields, code signatures, validation, and examples.
        Also call get_item_schema(item_type) to see all available fields.

        name: item name — operators must end with .operator, actions with .action, usecases with .usecase
        item_type: e.g. task, operator, operator.python, action, connection, payload, config, folder.workflow, ai_skill
        parent_laui: LAUI of the parent folder/item
        extra_fields: additional fields as a flat dict (codeblock, bashblock, description, operator_laui, etc.)

        Quick summary (full rules in item_creation_rules.md):
        - Operators need codeblock with main.py (4 functions: initialize, run, check_completion, finish) + bashblock
        - Actions need codeblock with main.py (1 function: def run(obj, **kwargs) -> bool) + bashblock
        - Tasks need project_laui, account_laui, operator_laui, connection_laui
        - All code is validated: no async, no subprocess/pickle/threading, no logging module, no secret leaks
        """
        if err := _check_tool_access("create_catalog_item"):
            return err
        payload = {
            "name": name,
            "item_type": item_type,
            "parent_laui": parent_laui,
            **(extra_fields or {}),
        }
        return await mcp_api("POST", "catalog/create", json=payload)

    @mcp.tool()
    async def create_link(parent_laui: str, child_laui: str) -> dict:
        """Create a soft link between two items (parent → child relationship)."""
        if err := _check_tool_access("create_link"):
            return err
        return await mcp_api(
            "POST",
            "catalog/create/link",
            json={
                "parent_laui": parent_laui,
                "child_laui": child_laui,
            },
        )

    @mcp.tool()
    async def delete_item(item_laui: str, parent_laui: str, hard_delete: bool = False) -> dict:
        """Delete a catalog item (soft delete to trash by default).

        item_laui: LAUI of the item to delete
        parent_laui: LAUI of the item's parent
        hard_delete: if True, permanently delete instead of moving to trash
        """
        if err := _check_tool_access("delete_item"):
            return err
        return await mcp_api(
            "POST",
            "catalog/delete",
            json={
                "item_laui": item_laui,
                "parent_laui": parent_laui,
                "hard_delete": hard_delete,
            },
        )

    @mcp.tool()
    async def restore_item(item_laui: str) -> dict:
        """Restore a previously deleted item from trash."""
        if err := _check_tool_access("restore_item"):
            return err
        return await mcp_api("POST", f"catalog/restore/{item_laui}")

    # ── Task creation, execution & management ────────────────────────────────────
    @mcp.tool()
    async def create_task(task_data: dict[str, Any]) -> dict:
        """Create a task"""
        if err := _check_tool_access("create_task"):
            return err
        return await mcp_api(
            "POST",
            "task",
            json=task_data,
        )

    @mcp.tool()
    async def run_task(task_laui: str) -> dict:
        """Run a task by its LAUI. The task must already exist with operator and connection configured."""
        if err := _check_tool_access("run_task"):
            return err
        return await mcp_api(
            "POST",
            "task",
            json={
                "item_type": "task",
                "item_laui": task_laui,
            },
        )

    @mcp.tool()
    async def get_task_status(task_laui: str) -> dict:
        """Get comprehensive diagnostics for a task: state, required items, connection queue status, heartbeats."""
        if err := _check_tool_access("get_task_status"):
            return err
        return await mcp_api("GET", f"task/diagnose/{task_laui}")

    @mcp.tool()
    async def get_task_history(
        task_laui: str,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict:
        """Get execution history for a task by reading TASK_HISTORY log files.
        Returns entries with: session_id, state, status, start_time, duration_seconds,
        logical_date, prev_interval_start, output, actions_status, and more.

        task_laui: LAUI of the task
        date_from: start date YYYY-MM-DD (default: 90 days ago)
        date_to: end date YYYY-MM-DD (default: today)

        IMPORTANT: date_from/date_to filter against the task's LOGICAL DATE (prev_interval_start),
        not the wall-clock date the task actually ran. A task with start_date 2026-01-15 has
        history stored under logical date folders (e.g. yyyy=2026/mm=01/dd=15), regardless of
        when it was executed. If results are empty, pass date_from matching the task's start_date.
        """
        if err := _check_tool_access("get_task_history"):
            return err
        from src.core.logs_details.service import LogsService

        today = datetime.now(UTC)
        date_to_dt = (
            datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=UTC) if date_to else today
        )
        date_from_dt = (
            datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=UTC)
            if date_from
            else today - timedelta(days=90)
        )

        dates = []
        cur = date_from_dt
        while cur <= date_to_dt:
            dates.append(cur.strftime("%Y-%m-%d"))
            cur += timedelta(days=1)

        service = LogsService()
        entries = []

        for date_str in dates:
            y, m, d = date_str.split("-")
            folder = f"category=TASK_HISTORY/task_laui={task_laui}/yyyy={y}/mm={m}/dd={d}"
            try:
                result = await service.list_folder_items(folder)
            except Exception:
                continue

            history_files = [
                item
                for item in result.get("items", [])
                if item.get("type") == "file"
                and item.get("name", "").endswith(".log")
                and not item.get("name", "").startswith("latest_")
            ]

            for file_item in sorted(history_files, key=lambda x: x.get("name", "")):
                file_path = file_item.get("path") or f"{folder}/{file_item['name']}"
                try:
                    file_data = await service.get_file_details(file_path)
                    content = file_data.get("content", "")
                except Exception:
                    continue

                merged: dict = {}
                for raw_line in content.splitlines():
                    trimmed = raw_line.strip()
                    if not trimmed.startswith("{"):
                        continue
                    try:
                        outer = json.loads(trimmed)
                        merged.update(outer)
                        if isinstance(outer.get("message"), str) and outer[
                            "message"
                        ].strip().startswith("{"):
                            try:
                                merged.update(json.loads(outer["message"]))
                            except Exception:
                                pass
                    except Exception:
                        pass

                if not merged:
                    continue

                if isinstance(merged.get("output"), str):
                    try:
                        merged["output"] = json.loads(merged["output"])
                    except Exception:
                        pass

                if not merged.get("status"):
                    output_err = (
                        (merged.get("output") or {}).get("error")
                        if isinstance(merged.get("output"), dict)
                        else None
                    )
                    if output_err:
                        merged["status"] = "error"
                    elif merged.get("user_set_state") == "cancel":
                        merged["status"] = "cancelled"
                    elif merged.get("state") in {
                        "success",
                        "error",
                        "failed",
                        "fail",
                        "timeout",
                        "cancelled",
                    }:
                        merged["status"] = merged["state"]
                    else:
                        merged["status"] = merged.get("state", "unknown")

                entries.append(
                    {
                        **merged,
                        "fileName": file_item.get("name"),
                        "_date": date_str,
                    }
                )

        entries.sort(
            key=lambda x: x.get("start_time") or x.get("task_instance_start_date") or "",
            reverse=True,
        )
        return {
            "task_laui": task_laui,
            "date_from": date_from_dt.strftime("%Y-%m-%d"),
            "date_to": date_to_dt.strftime("%Y-%m-%d"),
            "total": len(entries),
            "entries": entries,
        }

    @mcp.tool()
    async def get_task_logs(
        task_laui: str,
        session_id: str,
        date: str | None = None,
        tail: int = 0,
    ) -> dict:
        """Fetch parsed execution logs for a task session.

        task_laui: LAUI of the task
        session_id: the session ID from run_task, get_task_status, or get_task_history
        date: specific date YYYY-MM-DD to search (default: searches today and last 2 days)
        tail: if > 0, return only the last N lines
        """
        if err := _check_tool_access("get_task_logs"):
            return err
        from datetime import datetime, timedelta

        from src.core.logs_details.service import LogsService

        service = LogsService()
        dates = (
            [date]
            if date
            else [(datetime.now(UTC) - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(3)]
        )

        all_lines: list[str] = []
        found_folder = None
        for date_str in dates:
            y, m, d = date_str.split("-")
            folder = f"verbose=TASK/yyyy={y}/mm={m}/dd={d}/task_laui={task_laui}/session_id={session_id}/category=TASK"
            try:
                result = await service.list_folder_items(folder)
            except Exception:
                continue
            log_files = [
                i
                for i in result.get("items", [])
                if i.get("type") == "file" and i.get("name", "").endswith(".log")
            ]
            if not log_files:
                continue
            found_folder = folder
            for file_item in sorted(log_files, key=lambda x: x.get("name", "")):
                file_path = file_item.get("path") or f"{folder}/{file_item['name']}"
                try:
                    file_data = await service.get_file_details(file_path)
                    content = file_data.get("content", "")
                except Exception:
                    continue
                all_lines.extend(l for l in content.splitlines() if l.strip())
            break

        if not found_folder:
            debug_items = []
            if dates:
                y, m, d = dates[0].split("-")
                folder = f"verbose=TASK/yyyy={y}/mm={m}/dd={d}/task_laui={task_laui}/session_id={session_id}/category=TASK"
                try:
                    debug_result = await service.list_folder_items(folder)
                    debug_items = debug_result.get("items", [])
                except Exception as e:
                    debug_items = [{"error": str(e)}]
            return {
                "error": "No log files found",
                "searched_dates": dates,
                "task_laui": task_laui,
                "session_id": session_id,
                "debug_items": debug_items,
            }

        if tail > 0:
            all_lines = all_lines[-tail:]

        parsed = []
        for line in all_lines:
            try:
                parsed.append(json.loads(line))
            except Exception:
                parsed.append({"raw": line})

        return {
            "task_laui": task_laui,
            "session_id": session_id,
            "folder": found_folder,
            "total_lines": len(parsed),
            "lines": parsed,
        }

    @mcp.tool()
    async def get_non_task_logs(
        session_id: str,
        date: str | None = None,
        category: str = "CELERY",
        tail: int = 0,
    ) -> dict:
        """Fetch logs for a session from the NON_TASK log store (CELERY worker logs, API logs).

        Use this when get_task_logs returns no useful error details — operator exceptions and
        tracebacks are written to the CELERY category, not the TASK category.

        session_id: the session ID from run_task or get_task_history
        date: logical date YYYY-MM-DD (prev_interval_start) — CELERY logs are indexed by logical date, not wall-clock run date (default: today and last 2 days)
        category: log category — "CELERY" (operator tracebacks) or "API" (request logs). Default: CELERY
        tail: if > 0, return only the last N lines
        """
        if err := _check_tool_access("get_non_task_logs"):
            return err
        from datetime import datetime, timedelta

        from src.core.logs_details.service import LogsService

        service = LogsService()
        dates = (
            [date]
            if date
            else [(datetime.now(UTC) - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(3)]
        )

        all_lines: list[str] = []
        found_folder = None
        for date_str in dates:
            y, m, d = date_str.split("-")
            folder = f"verbose=NON_TASK/yyyy={y}/mm={m}/dd={d}/session_id={session_id}/category={category}"
            try:
                result = await service.list_folder_items(folder)
            except Exception:
                continue
            log_files = [
                i
                for i in result.get("items", [])
                if i.get("type") == "file" and i.get("name", "").endswith(".log")
            ]
            if not log_files:
                continue
            found_folder = folder
            for file_item in sorted(log_files, key=lambda x: x.get("name", "")):
                file_path = file_item.get("path") or f"{folder}/{file_item['name']}"
                try:
                    file_data = await service.get_file_details(file_path)
                    content = file_data.get("content", "")
                except Exception:
                    continue
                all_lines.extend(l for l in content.splitlines() if l.strip())
            break

        if not found_folder:
            return {
                "error": f"No {category} log files found",
                "searched_dates": dates,
                "session_id": session_id,
            }

        if tail > 0:
            all_lines = all_lines[-tail:]

        parsed = []
        for line in all_lines:
            try:
                parsed.append(json.loads(line))
            except Exception:
                parsed.append({"raw": line})

        return {
            "session_id": session_id,
            "category": category,
            "folder": found_folder,
            "total_lines": len(parsed),
            "lines": parsed,
        }

    @mcp.tool()
    async def list_session_log_files(session_id: str) -> dict:
        """List all log files and categories available for a session.
        Use this to discover what log files exist before calling read_log_file.

        session_id: the session ID from run_task or get_task_history
        """
        if err := _check_tool_access("list_session_log_files"):
            return err
        from src.core.logs_details.service import LogsService

        service = LogsService()
        return await service.get_logs_by_session_id(session_id)

    @mcp.tool()
    async def read_log_file(file_path: str, skip: int = 0, limit: int = 400) -> dict:
        """Read a specific log file by its path (from list_session_log_files).
        Pages backward from the end of file — newest lines appear last.

        file_path: relative log file path returned by list_session_log_files
        skip: lines from the end already loaded (0 = start from last line)
        limit: number of lines to return (default 400)
        """
        if err := _check_tool_access("read_log_file"):
            return err
        from src.core.logs_details.service import LogsService

        service = LogsService()
        chunks = [c async for c in service.iter_file_lines_paged(file_path, skip=skip, limit=limit)]
        if not chunks:
            return {"file_path": file_path, "content": "", "total_lines": 0, "has_more": False}
        return {"file_path": file_path, **chunks[0]}

    @mcp.tool()
    async def query_logs(sql: str, category: str = None, date: str = None) -> dict:
        """Run a SQL SELECT query against application logs using DuckDB.

        category is REQUIRED. Omitting it returns an error immediately.
        date is strongly recommended — without it the full category is scanned.

        category: limit scan to one log source —
                    "PERFORMANCE"  → API timing logs (category=PERFORMANCE/yyyy/mm/dd/)
                    "CRON"         → scheduler logs (category=CRON/project=*/yyyy/mm/dd/)
                    "TASK_HISTORY" → task run history (category=TASK_HISTORY/task_laui=*/yyyy/mm/dd/)
                    "CELERY"       → worker tracebacks (verbose=NON_TASK/yyyy/mm/dd/session_id=*/category=CELERY/)
                    "API"          → API request logs (verbose=NON_TASK/yyyy/mm/dd/session_id=*/category=API/)
                    "TASK"         → task execution logs (verbose=TASK/yyyy/mm/dd/)
        date:     limit scan to one day — "YYYY-MM-DD"
        sql:      SELECT or WITH query (no semicolons, no DDL/DML)

        Common columns: timestamp, level, step, session_id, message, category,
                        operation, task_laui, task_name, logical_date

        Examples:
          query_logs(sql="SELECT operation, COUNT(*) FROM logs GROUP BY operation ORDER BY 2 DESC",
                     category="PERFORMANCE", date="2026-05-21")
          query_logs(sql="SELECT * FROM logs WHERE level='error' ORDER BY timestamp DESC LIMIT 50",
                     category="CRON", date="2026-05-21")
          query_logs(sql="SELECT * FROM logs WHERE session_id='<id>' ORDER BY timestamp",
                     category="TASK_HISTORY", date="2026-05-21")
        """
        if err := _check_tool_access("query_logs"):
            return err
        return await mcp_api(
            "POST", "logs/query", json={"sql": sql, "category": category, "date": date}
        )

    @mcp.tool()
    async def inspect_data(connection_laui: str, sql: str) -> dict:
        """Sample and inspect data from any catalog connection — the primary tool for
        post-task verification and pipeline debugging.

        Use cases:
        - Did the task load data? → SELECT COUNT(*) FROM <table>
        - Sample what landed → SELECT * FROM <table> LIMIT 20
        - Inspect an S3 file → SELECT * FROM read_parquet('s3://bucket/file.parquet') LIMIT 50
        - Check null rates → SELECT COUNT(*) - COUNT(col) FROM <table>
        - Detect type mismatches → SELECT typeof(col), COUNT(*) FROM <table> GROUP BY 1
        - Find duplicates → SELECT col, COUNT(*) FROM <table> GROUP BY col HAVING COUNT(*) > 1
        - CSV parse errors → SELECT * FROM read_csv('s3://...', ignore_errors=true, store_rejects=true)

        connection_laui: LAUI of a connection catalog item (item_type starts with "connection.")
        sql: SELECT or WITH query — INSERT/UPDATE/DELETE/DDL are blocked; session is read-only

        Supported connection types: PostgreSQL, MySQL, AWS Athena, AWS Redshift,
        BigQuery, S3 (connection.s3), GCS (connection.gcs), Azure Blob (connection.azure)

        Returns: {"columns": [...], "rows": [[...], ...], "row_count": N, "truncated": bool}
        Max 10,000 rows. Returns error dict on connection failure or SQL error.

        Workflow:
        1. run_task(task_laui=<id>) → get session_id
        2. get_task_logs(task_laui=<id>, session_id=<id>) → confirm success
        3. inspect_data(connection_laui=<conn_id>, sql="SELECT COUNT(*) FROM <target_table>") → verify data landed
        4. If count is wrong or data looks off, inspect with more queries, fix the task, and re-run

        Find the right connection_laui with:
          search_catalog(item_type="connection", name="<connection name>")
        """
        if err := _check_tool_access("inspect_data"):
            return err
        try:
            item_type, data = await _resolve_connection_via_api(connection_laui)
            columns, rows = await execute_sql(proxy, connection_laui, item_type, data, sql)
        except DataplaneError as e:
            return {"error": e.detail}
        except TimeoutError:
            return {"error": "Query timed out after 2 minutes."}
        truncated = len(rows) > _ROW_LIMIT
        if truncated:
            rows = rows[:_ROW_LIMIT]
        return {
            "columns": columns,
            "rows": _json_safe(rows),
            "row_count": len(rows),
            "truncated": truncated,
        }

    @mcp.tool()
    async def reset_task(task_laui: str) -> dict:
        """Reset a task back to 'scheduled' state, clearing run output and actions status. Use with caution."""
        if err := _check_tool_access("reset_task"):
            return err
        return await mcp_api("POST", f"task/dangerously_reset/{task_laui}")

    # ── Action tools ───────────────────────────────────────────────────
    @mcp.tool()
    async def create_action(action_data: dict[str, Any]) -> dict:
        """Create an action"""
        if err := _check_tool_access("create_action"):
            return err
        return await mcp_api(
            "POST",
            "action",
            json=action_data,
        )

    @mcp.tool()
    async def run_action(
        action_laui: str | None = None,
        item_type: str = "action",
        connection_laui: str | None = None,
        action_variables: dict = {},
    ) -> dict:
        """Execute a standalone action by its LAUI.

        action_laui: LAUI of an existing action to execute
        item_type: action type (default 'action')
        connection_laui: optional connection to use for the action
        action_variables: optional variables to pass to the action

        Returns a dict that always includes a `session_id` — the id this run's logs
        are written under. The action runs under that session_id (sent as the
        X-Session-ID header). Use it to fetch execution detail when you need to
        confirm delivery or diagnose a failure (e.g. a Slack/email send returning
        false): `get_non_task_logs(session_id=<id>, category="CELERY")` for the
        operator traceback, or `category="API"` for the request log.
        """
        if action_variables is None:
            action_variables = {}
        if err := _check_tool_access("run_action"):
            return err
        # Generate the session_id client-side and pass it as X-Session-ID so the
        # action's logs are written under a known id we can return to the caller.
        # Mirrors the frontend runAction() flow (crypto.randomUUID + X-Session-ID).
        session_id = generate_session_id()
        payload = {"item_type": item_type}
        if action_laui:
            payload["item_laui"] = action_laui
        if connection_laui:
            payload["connection_laui"] = connection_laui
        if action_variables is not None:
            payload["action_variables"] = action_variables
        result = await mcp_api("POST", "action", json=payload, headers={"X-Session-ID": session_id})
        response = dict(result) if isinstance(result, dict) else {"result": result}
        response["session_id"] = session_id
        return response

    # ── Marketplace tools ───────────────────────────────────────────────

    @mcp.tool()
    async def search_marketplace(
        name: str | None = None,
        item_type: str | None = None,
        publisher: str | None = None,
        category: str | None = None,
        division: str | None = None,
        tags: list[str] | None = None,
        page: int = 1,
        per_page: int = 10,
        sort_order: str = "asc",
    ) -> dict:
        """Search the marketplace for reusable operators, actions, payloads, ai_skills, and usecases.

        page: page number (default 1)
        per_page: results per page (default 10)
        sort_order: 'asc' or 'desc' (default 'asc')
        """
        if err := _check_tool_access("search_marketplace"):
            return err
        try:
            import httpx

            from src.common.utils import MARKETPLACE_BACKEND_NETLOC

            url = f"http://{MARKETPLACE_BACKEND_NETLOC}/api/v1/marketplace/catalog/search"
            item_filter: dict = {}
            if name:
                item_filter["name"] = name
            if item_type:
                item_filter["item_type"] = item_type
            if publisher:
                item_filter["publisher"] = publisher
            if category:
                item_filter["category"] = category
            if division:
                item_filter["division"] = division
            if tags:
                item_filter["tags"] = tags
            if not item_filter:
                item_filter["item_type"] = "operator"
            payload: dict = {
                "item_filter": item_filter,
                "projection": {
                    "include": [
                        "name",
                        "item_type",
                        "publisher",
                        "category",
                        "division",
                        "tags",
                        "description",
                    ]
                },
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "sort_order": sort_order,
                },
            }
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(url, json=payload)
            if not resp.is_success:
                return {"error": f"Marketplace search failed: {resp.status_code} {resp.text}"}
            from src.core.api.utils import convert_objectid_to_str

            return convert_objectid_to_str(resp.json())
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    async def get_marketplace_item(item_laui: str) -> dict:
        """Get full details of a marketplace item by its laui ID."""
        if err := _check_tool_access("get_marketplace_item"):
            return err
        try:
            import httpx

            from src.common.utils import MARKETPLACE_BACKEND_NETLOC

            url = f"http://{MARKETPLACE_BACKEND_NETLOC}/api/v1/marketplace/catalog/get"
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url, params={"item_laui": item_laui})
            if not resp.is_success:
                return {"error": f"Marketplace get failed: {resp.status_code} {resp.text}"}
            from src.core.api.utils import convert_objectid_to_str

            return convert_objectid_to_str(resp.json())
        except Exception as e:
            return {"error": str(e)}

    # ── Cloud per-service tools (one tool per service, gated individually) ──────
    # Generated from the server/service tables so each registers under its own
    # name. Per-tool gating means a user granted only `aws_redshift` cannot reach
    # `aws_s3`, `gcp_compute`, or `azure_storage`.

    def _make_aws_tool(tool_name: str, command: str, args: list[str]):
        async def _aws_tool(
            connection_laui: str, tool: str | None = None, parameters: dict | None = None
        ) -> dict:
            if err := _check_tool_access(tool_name):
                return err
            try:
                item_type, data = await _resolve_connection_via_api(connection_laui)
                if item_type != "connection.AWS":
                    return {"error": f"Connection is '{item_type}', expected connection.AWS."}
                env = aws_env(data)
                cache_key = f"{connection_laui}:{tool_name}"
                if not tool:
                    return await proxy.list_tools(cache_key, command, args, env)
                return await proxy.call(cache_key, command, args, env, tool, parameters)
            except DataplaneError as e:
                return {"error": e.detail}

        _aws_tool.__name__ = tool_name
        _aws_tool.__doc__ = (
            f"AWS operations proxied to the official awslabs MCP server '{command}', using "
            f"credentials from a connection item.\n\n"
            f"connection_laui: LAUI of a connection.AWS catalog item\n"
            f"tool: the underlying awslabs tool to run (e.g. execute_query, list_clusters). "
            f"Omit to list the available tools and their schemas.\n"
            f"parameters: dict of arguments for the chosen tool."
        )
        return _aws_tool

    for _tool_name, _spec in AWS_MCP_SERVERS.items():
        _command = _spec["command"]
        _args = _spec.get("args", [])
        mcp.tool()(_make_aws_tool(_tool_name, _command, _args))

    def _make_gcp_tool(tool_name: str, api: str, version: str):
        async def _gcp_tool(
            connection_laui: str,
            method: str,
            parameters: dict | None = None,
            resource_path: str | None = None,
        ) -> dict:
            if err := _check_tool_access(tool_name):
                return err
            try:
                item_type, data = await _resolve_connection_via_api(connection_laui)
                if item_type != "connection.gcp":
                    return {"error": f"Connection is '{item_type}', expected connection.gcp."}
                return await asyncio.to_thread(
                    gcp_read_call, data, api, version, method, parameters, resource_path
                )
            except DataplaneError as e:
                return {"error": e.detail}

        _gcp_tool.__name__ = tool_name
        _gcp_tool.__doc__ = (
            f"Read-only Google Cloud {api}/{version} operations using credentials from a "
            f"connection item (service-account JSON).\n\n"
            f"connection_laui: LAUI of a connection.gcp catalog item\n"
            f"method: a read-only Discovery verb (list, get, aggregatedList, search). "
            f"Write methods are rejected.\n"
            f"resource_path: dotted nested-resource path (e.g. 'instances'); omit for top-level\n"
            f"parameters: dict of request parameters for the method."
        )
        return _gcp_tool

    for _tool_name, (_api, _version) in GCP_SERVICE_TOOLS.items():
        mcp.tool()(_make_gcp_tool(_tool_name, _api, _version))

    def _make_azure_tool(tool_name: str, prefixes: tuple[str, ...]):
        async def _azure_tool(
            connection_laui: str, tool: str | None = None, parameters: dict | None = None
        ) -> dict:
            if err := _check_tool_access(tool_name):
                return err
            try:
                item_type, data = await _resolve_connection_via_api(connection_laui)
                if item_type != "connection.azure":
                    return {"error": f"Connection is '{item_type}', expected connection.azure."}
                env = azure_env(data)
                command, args = azure_command_args()
                # One Azure MCP per connection (all namespaces); gate by prefix here.
                cache_key = f"{connection_laui}:azure"
                if not tool:
                    return await proxy.list_tools(cache_key, command, args, env, prefixes)
                if not tool.startswith(prefixes):
                    return {
                        "error": f"Tool '{tool}' is not in the '{tool_name}' namespace "
                        f"(allowed prefixes: {', '.join(prefixes)})."
                    }
                return await proxy.call(cache_key, command, args, env, tool, parameters)
            except DataplaneError as e:
                return {"error": e.detail}

        _azure_tool.__name__ = tool_name
        _azure_tool.__doc__ = (
            f"Read-only Azure operations in the '{tool_name}' namespace, proxied to the "
            f"official Azure MCP server using the connection's service principal.\n\n"
            f"connection_laui: LAUI of a connection.azure catalog item (with service-principal "
            f"creds: tenant_id, client_id, client_secret, subscription_id)\n"
            f"tool: the underlying azmcp tool name to run (must be in this namespace). "
            f"Omit to list the available tools and their schemas.\n"
            f"parameters: dict of arguments for the chosen azmcp tool."
        )
        return _azure_tool

    for _tool_name, _prefixes in AZURE_NAMESPACE_TOOLS.items():
        mcp.tool()(_make_azure_tool(_tool_name, _prefixes))

    return mcp
