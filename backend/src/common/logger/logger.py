# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import json
import logging
import sys
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from src.common.config import Config
from src.common.context_vars.session_context import (
    get_action_context,
    get_logger_context,
    get_session_id,
)


class LogLevel(Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


# Categories that write into the task-history directory partition
_TASK_CATEGORIES = frozenset(
    {
        "TASK",
        "TASK_HISTORY",
        "PRE_ACTIONS",
        "POST_ACTIONS",
        "RUNNING_ACTIONS",
        "ACTION",
        "CREATE_ACTIONS",
    }
)

# ACTION category + one of these action_types triggers dual-write
# (TASK_HISTORY snapshot + action rolling log)
_DUAL_WRITE_ACTION_TYPES = frozenset({"PRE_ACTIONS"})


class LoggerManager:
    def __init__(self, config: Config):
        self.base_dir = Path(config.logs_dir)
        self._loggers: dict[str, logging.Logger] = {}
        self._overwrite_initialized: set[str] = set()
        self._created_dirs: set[str] = set()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _make_dir(self, log_dir: Path) -> None:
        """Safely creates directories, ignoring multi-process race conditions."""
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Fallback if another process or thread created it at the exact same millisecond
            if not log_dir.is_dir():
                raise

    def _get_logical_or_fixed_run_date(self, logical_date: datetime | None) -> datetime:
        return logical_date if isinstance(logical_date, datetime) else datetime.now(UTC)

    def _resolve_category(self, category: str, action_type: str | None) -> str:
        cat = category.upper()
        if cat == "ACTION":
            return action_type.upper() if action_type else "ACTION"
        return cat

    def _build_log_path(
        self,
        category: str,
        operation: str,
        step: str,
        session_id: str,
        task_laui: str | None = None,
        task_name: str | None = None,
        logical_date: datetime | None = None,
        project_laui: str | None = None,
        action_name: str | None = None,
        action_type: str | None = None,
    ) -> Path:
        date = self._get_logical_or_fixed_run_date(logical_date)
        timestamp = date.strftime("%Y%m%d_%H%M%S_%f")[:-3]

        effective_task_laui = task_laui or "no-task"
        effective_task_name = task_name or "no-task-name"
        effective_action_name = action_name or "no-action"
        effective_project_laui = project_laui or "no-project"

        cat = self._resolve_category(category, action_type)

        if cat == "TASK_HISTORY":
            log_dir = (
                self.base_dir
                / f"category={cat}"
                / f"task_laui={effective_task_laui}"
                / f"yyyy={date.year}"
                / f"mm={date.month:02d}"
                / f"dd={date.day:02d}"
            )
            self._make_dir(log_dir)
            if operation.lower() == "task":
                filename = f"{timestamp}__{session_id}__{effective_task_name}.log"
            else:
                type_prefix = action_type.lower() if action_type else "action"
                filename = f"latest_{type_prefix}_{effective_task_name}_{effective_action_name}.log"
            return log_dir / filename

        elif cat in ("API", "CELERY", "API_TRACEBACK"):
            log_dir = (
                self.base_dir
                / "verbose=NON_TASK"
                / f"yyyy={date.year}"
                / f"mm={date.month:02d}"
                / f"dd={date.day:02d}"
                / f"session_id={session_id}"
                / f"category={cat}"
            )
            self._make_dir(log_dir)
            return log_dir / f"{operation}.log"

        elif cat in _TASK_CATEGORIES:
            log_dir = (
                self.base_dir
                / "verbose=TASK"
                / f"yyyy={date.year}"
                / f"mm={date.month:02d}"
                / f"dd={date.day:02d}"
                / f"task_laui={effective_task_laui}"
                / f"session_id={session_id}"
                / f"category={cat}"
            )
            self._make_dir(log_dir)
            if cat == "TASK":
                return log_dir / f"{effective_task_name}.log"
            else:
                return log_dir / f"{effective_action_name}.log"

        elif cat == "CRON":
            log_dir = (
                self.base_dir
                / f"category={cat}"
                / f"project={effective_project_laui}"
                / f"yyyy={date.year}"
                / f"mm={date.month:02d}"
                / f"dd={date.day:02d}"
            )
            self._make_dir(log_dir)
            return log_dir / "cron.log"

        elif cat == "PERFORMANCE":
            log_dir = (
                self.base_dir
                / f"category={cat}"
                / f"yyyy={date.year}"
                / f"mm={date.month:02d}"
                / f"dd={date.day:02d}"
            )
            self._make_dir(log_dir)
            return log_dir / f"{operation}.log"

        else:
            log_dir = (
                self.base_dir
                / "verbose=OTHER"
                / f"yyyy={date.year}"
                / f"mm={date.month:02d}"
                / f"dd={date.day:02d}"
                / f"session_id={session_id}"
                / f"category={cat}"
            )
            self._make_dir(log_dir)
            return log_dir / f"{operation}.log"

    def _get_or_create_logger(
        self,
        category: str,
        operation: str,
        level: LogLevel,
        session_id: str,
        task_laui: str | None = None,
        action_type: str | None = None,
    ) -> logging.Logger:
        effective_cat = self._resolve_category(category, action_type)
        task_part = f"_{task_laui}" if task_laui else ""
        logger_name = f"{effective_cat}_{operation}{task_part}"

        if logger_name in self._loggers:
            return self._loggers[logger_name]

        logger = logging.getLogger(logger_name)
        logger.setLevel(level.value)
        logger.handlers.clear()
        logger.propagate = False
        self._loggers[logger_name] = logger
        return logger

    def _resolve_write_mode(self, log_file: Path, session_id: str) -> str:
        """
        Return "w" for the very first write of a (file, session) pair — clears any
        stale content from a previous run — and "a" for all subsequent writes within
        the same run so entries accumulate correctly.
        """
        key = str(log_file)
        if key not in self._overwrite_initialized:
            self._overwrite_initialized.add(key)
            return "w"
        return "a"

    def _write_to_file(
        self,
        log_file: Path,
        file_mode: str,
        step: str,
        level: LogLevel,
        message: str,
        logger: logging.Logger,
        session_id: str,
        category: str | None = None,
        operation: str | None = None,
        task_laui: str | None = None,
        task_name: str | None = None,
        logical_date: datetime | None = None,
        project_laui: str | None = None,
        action_name: str | None = None,
    ) -> None:
        lvl_name = level.name.lower()
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": lvl_name,
            "step": step,
            "session_id": session_id,
            "message": message,
        }

        if category is not None:
            log_entry["category"] = category
        if operation is not None:
            log_entry["operation"] = operation
        if task_laui is not None:
            log_entry["task_laui"] = task_laui
        if task_name is not None:
            log_entry["task_name"] = task_name
        if logical_date is not None:
            log_entry["logical_date"] = logical_date.isoformat()
        if project_laui is not None:
            log_entry["project_laui"] = project_laui
        if action_name is not None:
            log_entry["action_name"] = action_name

        json_message = json.dumps(log_entry)

        handler = logging.FileHandler(log_file, mode=file_mode, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        try:
            getattr(logger, lvl_name)(json_message)
            handler.flush()
        finally:
            logger.removeHandler(handler)
            handler.close()

    def log(
        self,
        category: str,
        operation: str,
        step: str,
        message: str,
        level: LogLevel = LogLevel.INFO,
    ) -> None:
        try:
            print(
                f"[LoggerManager] log(): category={category}, operation={operation}, step={step}, message={message}"
            )
            # self._log(category, operation, step, message, level)
        except Exception as exc:
            print(f"[LoggerManager] Unhandled error during log(): {exc}", file=sys.stderr)

    def _log(
        self,
        category: str,
        operation: str,
        step: str,
        message: str,
        level: LogLevel,
    ) -> None:
        session_id = get_session_id()
        logger_context = get_logger_context()
        task_laui = logger_context.get("task_laui")
        task_name = logger_context.get("task_name")
        logical_date = logger_context.get("logical_date")
        project_laui = logger_context.get("project_laui")

        action_context = get_action_context()
        action_name = action_context.get("name")
        action_type = action_context.get("action_type")
        action_type_upper = action_type.upper() if action_type else None

        path_kwargs = {
            "step": step,
            "session_id": session_id,
            "task_laui": task_laui,
            "task_name": task_name,
            "logical_date": logical_date,
            "project_laui": project_laui,
            "action_name": action_name,
            "action_type": action_type,
        }

        logger = self._get_or_create_logger(
            category=category,
            operation=operation,
            level=level,
            session_id=session_id,
            task_laui=task_laui,
            action_type=action_type,
        )

        if category.upper() == "ACTION" and action_type_upper in _DUAL_WRITE_ACTION_TYPES:
            # --- Dual-write path ---
            # 1. TASK_HISTORY snapshot: cleared on first write of each run, then appended.
            task_history_path = self._build_log_path(
                category="TASK_HISTORY",
                operation="action",
                **path_kwargs,
            )
            th_mode = self._resolve_write_mode(task_history_path, session_id)
            self._write_to_file(
                task_history_path,
                th_mode,
                step,
                level,
                message,
                logger,
                session_id,
                "TASK_HISTORY",
                "action",
                task_laui,
                task_name,
                logical_date,
                project_laui,
                action_name,
            )
            action_cat_path = self._build_log_path(
                category=action_type,
                operation=operation,
                **path_kwargs,
            )
            self._write_to_file(
                action_cat_path,
                "a",
                step,
                level,
                message,
                logger,
                session_id,
                action_type,
                operation,
                task_laui,
                task_name,
                logical_date,
                project_laui,
                action_name,
            )

        else:
            log_file = self._build_log_path(
                category=category,
                operation=operation,
                **path_kwargs,
            )
            effective_cat = self._resolve_category(category, action_type)
            # TASK_HISTORY action entries are cleared once per run; everything else appends.
            if effective_cat == "TASK_HISTORY" and operation.lower() != "task":
                file_mode = self._resolve_write_mode(log_file, session_id)
            else:
                file_mode = "a"
            self._write_to_file(
                log_file,
                file_mode,
                step,
                level,
                message,
                logger,
                session_id,
                category,
                operation,
                task_laui,
                task_name,
                logical_date,
                project_laui,
                action_name,
            )

    def clear_loggers(self) -> None:
        for name, logger in self._loggers.items():
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
            logger.handlers.clear()
            logging.Logger.manager.loggerDict.pop(name, None)

        self._loggers.clear()
        self._overwrite_initialized.clear()
        self._created_dirs.clear()


_global_logger_manager: LoggerManager | None = None


def initialize_logger(config: Config) -> None:
    global _global_logger_manager
    _global_logger_manager = LoggerManager(config)


def get_logger_manager() -> LoggerManager:
    if _global_logger_manager is None:
        raise RuntimeError("LoggerManager not initialized. Call initialize_logger() first.")
    return _global_logger_manager


def log_info(category: str, operation: str, step: str, message: str) -> None:
    get_logger_manager().log(category, operation, step, message, level=LogLevel.INFO)


def log_warning(category: str, operation: str, step: str, message: str) -> None:
    get_logger_manager().log(category, operation, step, message, level=LogLevel.WARNING)


def log_error(category: str, operation: str, step: str, message: str) -> None:
    get_logger_manager().log(category, operation, step, message, level=LogLevel.ERROR)


def log_critical(category: str, operation: str, step: str, message: str) -> None:
    get_logger_manager().log(category, operation, step, message, level=LogLevel.CRITICAL)


def log_debug(category: str, operation: str, step: str, message: str) -> None:
    get_logger_manager().log(category, operation, step, message, level=LogLevel.DEBUG)
