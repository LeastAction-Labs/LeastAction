# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from src.common.config import Config
from src.common.logger.logger import (
    LoggerManager,
    LogLevel,
    get_logger_manager,
    initialize_logger,
    log_error,
)


@pytest.fixture
def real_config():
    return Config()


@pytest.fixture
def logger_manager(real_config, tmp_path):
    with patch.object(Config, "logs_dir", new=property(lambda self: tmp_path)):
        mgr = LoggerManager(real_config)
    yield mgr
    mgr.clear_loggers()


@pytest.fixture(autouse=True)
def reset_global_logger():
    import src.common.logger.logger as logger_module

    original = logger_module._global_logger_manager
    logger_module._global_logger_manager = None
    yield
    logger_module._global_logger_manager = original


def find_log_file(base_dir: Path, event_name: str, session_id: str):
    """
    Locate the correct log file for a given event and session.
    API structure: verbose=NON_TASK/yyyy=YYYY/mm=MM/dd=DD/session_id=SESSION_ID/category=API/EVENT.log
    """
    path_pattern = f"**/session_id={session_id}/category=API/{event_name}.log"
    files = list(base_dir.glob(path_pattern))
    if not files:
        raise FileNotFoundError(
            f"No log file found for event '{event_name}', session '{session_id}'"
        )
    return files[0]


def test_logger_manager_initialization_creates_base_directory(logger_manager):
    """Test that LoggerManager creates the base logs directory on initialization."""
    assert logger_manager.base_dir.exists()


def test_api_logging_creates_correct_directory_structure(logger_manager):
    with (
        patch("src.common.logger.logger.get_session_id", return_value="session-123"),
        patch("src.common.logger.logger.get_logger_context", return_value={}),
        patch("src.common.logger.logger.get_action_context", return_value={}),
    ):
        logger_manager.log(
            category="API",
            operation="createUser",
            step="start",
            message="Test message",
            level=LogLevel.INFO,
        )

    # API category structure: verbose=NON_TASK/yyyy=YYYY/mm=MM/dd=DD/session_id=SESSION_ID/category=API/createUser.log
    now = datetime.now(UTC)
    expected_dir = (
        logger_manager.base_dir
        / "verbose=NON_TASK"
        / f"yyyy={now.year}"
        / f"mm={now.month:02d}"
        / f"dd={now.day:02d}"
        / "session_id=session-123"
        / "category=API"
    )
    assert expected_dir.exists()
    assert (expected_dir / "createUser.log").exists()


def test_task_logging_includes_task_id_in_directory_path(logger_manager):
    with (
        patch("src.common.logger.logger.get_session_id", return_value="session-456"),
        patch(
            "src.common.logger.logger.get_logger_context", return_value={"task_laui": "task-789"}
        ),
        patch("src.common.logger.logger.get_action_context", return_value={}),
    ):
        logger_manager.log(
            category="TASK",
            operation="processData",
            step="start",
            message="Processing",
            level=LogLevel.INFO,
        )

    # TASK category structure: verbose=TASK/yyyy=YYYY/mm=MM/dd=DD/task_laui=TASK_ID/session_id=SESSION_ID/category=TASK/{task_name}.log
    now = datetime.now(UTC)
    expected_dir = (
        logger_manager.base_dir
        / "verbose=TASK"
        / f"yyyy={now.year}"
        / f"mm={now.month:02d}"
        / f"dd={now.day:02d}"
        / "task_laui=task-789"
        / "session_id=session-456"
        / "category=TASK"
    )
    assert expected_dir.exists()
    # task_name not provided in context, so defaults to "no-task-name"
    assert (expected_dir / "no-task-name.log").exists()


def test_log_file_content_contains_expected_message_and_level(logger_manager):
    session_id = "session-abc"
    event_name = "testOp"

    with (
        patch("src.common.logger.logger.get_session_id", return_value=session_id),
        patch("src.common.logger.logger.get_logger_context", return_value={}),
        patch("src.common.logger.logger.get_action_context", return_value={}),
    ):
        logger_manager.log(
            category="API",
            operation=event_name,
            step="execute",
            message="Test log message",
            level=LogLevel.INFO,
        )

    log_file = find_log_file(logger_manager.base_dir, event_name, session_id)
    content = log_file.read_text()
    assert "Test log message" in content
    assert '"level": "info"' in content  # JSON stores level as lowercase


def test_log_entry_is_valid_json(logger_manager):
    """Each line in a log file is a valid JSON object with required fields."""
    with (
        patch("src.common.logger.logger.get_session_id", return_value="session-json"),
        patch("src.common.logger.logger.get_logger_context", return_value={}),
        patch("src.common.logger.logger.get_action_context", return_value={}),
    ):
        logger_manager.log("API", "jsonOp", "step1", "JSON test", LogLevel.WARNING)

    log_file = find_log_file(logger_manager.base_dir, "jsonOp", "session-json")
    for line in log_file.read_text().splitlines():
        if line.strip():
            entry = json.loads(line)
            assert "timestamp" in entry
            assert "level" in entry
            assert "message" in entry
            assert "session_id" in entry
            assert entry["level"] == "warning"
            assert entry["message"] == "JSON test"


def test_multiple_log_levels_write_to_same_file(logger_manager):
    with (
        patch("src.common.logger.logger.get_session_id", return_value="session-xyz"),
        patch("src.common.logger.logger.get_logger_context", return_value={}),
        patch("src.common.logger.logger.get_action_context", return_value={}),
    ):
        logger_manager.log("API", "test", "step1", "Info message", LogLevel.INFO)
        logger_manager.log("API", "test", "step2", "Error message", LogLevel.ERROR)
        logger_manager.log("API", "test", "step3", "Warning message", LogLevel.WARNING)

    log_file = find_log_file(logger_manager.base_dir, "test", "session-xyz")
    content = log_file.read_text()
    assert "Info message" in content
    assert "Error message" in content
    assert "Warning message" in content


def test_task_history_category_creates_correct_path(logger_manager):
    """TASK_HISTORY category with operation='task' creates timestamped filename."""
    now = datetime.now(UTC)
    with (
        patch("src.common.logger.logger.get_session_id", return_value="session-th"),
        patch(
            "src.common.logger.logger.get_logger_context",
            return_value={
                "task_laui": "task-th-001",
                "task_name": "my-task",
                "logical_date": now,
            },
        ),
        patch("src.common.logger.logger.get_action_context", return_value={}),
    ):
        logger_manager.log(
            category="TASK_HISTORY",
            operation="task",
            step="start",
            message="Task history entry",
            level=LogLevel.INFO,
        )

    expected_dir = (
        logger_manager.base_dir
        / "category=TASK_HISTORY"
        / "task_laui=task-th-001"
        / f"yyyy={now.year}"
        / f"mm={now.month:02d}"
        / f"dd={now.day:02d}"
    )
    assert expected_dir.exists()
    # Filename: {timestamp}__{session_id}__{task_name}.log
    files = list(expected_dir.glob("*__session-th__my-task.log"))
    assert len(files) >= 1


def test_cron_category_creates_correct_path(logger_manager):
    """CRON category creates project-scoped directory with cron.log."""
    now = datetime.now(UTC)
    with (
        patch("src.common.logger.logger.get_session_id", return_value="session-cron"),
        patch(
            "src.common.logger.logger.get_logger_context",
            return_value={
                "project_laui": "proj-001",
                "logical_date": now,
            },
        ),
        patch("src.common.logger.logger.get_action_context", return_value={}),
    ):
        logger_manager.log(
            category="CRON",
            operation="schedule",
            step="tick",
            message="Cron triggered",
            level=LogLevel.INFO,
        )

    expected_dir = (
        logger_manager.base_dir
        / "category=CRON"
        / "project=proj-001"
        / f"yyyy={now.year}"
        / f"mm={now.month:02d}"
        / f"dd={now.day:02d}"
    )
    assert expected_dir.exists()
    assert (expected_dir / "cron.log").exists()


def test_action_dual_write_with_pre_action_type(logger_manager):
    """ACTION category with PRE_ACTION type writes to both TASK_HISTORY snapshot and rolling action log."""
    now = datetime.now(UTC)
    with (
        patch("src.common.logger.logger.get_session_id", return_value="session-dual"),
        patch(
            "src.common.logger.logger.get_logger_context",
            return_value={
                "task_laui": "task-dual",
                "task_name": "dual-task",
                "logical_date": now,
            },
        ),
        patch(
            "src.common.logger.logger.get_action_context",
            return_value={
                "name": "my-action",
                "action_type": "PRE_ACTIONS",
            },
        ),
    ):
        logger_manager.log(
            category="ACTION",
            operation="runAction",
            step="execute",
            message="Dual write test",
            level=LogLevel.INFO,
        )

    # 1. TASK_HISTORY snapshot: latest_pre_action_{task_name}_{action_name}.log
    th_dir = (
        logger_manager.base_dir
        / "category=TASK_HISTORY"
        / "task_laui=task-dual"
        / f"yyyy={now.year}"
        / f"mm={now.month:02d}"
        / f"dd={now.day:02d}"
    )
    assert th_dir.exists()
    th_files = list(th_dir.glob("latest_pre_actions_dual-task_my-action.log"))
    assert len(th_files) == 1

    # 2. Action rolling log under verbose=TASK/category=PRE_ACTIONS
    action_dir = (
        logger_manager.base_dir
        / "verbose=TASK"
        / f"yyyy={now.year}"
        / f"mm={now.month:02d}"
        / f"dd={now.day:02d}"
        / "task_laui=task-dual"
        / "session_id=session-dual"
        / "category=PRE_ACTIONS"
    )
    assert action_dir.exists()
    assert (action_dir / "my-action.log").exists()


def test_resolve_write_mode_first_write_clears_then_appends(logger_manager):
    """First write for a (file, session) pair returns 'w'; all subsequent return 'a'."""
    dummy_file = logger_manager.base_dir / "test_mode.log"
    session = "sess-mode"

    assert logger_manager._resolve_write_mode(dummy_file, session) == "w"
    assert logger_manager._resolve_write_mode(dummy_file, session) == "a"
    assert logger_manager._resolve_write_mode(dummy_file, session) == "a"


def test_task_categories_use_verbose_task_path(logger_manager):
    """PRE_ACTION, POST_ACTION, and RUNNING_ACTION all route to verbose=TASK directory."""
    now = datetime.now(UTC)
    for cat in ("PRE_ACTIONS", "POST_ACTIONS", "RUNNING_ACTIONS"):
        with (
            patch("src.common.logger.logger.get_session_id", return_value=f"sess-{cat}"),
            patch(
                "src.common.logger.logger.get_logger_context",
                return_value={
                    "task_laui": f"task-{cat}",
                    "task_name": "t",
                },
            ),
            patch("src.common.logger.logger.get_action_context", return_value={"name": "act1"}),
        ):
            logger_manager.log(cat, "op", "step", f"{cat} message", LogLevel.INFO)

        expected_dir = (
            logger_manager.base_dir
            / "verbose=TASK"
            / f"yyyy={now.year}"
            / f"mm={now.month:02d}"
            / f"dd={now.day:02d}"
            / f"task_laui=task-{cat}"
            / f"session_id=sess-{cat}"
            / f"category={cat}"
        )
        assert expected_dir.exists(), f"{cat} directory not found"
        assert (expected_dir / "act1.log").exists(), f"{cat} log file not found"


def test_clear_loggers_resets_all_internal_state(logger_manager):
    """clear_loggers() closes all handlers and empties all internal dicts."""
    with (
        patch("src.common.logger.logger.get_session_id", return_value="sess-clear"),
        patch("src.common.logger.logger.get_logger_context", return_value={}),
        patch("src.common.logger.logger.get_action_context", return_value={}),
    ):
        logger_manager.log("API", "clearTest", "step", "Before clear", LogLevel.INFO)

    assert len(logger_manager._loggers) > 0

    logger_manager.clear_loggers()

    assert len(logger_manager._loggers) == 0
    assert len(logger_manager._overwrite_initialized) == 0


def test_initialize_logger_creates_global_logger_manager_instance(real_config):
    initialize_logger(real_config)
    manager = get_logger_manager()
    assert manager is not None
    assert isinstance(manager, LoggerManager)


def test_get_logger_manager_raises_runtime_error_when_not_initialized():
    import src.common.logger.logger as logger_module

    logger_module._global_logger_manager = None
    with pytest.raises(RuntimeError, match="LoggerManager not initialized"):
        get_logger_manager()


def test_log_error_function_raises_runtime_error_without_initialization():
    import src.common.logger.logger as logger_module

    logger_module._global_logger_manager = None
    with pytest.raises(RuntimeError, match="LoggerManager not initialized"):
        log_error("API", "failTest", "error", "This should fail")
