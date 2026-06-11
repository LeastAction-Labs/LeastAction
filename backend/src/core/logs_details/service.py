# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os

from src.common.config import Config
from src.common.exceptions import InvalidArgumentError, NotFoundError, UnsupportedMediaTypeError

CHUNK_SIZE = 64 * 1024  # 64 KB


class LogsService:
    def __init__(self) -> None:
        self._logs_dir = self._get_logs_dir()

    def _get_logs_dir(self) -> Path:
        return Config().logs_dir

    def _build_item_info(self, base_dir: Path, item: Path, stat) -> dict[str, Any]:
        return {
            "name": item.name,
            "type": "directory" if item.is_dir() else "file",
            "size": stat.st_size if item.is_file() else None,
            "modified": stat.st_mtime,
            "path": str(item.relative_to(base_dir)),
        }

    async def list_folder_items(self, folder_path: str) -> dict[str, Any]:
        logs_dir = self._logs_dir
        target = logs_dir if not folder_path or folder_path == "." else logs_dir / folder_path

        if not await aiofiles.os.path.exists(target):
            raise NotFoundError(message="Folder not found")
        if not await aiofiles.os.path.isdir(target):
            raise InvalidArgumentError(message="Path is not a directory")

        items: list[dict[str, Any]] = []
        for item in target.iterdir():
            stat = await aiofiles.os.stat(item)
            items.append(self._build_item_info(logs_dir, item, stat))

        if not folder_path or folder_path == ".":
            items.sort(key=lambda x: x["name"], reverse=True)

        return {"directory": str(target), "items": items, "total_count": len(items)}

    async def get_file_metadata(self, file_path: str) -> dict[str, Any]:
        logs_dir = self._logs_dir
        target = logs_dir / file_path

        if not await aiofiles.os.path.exists(target):
            raise NotFoundError(message="File not found")
        if not await aiofiles.os.path.isfile(target):
            raise InvalidArgumentError(message="Path is not a file")

        s = await aiofiles.os.stat(target)
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

    async def iter_file_lines_paged(
        self,
        file_path: str,
        skip: int = 0,
        limit: int = 400,
    ) -> AsyncIterator[dict[str, Any]]:
        """Return a tail page of lines in chronological order, paging backward from end of file.

        skip: number of lines from the end already loaded (0 = start from last line)
        limit: page size
        Returns lines in normal chronological order so newest appears at bottom.
        """
        logs_dir = self._logs_dir
        target = logs_dir / file_path
        ext = target.suffix.lower()

        if not await aiofiles.os.path.exists(target):
            raise NotFoundError(message="File not found")
        if not await aiofiles.os.path.isfile(target):
            raise InvalidArgumentError(message="Path is not a file")
        if ext not in {".log", ".txt"}:
            raise UnsupportedMediaTypeError(message=f"Streaming not supported for '{ext}'")

        async with aiofiles.open(target, encoding="utf-8", errors="replace") as f:
            content = await f.read()

        all_lines = [l for l in content.splitlines() if l.strip()]
        total = len(all_lines)
        # Page backward from the end: window is [start, end) in chronological order
        end = max(0, total - skip)
        start = max(0, end - limit)
        page = all_lines[start:end]
        has_more = start > 0

        if page:
            yield {
                "content": "\n".join(page),
                "content_type": "text/plain",
                "chunk_index": 0,
                "has_more": has_more,
                "total_lines": total,
            }

    async def iter_file_chunks(self, file_path: str) -> AsyncIterator[dict[str, Any]]:
        logs_dir = self._logs_dir
        target = logs_dir / file_path
        ext = target.suffix.lower()

        if ext not in {".log", ".txt", ".json"}:
            raise UnsupportedMediaTypeError(message=f"Streaming not supported for '{ext}'")

        if ext == ".json":
            async with aiofiles.open(target, encoding="utf-8") as f:
                raw = await f.read()
            try:
                parsed = json.loads(raw)
                yield {
                    "content": json.dumps(parsed, indent=2),
                    "content_type": "application/json",
                    "json_valid": True,
                }
            except json.JSONDecodeError as je:
                yield {
                    "content": raw,
                    "content_type": "application/json",
                    "json_valid": False,
                    "content_error": str(je),
                }
            return

        async with aiofiles.open(target, encoding="utf-8", errors="replace") as f:
            index = 0
            while chunk := await f.read(CHUNK_SIZE):
                yield {"content": chunk, "content_type": "text/plain", "chunk_index": index}
                index += 1

    async def iter_session_logs(self, session_id: str) -> AsyncIterator[dict[str, Any]]:
        logs_dir = self._logs_dir
        if not await aiofiles.os.path.exists(logs_dir):
            return

        for log_file in logs_dir.glob(f"**/session_id={session_id}/**/*.log"):
            if not log_file.is_file():
                continue
            try:
                s = await aiofiles.os.stat(log_file)
                yield {
                    "name": log_file.name,
                    "path": str(log_file.relative_to(logs_dir)),
                    "full_path": str(log_file),
                    "size": s.st_size,
                    "modified": s.st_mtime,
                    "created": s.st_ctime,
                }
            except Exception:
                continue

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

    async def get_session_log_content(
        self,
        session_id: str,
        level: str | None = None,
        category: str | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> dict[str, Any]:
        """Read and parse all log files for a session, returning structured entries."""
        logs_dir = self._logs_dir
        if not await aiofiles.os.path.exists(logs_dir):
            return {
                "session_id": session_id,
                "entries": [],
                "total_count": 0,
                "page": page,
                "per_page": per_page,
                "files_read": 0,
            }

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
                    async with aiofiles.open(log_file, encoding="utf-8", errors="replace") as f:
                        content = await f.read()
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


def get_logs_service() -> LogsService:
    return LogsService()
