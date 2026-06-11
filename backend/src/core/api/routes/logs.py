# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import asyncio
import json
import traceback
from collections.abc import AsyncGenerator
from typing import Any

import duckdb
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.common.config import Config
from src.common.context_vars.user_context import get_user_laui
from src.common.logger.logger import log_error, log_info
from src.core.logs_details.service import LogsService, get_logs_service

logs_router = APIRouter()


class LogQueryRequest(BaseModel):
    sql: str
    category: str | None = None  # PERFORMANCE | CRON | TASK_HISTORY | CELERY | API | TASK
    date: str | None = None  # YYYY-MM-DD


# Each top-level folder uses a different partition layout:
#   category=PERFORMANCE  → yyyy=Y/mm=M/dd=D/*.log
#   category=CRON         → project=*/yyyy=Y/mm=M/dd=D/*.log
#   category=TASK_HISTORY → task_laui=*/yyyy=Y/mm=M/dd=D/*.log
#   verbose=NON_TASK      → yyyy=Y/mm=M/dd=D/session_id=*/category={CELERY|API}/*.log
#   verbose=TASK          → yyyy=Y/mm=M/dd=D/*.log
_CATEGORY_GLOB: dict[str, str] = {
    "PERFORMANCE": "category=PERFORMANCE/{date}/*.log",
    "CRON": "category=CRON/project=*/{date}/*.log",
    "TASK_HISTORY": "category=TASK_HISTORY/task_laui=*/{date}/*.log",
    "CELERY": "verbose=NON_TASK/{date}/session_id=*/category=CELERY/*.log",
    "API": "verbose=NON_TASK/{date}/session_id=*/category=API/*.log",
    "API_TRACEBACK": "verbose=NON_TASK/{date}/session_id=*/category=API_TRACEBACK/*.log",
    "TASK": "verbose=TASK/{date}/task_laui=*/session_id=*/*.log",
    "KETO": "verbose=OTHER/{date}/session_id=*/category=KETO/*.log",
}
_DATE_PLACEHOLDER = "{date}"


def _build_glob(logs_dir, category: str | None, date: str | None) -> str:
    base = str(logs_dir)
    # Use explicit wildcards per level so path structure stays valid for all categories.
    # verbose=NON_TASK has date BEFORE session_id, so ** would break the ordering.
    date_part = f"yyyy={date[:4]}/mm={date[5:7]}/dd={date[8:10]}" if date else "yyyy=*/mm=*/dd=*"

    if category:
        template = _CATEGORY_GLOB.get(category.upper())
        if template:
            return f"{base}/{template.replace(_DATE_PLACEHOLDER, date_part)}"
        return f"{base}/category={category}/{date_part}/*.log"

    if date:
        return f"{base}/**/{date_part}/*.log"
    return f"{base}/**/*.log"


def _run_duckdb_query(sql: str, category: str | None, date: str | None) -> dict:
    if not category:
        return {
            "error": "category is required. Use one of: PERFORMANCE, CRON, TASK_HISTORY, CELERY, API, TASK"
        }
    sql_stripped = sql.strip()
    upper = sql_stripped.upper()
    if ";" in sql_stripped or not (upper.startswith("SELECT") or upper.startswith("WITH")):
        return {"error": "Only SELECT queries are allowed"}
    try:
        logs_dir = Config().logs_dir
        glob = _build_glob(logs_dir, category, date)
        con = duckdb.connect(":memory:")
        con.execute(
            f"CREATE VIEW logs AS SELECT * FROM read_json_auto("
            f"'{glob}', union_by_name=True, ignore_errors=True)"
        )
        result = con.execute(sql_stripped).fetchall()
        columns = [desc[0] for desc in con.description]
        rows = [list(row) for row in result]
        return {"columns": columns, "rows": rows, "row_count": len(rows)}
    except Exception as exc:
        return {"error": str(exc)}


@logs_router.post("/query")
async def query_logs(request: LogQueryRequest) -> dict:
    log_info(
        "api", "logs_router", "query_logs", f"user={get_user_laui()} payload={request.model_dump()}"
    )
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _run_duckdb_query, request.sql, request.category, request.date
    )


def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _streaming_response(generator: AsyncGenerator[str, None]) -> StreamingResponse:
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream_list_folder(service: LogsService, folder_path: str):
    yield _sse("status", {"state": "processing"})
    try:
        result = await service.list_folder_items(folder_path)
        yield _sse("data", result)
        yield _sse("done", {"state": "complete"})
    except Exception as exc:
        log_error(
            "api_traceback",
            "logs_router",
            "_stream_list_folder",
            f"folder_path={folder_path} error: {str(exc)}\n{traceback.format_exc()}",
        )
        yield _sse("error", {"message": str(exc)})


async def _stream_file_details(service: LogsService, file_path: str):
    yield _sse("status", {"state": "processing"})
    try:
        meta = await service.get_file_metadata(file_path)
        yield _sse("metadata", meta)

        count = 0
        async for chunk in service.iter_file_chunks(file_path):
            yield _sse("chunk", chunk)
            count += 1

        yield _sse("done", {"state": "complete", "total_chunks": count})
    except Exception as exc:
        log_error(
            "api_traceback",
            "logs_router",
            "_stream_file_details",
            f"file_path={file_path} error: {str(exc)}\n{traceback.format_exc()}",
        )
        yield _sse("error", {"message": str(exc)})


async def _stream_file_details_paged(service: LogsService, file_path: str, skip: int, limit: int):
    yield _sse("status", {"state": "processing"})
    try:
        meta = await service.get_file_metadata(file_path)
        yield _sse("metadata", meta)

        count = 0
        async for chunk in service.iter_file_lines_paged(file_path, skip, limit):
            yield _sse("chunk", chunk)
            count += 1

        yield _sse("done", {"state": "complete", "total_chunks": count})
    except Exception as exc:
        log_error(
            "api_traceback",
            "logs_router",
            "_stream_file_details_paged",
            f"file_path={file_path} error: {str(exc)}\n{traceback.format_exc()}",
        )
        yield _sse("error", {"message": str(exc)})


async def _stream_session_logs(service: LogsService, session_id: str):
    yield _sse("status", {"state": "processing"})
    try:
        count = 0
        async for entry in service.iter_session_logs(session_id):
            yield _sse("log", entry)
            count += 1

        yield _sse("done", {"state": "complete", "total_count": count})
    except Exception as exc:
        log_error(
            "api_traceback",
            "logs_router",
            "_stream_session_logs",
            f"session_id={session_id} error: {str(exc)}\n{traceback.format_exc()}",
        )
        yield _sse("error", {"message": str(exc)})


@logs_router.get("/listItems/{folder_path:path}")
async def list_folder_items(
    folder_path: str,
    logs_service: LogsService = Depends(get_logs_service),
) -> StreamingResponse:
    log_info(
        "api",
        "logs_router",
        "list_folder_items",
        f"user={get_user_laui()} payload={{folder_path={folder_path}}}",
    )
    return _streaming_response(_stream_list_folder(logs_service, folder_path))


@logs_router.get("/file/{file_path:path}")
async def get_file_details(
    file_path: str,
    reverse: bool = Query(default=False),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=5000),
    logs_service: LogsService = Depends(get_logs_service),
) -> StreamingResponse:
    log_info(
        "api",
        "logs_router",
        "get_file_details",
        f"user={get_user_laui()} payload={{file_path={file_path}, reverse={reverse}, skip={skip}, limit={limit}}}",
    )
    if reverse:
        return _streaming_response(_stream_file_details_paged(logs_service, file_path, skip, limit))
    return _streaming_response(_stream_file_details(logs_service, file_path))


@logs_router.get("/session/{session_id}")
async def get_session_logs(
    session_id: str,
    logs_service: LogsService = Depends(get_logs_service),
) -> StreamingResponse:
    log_info(
        "api",
        "logs_router",
        "get_session_logs",
        f"user={get_user_laui()} payload={{session_id={session_id}}}",
    )
    return _streaming_response(_stream_session_logs(logs_service, session_id))


@logs_router.get("/session/{session_id}/content")
async def get_session_log_content(
    session_id: str,
    level: str | None = Query(default=None),
    category: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=500),
    logs_service: LogsService = Depends(get_logs_service),
) -> dict:
    log_info(
        "api",
        "logs_router",
        "get_session_log_content",
        f"user={get_user_laui()} payload={{session_id={session_id}, level={level}, category={category}, page={page}, per_page={per_page}}}",
    )
    return await logs_service.get_session_log_content(
        session_id=session_id,
        level=level,
        category=category,
        page=page,
        per_page=per_page,
    )
