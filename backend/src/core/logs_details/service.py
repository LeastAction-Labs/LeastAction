# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import asyncio
import json
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import aiofiles

from src.common.config import Config
from src.common.exceptions import InvalidArgumentError, NotFoundError, UnsupportedMediaTypeError

CHUNK_SIZE = 64 * 1024  # 64 KB
TAIL_BLOCK_SIZE = 64 * 1024  # read window when paging a file tail from the end

# Bounds how many heavy log operations (directory walks, full-file reads, JSON
# parsing) run concurrently *per worker process*. uvicorn runs one event loop per
# worker; without a cap, a handful of heavy log requests can saturate the shared
# thread pool and starve every other endpoint on that worker. See issue #11.
_MAX_CONCURRENT_LOG_OPS = 3
LOG_WORK_SEMAPHORE = asyncio.Semaphore(_MAX_CONCURRENT_LOG_OPS)

# Wall-clock ceiling for a single heavy log operation. On timeout the semaphore
# slot is released so a wedged disk/mount or pathological glob can't permanently
# consume capacity and lock out every log endpoint (issue #11, "thread locks").
# Caveat: the worker thread keeps running — Python threads aren't cancellable —
# so keep this generous; it should only fire on genuine pathology, not slow I/O.
_LOG_OP_TIMEOUT = 30.0  # seconds
# DuckDB queries over wide date ranges are legitimately slower; give them headroom.
LOG_QUERY_TIMEOUT = 120.0  # seconds


async def run_log_op(fn, *args, timeout: float = _LOG_OP_TIMEOUT):
    """Run a blocking log operation in a thread, gated by the concurrency semaphore
    and bounded by a wall-clock timeout. Raises TimeoutError with a clear message
    (plain asyncio.TimeoutError stringifies to ''), which the SSE handlers surface
    as an error event."""
    async with LOG_WORK_SEMAPHORE:
        try:
            return await asyncio.wait_for(asyncio.to_thread(fn, *args), timeout)
        except TimeoutError as exc:
            raise TimeoutError(f"Log operation exceeded {int(timeout)}s and was aborted") from exc


def _read_tail_lines(path: Path, needed: int) -> tuple[list[str], bool]:
    """Read non-empty lines from the END of a file, growing backward until at least
    ``needed`` complete lines are available or the start of file is reached.

    Returns ``(lines_in_chronological_order, reached_start)``. Avoids loading the
    whole file just to show a tail page.
    """
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        pos = f.tell()
        buf = b""
        # +1 newline of slack so a partial first line can be dropped and still leave
        # `needed` complete lines.
        while pos > 0 and buf.count(b"\n") <= needed:
            read_size = min(TAIL_BLOCK_SIZE, pos)
            pos -= read_size
            f.seek(pos)
            buf = f.read(read_size) + buf
        reached_start = pos == 0

    lines = buf.decode("utf-8", errors="replace").split("\n")
    if not reached_start and lines:
        # The first line was cut mid-line by the block boundary; drop it.
        lines = lines[1:]
    return [ln for ln in lines if ln.strip()], reached_start


class LogsService:
    def __init__(self) -> None:
        self._logs_dir = self._get_logs_dir()

    def _get_logs_dir(self) -> Path:
        return Config().logs_dir

    # ── folder listing ────────────────────────────────────────────────────────

    def _list_folder_items_sync(self, folder_path: str) -> dict[str, Any]:
        logs_dir = self._logs_dir
        target = logs_dir if not folder_path or folder_path == "." else logs_dir / folder_path

        if not target.exists():
            raise NotFoundError(message="Folder not found")
        if not target.is_dir():
            raise InvalidArgumentError(message="Path is not a directory")

        items: list[dict[str, Any]] = []
        with os.scandir(target) as it:
            for entry in it:
                stat = entry.stat()
                is_file = entry.is_file()
                items.append(
                    {
                        "name": entry.name,
                        "type": "directory" if entry.is_dir() else "file",
                        "size": stat.st_size if is_file else None,
                        "modified": stat.st_mtime,
                        "path": str(Path(entry.path).relative_to(logs_dir)),
                    }
                )

        if not folder_path or folder_path == ".":
            items.sort(key=lambda x: x["name"], reverse=True)

        return {"directory": str(target), "items": items, "total_count": len(items)}

    async def list_folder_items(self, folder_path: str) -> dict[str, Any]:
        return await run_log_op(self._list_folder_items_sync, folder_path)

    # ── file metadata (light) ─────────────────────────────────────────────────

    def _get_file_metadata_sync(self, file_path: str) -> dict[str, Any]:
        logs_dir = self._logs_dir
        target = logs_dir / file_path

        if not target.exists():
            raise NotFoundError(message="File not found")
        if not target.is_file():
            raise InvalidArgumentError(message="Path is not a file")

        s = target.stat()
        return {
            "name": target.name,
            "path": str(target.relative_to(logs_dir)),
            "full_path": str(target),
            "size": s.st_size,
            "modified": s.st_mtime,
            "created": s.st_ctime,
            "extension": target.suffix,
            "is_readable": s.st_size > 0,
        }

    async def get_file_metadata(self, file_path: str) -> dict[str, Any]:
        # A single stat — cheap enough to skip the concurrency gate.
        return await asyncio.to_thread(self._get_file_metadata_sync, file_path)

    # ── paged tail reader ─────────────────────────────────────────────────────

    def _read_tail_page_sync(self, file_path: str, skip: int, limit: int) -> dict[str, Any] | None:
        logs_dir = self._logs_dir
        target = logs_dir / file_path
        ext = target.suffix.lower()

        if not target.exists():
            raise NotFoundError(message="File not found")
        if not target.is_file():
            raise InvalidArgumentError(message="Path is not a file")
        if ext not in {".log", ".txt"}:
            raise UnsupportedMediaTypeError(message=f"Streaming not supported for '{ext}'")

        tail, reached_start = _read_tail_lines(target, skip + limit + 1)
        n = len(tail)
        # Window [start, end) within `tail`, in chronological order. skip counts lines
        # already loaded from the end; limit is the page size.
        end = max(0, n - skip)
        start = max(0, end - limit)
        page = tail[start:end]
        has_more = (start > 0) if reached_start else end > 0

        if not page:
            return None
        return {
            "content": "\n".join(page),
            "content_type": "text/plain",
            "chunk_index": 0,
            "has_more": has_more,
            "total_lines": n if reached_start else None,
        }

    async def iter_file_lines_paged(
        self,
        file_path: str,
        skip: int = 0,
        limit: int = 400,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield a tail page of lines in chronological order, paging backward from the
        end of the file without reading the whole file into memory.

        skip: number of lines from the end already loaded (0 = start from last line)
        limit: page size
        """
        page = await run_log_op(self._read_tail_page_sync, file_path, skip, limit)
        if page is not None:
            yield page

    # ── whole-file chunk reader ───────────────────────────────────────────────

    def _read_json_sync(self, target: Path) -> dict[str, Any]:
        with open(target, encoding="utf-8") as f:
            raw = f.read()
        try:
            parsed = json.loads(raw)
            return {
                "content": json.dumps(parsed, indent=2),
                "content_type": "application/json",
                "json_valid": True,
            }
        except json.JSONDecodeError as je:
            return {
                "content": raw,
                "content_type": "application/json",
                "json_valid": False,
                "content_error": str(je),
            }

    async def iter_file_chunks(self, file_path: str) -> AsyncIterator[dict[str, Any]]:
        logs_dir = self._logs_dir
        target = logs_dir / file_path
        ext = target.suffix.lower()

        if ext not in {".log", ".txt", ".json"}:
            raise UnsupportedMediaTypeError(message=f"Streaming not supported for '{ext}'")

        # Held across the whole stream to throttle concurrent big-file reads, so
        # run_log_op (which acquires the same semaphore) can't be used here. Each
        # blocking step is bounded with wait_for so a stalled read can't pin the slot.
        async with LOG_WORK_SEMAPHORE:
            if ext == ".json":
                # Parsing/re-serialising is CPU-bound — keep it off the event loop.
                yield await asyncio.wait_for(
                    asyncio.to_thread(self._read_json_sync, target), _LOG_OP_TIMEOUT
                )
                return

            async with aiofiles.open(target, encoding="utf-8", errors="replace") as f:
                index = 0
                while chunk := await asyncio.wait_for(f.read(CHUNK_SIZE), _LOG_OP_TIMEOUT):
                    yield {"content": chunk, "content_type": "text/plain", "chunk_index": index}
                    index += 1

    # ── session logs ──────────────────────────────────────────────────────────

    def _collect_session_logs_sync(self, session_id: str) -> list[dict[str, Any]]:
        logs_dir = self._logs_dir
        if not logs_dir.exists():
            return []

        out: list[dict[str, Any]] = []
        for log_file in logs_dir.glob(f"**/session_id={session_id}/**/*.log"):
            if not log_file.is_file():
                continue
            try:
                s = log_file.stat()
                out.append(
                    {
                        "name": log_file.name,
                        "path": str(log_file.relative_to(logs_dir)),
                        "full_path": str(log_file),
                        "size": s.st_size,
                        "modified": s.st_mtime,
                        "created": s.st_ctime,
                    }
                )
            except Exception:
                continue
        return out

    async def iter_session_logs(self, session_id: str) -> AsyncIterator[dict[str, Any]]:
        entries = await run_log_op(self._collect_session_logs_sync, session_id)
        for entry in entries:
            yield entry

    # ── legacy non-streaming (kept for compatibility) ─────────────────────────

    async def get_file_details(self, file_path: str) -> dict[str, Any]:
        meta = await self.get_file_metadata(file_path)
        chunks = []
        async for chunk in self.iter_file_chunks(file_path):
            chunks.append(chunk)
        if chunks:
            meta["content"] = "".join(c["content"] for c in chunks)
            meta["content_type"] = chunks[0]["content_type"]
            if chunks[0].get("json_valid") is not None:
                meta["json_valid"] = chunks[0]["json_valid"]
        return meta

    async def get_logs_by_session_id(self, session_id: str) -> dict[str, Any]:
        logs = [entry async for entry in self.iter_session_logs(session_id)]
        logs.sort(key=lambda x: x["modified"], reverse=True)
        return {"session_id": session_id, "logs": logs, "total_count": len(logs)}

    def _get_session_log_content_sync(
        self,
        session_id: str,
        level: str | None,
        category: str | None,
        page: int,
        per_page: int,
    ) -> dict[str, Any]:
        logs_dir = self._logs_dir
        empty = {
            "session_id": session_id,
            "entries": [],
            "total_count": 0,
            "page": page,
            "per_page": per_page,
            "files_read": 0,
        }
        if not logs_dir.exists():
            return empty

        all_entries: list[dict[str, Any]] = []
        files_read = 0

        patterns = [
            f"**/session_id={session_id}/**/*.log",
            f"**/*__{session_id}__*.log",
        ]

        seen_files: set = set()
        for pattern in patterns:
            for log_file in logs_dir.glob(pattern):
                if not log_file.is_file() or str(log_file) in seen_files:
                    continue
                seen_files.add(str(log_file))
                try:
                    with open(log_file, encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    files_read += 1
                    for line in content.splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            entry["_source_file"] = str(log_file.relative_to(logs_dir))
                            if level and entry.get("level", "").lower() != level.lower():
                                continue
                            if category and entry.get("category", "").lower() != category.lower():
                                continue
                            all_entries.append(entry)
                        except json.JSONDecodeError:
                            all_entries.append(
                                {
                                    "message": line,
                                    "level": "raw",
                                    "_source_file": str(log_file.relative_to(logs_dir)),
                                }
                            )
                except Exception:
                    continue

        all_entries.sort(key=lambda x: x.get("timestamp", ""))
        total = len(all_entries)
        start = (page - 1) * per_page
        end = start + per_page
        entries = all_entries[start:end]

        return {
            "session_id": session_id,
            "entries": entries,
            "total_count": total,
            "returned_count": len(entries),
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if per_page else 1,
            "files_read": files_read,
        }

    async def get_session_log_content(
        self,
        session_id: str,
        level: str | None = None,
        category: str | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> dict[str, Any]:
        """Read and parse all log files for a session, returning structured entries."""
        return await run_log_op(
            self._get_session_log_content_sync, session_id, level, category, page, per_page
        )


def get_logs_service() -> LogsService:
    return LogsService()
