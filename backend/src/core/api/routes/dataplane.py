# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
# Experimental Preview — multi-database read-only inspect endpoint.
# Thin wrapper over src.core.dataplane.executors; the same logic backs the
# inspect_data MCP tool in-process. Mounted under /query for frontend parity.
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from src.core.catalog.orchestrator import ItemOrchestrator, get_item_orchestrator
from src.core.dataplane.executors import DataplaneError, _ROW_LIMIT, resolve_connection
from src.core.dataplane.mcp_proxy import McpProxyManager, execute_sql

query_router = APIRouter()


class QueryRequest(BaseModel):
    connection_laui: str
    sql: str


class QueryResponse(BaseModel):
    columns: list[str]
    rows: list[list]
    row_count: int
    truncated: bool = False


@query_router.post("/execute", response_model=QueryResponse)
async def execute_query(
    req: QueryRequest,
    request: Request,
    orchestrator: ItemOrchestrator = Depends(get_item_orchestrator),
):
    # Shared proxy so the Data Inspector reuses the same awslabs servers as the
    # AWS MCP tools (Athena/Redshift SELECTs run server-side — no AI needed).
    proxy: McpProxyManager = getattr(request.app.state, "mcp_proxy", None) or McpProxyManager()
    try:
        item_type, data = await resolve_connection(orchestrator, req.connection_laui)
        columns, rows = await execute_sql(proxy, req.connection_laui, item_type, data, req.sql)
    except DataplaneError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Query timed out after 2 minutes.")

    truncated = len(rows) > _ROW_LIMIT
    if truncated:
        rows = rows[:_ROW_LIMIT]

    return QueryResponse(columns=columns, rows=rows, row_count=len(rows), truncated=truncated)
