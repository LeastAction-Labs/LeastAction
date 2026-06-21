# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
"""Proxy official cloud MCP servers (AWS awslabs + Azure) with per-connection creds.

We don't maintain cloud API client code. Per connection we spawn the official MCP
server (stdio) with the connection's credentials injected as environment variables,
then talk to it via fastmcp.Client. One LeastAction tool maps to one upstream
server (AWS) or one server namespace (Azure), so per-user gating via
allowed_mcp_tools is automatically per-service.
"""

import asyncio
import os
import time

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from src.core.dataplane.executors import (
    _AWS_SYNONYMS,
    _AZURE_SYNONYMS,
    _build_boto3_session,
    _json_safe,
    _pick,
    DataplaneError,
)

# ── Server registries ───────────────────────────────────────────────────────────

# AWS: LeastAction tool → awslabs MCP server console script. Each subprocess is a
# single awslabs server, so granting `aws_redshift` cannot reach `aws_s3`.
AWS_MCP_SERVERS: dict[str, dict] = {
    "aws_redshift": {"command": "awslabs.redshift-mcp-server"},
    # --allow-sensitive-data-access lets get-query-results return row data (read-only).
    "aws_athena": {
        "command": "awslabs.aws-dataprocessing-mcp-server",
        "args": ["--allow-sensitive-data-access"],
    },
    "aws_s3": {"command": "awslabs.s3-tables-mcp-server"},
    "aws_cloudwatch": {"command": "awslabs.cloudwatch-mcp-server"},
    "aws_cost": {"command": "awslabs.billing-cost-management-mcp-server"},
    "aws_docs": {"command": "awslabs.aws-documentation-mcp-server"},  # no creds needed
}

# Pin the Azure MCP server version; pre-baked into the image.
AZURE_MCP_PACKAGE = "@azure/mcp@0.5.0"

# Azure: one official server, exposed per namespace. LeastAction tool → allowed
# azmcp_* tool-name prefixes (the namespaces it may reach).
AZURE_NAMESPACE_TOOLS: dict[str, tuple[str, ...]] = {
    "azure_storage": ("azmcp_storage_",),
    "azure_monitor": ("azmcp_monitor_",),
    "azure_cosmos": ("azmcp_cosmos_",),
    "azure_sql": ("azmcp_sql_",),
    "azure_aks": ("azmcp_aks_",),
    "azure_keyvault": ("azmcp_keyvault_",),
    "azure_resources": ("azmcp_group_", "azmcp_subscription_"),
}

_IDLE_TIMEOUT_SECONDS = 600  # evict an idle server after 10 min


# ── Credential → environment builders ───────────────────────────────────────────


def _base_env() -> dict[str, str]:
    """Minimal env so node/uvx resolve; we inject only the cloud creds on top."""
    env: dict[str, str] = {}
    for key in ("PATH", "HOME", "NODE_PATH", "npm_config_cache", "UV_CACHE_DIR"):
        if os.environ.get(key):
            env[key] = os.environ[key]
    return env


def aws_env(data: dict) -> dict[str, str]:
    """Resolve connection creds (keys / session token / assume_role) into AWS_* env."""
    region = _pick(data, "region", _AWS_SYNONYMS, "us-east-1")
    try:
        creds = _build_boto3_session(data).get_credentials()
    except Exception as e:
        raise DataplaneError(502, f"Cannot resolve AWS credentials from connection: {e}")
    env = _base_env()
    env["AWS_REGION"] = str(region)
    env["AWS_DEFAULT_REGION"] = str(region)
    if creds is not None:
        frozen = creds.get_frozen_credentials()
        env["AWS_ACCESS_KEY_ID"] = frozen.access_key
        env["AWS_SECRET_ACCESS_KEY"] = frozen.secret_key
        if frozen.token:
            env["AWS_SESSION_TOKEN"] = frozen.token
    return env


def azure_env(data: dict) -> dict[str, str]:
    """Service-principal creds → AZURE_* env for DefaultAzureCredential."""
    tenant = _pick(data, "tenant_id", _AZURE_SYNONYMS)
    client_id = _pick(data, "client_id", _AZURE_SYNONYMS)
    client_secret = _pick(data, "client_secret", _AZURE_SYNONYMS)
    subscription = _pick(data, "subscription_id", _AZURE_SYNONYMS)
    missing = [
        name
        for name, val in (
            ("tenant_id", tenant),
            ("client_id", client_id),
            ("client_secret", client_secret),
            ("subscription_id", subscription),
        )
        if not val
    ]
    if missing:
        raise DataplaneError(
            400,
            "Azure connection missing service-principal fields for control-plane access: "
            f"{missing}. Add tenant_id / client_id / client_secret / subscription_id.",
        )
    env = _base_env()
    env.update(
        {
            "AZURE_TENANT_ID": str(tenant),
            "AZURE_CLIENT_ID": str(client_id),
            "AZURE_CLIENT_SECRET": str(client_secret),
            "AZURE_SUBSCRIPTION_ID": str(subscription),
        }
    )
    return env


def azure_command_args() -> tuple[str, list[str]]:
    return "npx", [
        "-y",
        AZURE_MCP_PACKAGE,
        "server",
        "start",
        "--transport",
        "stdio",
        "--read-only",
    ]


def _result_payload(result) -> object:
    """Best-effort JSON-safe payload from a fastmcp CallToolResult.

    Prefers the MCP structured output (a dict), then the deserialized .data
    (model_dump if it's a pydantic model), then concatenated text content.
    """
    sc = getattr(result, "structured_content", None)
    if sc is not None:
        return _json_safe(sc)
    data = getattr(result, "data", None)
    if data is not None:
        if hasattr(data, "model_dump"):
            try:
                return _json_safe(data.model_dump(mode="json"))
            except Exception:
                pass
        return _json_safe(data)
    blocks = getattr(result, "content", None) or []
    texts = [getattr(b, "text", None) for b in blocks if getattr(b, "text", None)]
    return "\n".join(texts) if texts else None


# ── Generic proxy manager ────────────────────────────────────────────────────────


class _Entry:
    __slots__ = ("client", "lock", "last_used")

    def __init__(self, client: Client):
        self.client = client
        self.lock = asyncio.Lock()
        self.last_used = time.monotonic()


class McpProxyManager:
    """Spawns and caches one upstream MCP server (stdio) per cache key."""

    def __init__(self) -> None:
        self._entries: dict[str, _Entry] = {}
        self._cache_lock = asyncio.Lock()

    async def _get_entry(
        self, cache_key: str, command: str, args: list[str], env: dict[str, str]
    ) -> _Entry:
        async with self._cache_lock:
            await self._evict_idle_locked()
            entry = self._entries.get(cache_key)
            if entry is None:
                # Some awslabs servers (e.g. billing-cost-management) try to create a
                # log dir inside their own root-owned package folder at import, which
                # the non-root runtime user can't write. Pointing FASTMCP_LOG_FILE at a
                # writable per-server path under /tmp avoids that crash.
                spawn_env = dict(env)
                spawn_env.setdefault(
                    "FASTMCP_LOG_FILE", f"/tmp/fastmcp-{cache_key.replace(':', '_')}.log"
                )
                transport = StdioTransport(
                    command=command, args=args, env=spawn_env, keep_alive=True
                )
                entry = _Entry(Client(transport))
                self._entries[cache_key] = entry
            entry.last_used = time.monotonic()
            return entry

    async def _evict_idle_locked(self) -> None:
        now = time.monotonic()
        stale = [k for k, e in self._entries.items() if now - e.last_used > _IDLE_TIMEOUT_SECONDS]
        for k in stale:
            entry = self._entries.pop(k)
            try:
                await entry.client.close()
            except Exception:
                pass

    async def call(
        self,
        cache_key: str,
        command: str,
        args: list[str],
        env: dict[str, str],
        tool: str,
        parameters: dict | None,
    ) -> dict:
        entry = await self._get_entry(cache_key, command, args, env)
        async with entry.lock:
            try:
                async with entry.client as client:
                    result = await client.call_tool(tool, parameters or {})
            except Exception as e:
                raise DataplaneError(502, f"MCP call '{tool}' failed: {e}")
        return {"tool": tool, "result": _result_payload(result)}

    async def list_tools(
        self,
        cache_key: str,
        command: str,
        args: list[str],
        env: dict[str, str],
        prefixes: tuple[str, ...] | None = None,
    ) -> dict:
        entry = await self._get_entry(cache_key, command, args, env)
        async with entry.lock:
            try:
                async with entry.client as client:
                    tools = await client.list_tools()
            except Exception as e:
                raise DataplaneError(502, f"MCP list_tools failed: {e}")
        out = [
            {"name": t.name, "description": t.description, "input_schema": t.inputSchema}
            for t in tools
            if prefixes is None or t.name.startswith(prefixes)
        ]
        return {"tools": out}

    async def aclose(self) -> None:
        async with self._cache_lock:
            for entry in self._entries.values():
                try:
                    await entry.client.close()
                except Exception:
                    pass
            self._entries.clear()


# ── SQL delegation: route Athena/Redshift SELECTs through the awslabs servers ─────
# So the human Data Inspector (and inspect_data) can run AWS SQL without the agent,
# reusing the same upstream servers as the AWS tools (no boto3 query code).

import asyncio  # noqa: E402

from src.core.dataplane.executors import (  # noqa: E402
    _AWS_SYNONYMS,
    _ROW_LIMIT,
    run_query,
)


def _is_athena(data: dict) -> bool:
    return bool(_pick(data, "output_location", _AWS_SYNONYMS))


def _is_redshift(data: dict) -> bool:
    return bool(
        _pick(data, "cluster_identifier", _AWS_SYNONYMS)
        or _pick(data, "workgroup_name", _AWS_SYNONYMS)
    )


def _adapt_redshift(payload) -> tuple[list[str], list[list]]:
    # redshift-mcp execute_query returns QueryResult{columns, rows, row_count}.
    body = payload.get("result") if isinstance(payload, dict) else None
    if isinstance(body, dict) and "columns" in body and "rows" in body:
        return list(body.get("columns") or []), [list(r) for r in (body.get("rows") or [])]
    raise DataplaneError(502, f"Unexpected Redshift result shape: {payload}")


def _adapt_athena_result_set(result_set: dict) -> tuple[list[str], list[list]]:
    # Standard Athena ResultSet: ResultSetMetadata.ColumnInfo[].Name + Rows[].Data[].VarCharValue
    meta = (result_set.get("ResultSetMetadata") or {}).get("ColumnInfo") or []
    columns = [c.get("Name") or c.get("Label") or "" for c in meta]
    raw_rows = result_set.get("Rows") or []
    rows: list[list] = []
    for i, row in enumerate(raw_rows):
        cells = [c.get("VarCharValue") for c in (row.get("Data") or [])]
        # Athena's first row repeats the header when ColumnInfo is present.
        if i == 0 and columns and cells == columns:
            continue
        rows.append(cells)
    return columns, rows


async def aws_sql_query(
    proxy: McpProxyManager, connection_laui: str, data: dict, sql: str
) -> tuple[list[str], list[list]]:
    """Run an AWS Athena/Redshift SELECT via the awslabs MCP servers, returning
    (columns, rows) — the same shape as the in-process SQL drivers."""
    env = aws_env(data)
    if _is_redshift(data):
        spec = AWS_MCP_SERVERS["aws_redshift"]
        cluster = _pick(data, "cluster_identifier", _AWS_SYNONYMS) or _pick(
            data, "workgroup_name", _AWS_SYNONYMS
        )
        database = _pick(data, "database", _AWS_SYNONYMS, "")
        payload = await proxy.call(
            f"{connection_laui}:aws_redshift",
            spec["command"],
            spec.get("args", []),
            env,
            "execute_query",
            {"cluster_identifier": cluster, "database_name": database, "sql": sql},
        )
        return _adapt_redshift(payload)

    if _is_athena(data):
        spec = AWS_MCP_SERVERS["aws_athena"]
        cache_key = f"{connection_laui}:aws_athena"
        cmd, cargs = spec["command"], spec.get("args", [])
        database = _pick(data, "database", _AWS_SYNONYMS, "default")
        workgroup = _pick(data, "workgroup", _AWS_SYNONYMS, "primary")
        output = _pick(data, "output_location", _AWS_SYNONYMS)

        started = await proxy.call(
            cache_key,
            cmd,
            cargs,
            env,
            "manage_aws_athena_query_executions",
            {
                "operation": "start-query-execution",
                "query_string": sql,
                "query_execution_context": {"Database": database},
                "result_configuration": {"OutputLocation": output},
                "work_group": workgroup,
            },
        )
        qid = _extract_athena_qid(started)
        if not qid:
            raise DataplaneError(502, f"Athena start-query-execution returned no id: {started}")

        for _ in range(60):
            await asyncio.sleep(2)
            status = await proxy.call(
                cache_key,
                cmd,
                cargs,
                env,
                "manage_aws_athena_query_executions",
                {"operation": "get-query-execution", "query_execution_id": qid},
            )
            state = _extract_athena_state(status)
            if state == "SUCCEEDED":
                break
            if state in ("FAILED", "CANCELLED"):
                raise DataplaneError(400, f"Athena query {state}: {status}")
        else:
            raise DataplaneError(504, "Athena query timed out after 120s.")

        results = await proxy.call(
            cache_key,
            cmd,
            cargs,
            env,
            "manage_aws_athena_query_executions",
            {"operation": "get-query-results", "query_execution_id": qid, "max_results": 1000},
        )
        result_set = _find_key(results, "ResultSet") or {}
        return _adapt_athena_result_set(result_set)

    raise DataplaneError(
        400, "connection.AWS SQL requires Athena (output_location) or Redshift fields."
    )


def _find_key(obj, key):
    """Depth-first search for the first value under `key` in a nested dict/list."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            found = _find_key(v, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_key(v, key)
            if found is not None:
                return found
    return None


def _extract_athena_qid(payload):
    return _find_key(payload, "QueryExecutionId") or _find_key(payload, "query_execution_id")


def _extract_athena_state(payload):
    state = _find_key(payload, "State")
    if isinstance(state, str):
        return state
    status = _find_key(payload, "Status")
    if isinstance(status, dict):
        return status.get("State")
    return None


async def execute_sql(
    proxy: McpProxyManager, connection_laui: str, item_type: str, data: dict, sql: str
) -> tuple[list[str], list[list]]:
    """Single entrypoint for read-only SQL used by both the /query route and the
    inspect_data tool. AWS Athena/Redshift delegate to the awslabs MCP servers;
    everything else runs in-process via the SQL drivers."""
    if item_type == "connection.AWS" and (_is_athena(data) or _is_redshift(data)):
        from src.core.dataplane.executors import _validate_sql

        _validate_sql(sql)
        columns, rows = await aws_sql_query(proxy, connection_laui, data, sql)
        if len(rows) > _ROW_LIMIT + 1:
            rows = rows[: _ROW_LIMIT + 1]
        return columns, rows
    return await asyncio.wait_for(asyncio.to_thread(run_query, item_type, data, sql), timeout=120.0)
