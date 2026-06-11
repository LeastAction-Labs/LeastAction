# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import importlib.util
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

from src.common.exceptions import InvalidArgumentError, UnprocessableEntityError
from src.common.utils import load_system_config


def get_stale_heartbeat_threshold_seconds() -> float:
    config = load_system_config()
    multiplier = config.get("stale_heartbeat_multiplier", 5)
    poll_interval = config.get("celery", {}).get("poll_interval_seconds", 2.5)
    return multiplier * poll_interval


def is_heartbeat_stale(latest_heartbeat, threshold_seconds: float) -> bool:
    if latest_heartbeat is None:
        return True
    if isinstance(latest_heartbeat, str):
        latest_heartbeat = datetime.fromisoformat(latest_heartbeat)
    if latest_heartbeat.tzinfo is None:
        latest_heartbeat = latest_heartbeat.replace(tzinfo=UTC)
    delta = (datetime.now(UTC) - latest_heartbeat).total_seconds()
    return delta > threshold_seconds


def create_module_from_codeblock(
    codeblock: dict[str, str],
    base_dir: Path,
    session_id: str | None = None,
) -> list[Path]:
    if not codeblock:
        raise InvalidArgumentError(
            message="Empty codeblock provided", detail={"codeblock": codeblock}
        )

    try:
        base_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise UnprocessableEntityError(
            message="Failed to create target directory",
            detail={"target_dir": str(base_dir), "error": str(e)},
        )

    created_files = []
    suffix = f"_{session_id}__{uuid.uuid4().hex[:4]}" if session_id else f"__{uuid.uuid4().hex[:4]}"

    try:
        for file_name, content in codeblock.items():
            base_name = Path(file_name).stem  # Strip any extension, enforce .py
            file_path = base_dir / f"{base_name}{suffix}.py"

            file_path.write_text(content, encoding="utf-8")
            created_files.append(file_path)

        return created_files

    except (InvalidArgumentError, UnprocessableEntityError):
        for f in created_files:
            f.unlink(missing_ok=True)
        raise

    except Exception as e:
        for f in created_files:
            f.unlink(missing_ok=True)

        raise UnprocessableEntityError(
            message="Failed to create files from codeblock",
            detail={"error": str(e), "error_type": type(e).__name__},
        )


def load_module(path: Path) -> ModuleType:
    try:
        module_name = f"leastAction_{uuid.uuid4().hex}"
        module_dir = str(path.parent)
        if module_dir not in sys.path:
            sys.path.insert(0, module_dir)
        spec = importlib.util.spec_from_file_location(module_name, path)

        if spec is None or spec.loader is None:
            raise UnprocessableEntityError(
                message="Could not load module specification",
                detail={"path": str(path), "module_name": module_name},
            )

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        return module

    except UnprocessableEntityError:
        raise
    except Exception as e:
        raise UnprocessableEntityError(
            message=f"Failed to load module from {path}: {str(e)}",
            detail={"path": str(path), "error": str(e), "error_type": type(e).__name__},
        )
