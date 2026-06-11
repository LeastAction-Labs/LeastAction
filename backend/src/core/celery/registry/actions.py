# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import json
from datetime import datetime

from celery.exceptions import SoftTimeLimitExceeded
from celery.result import AsyncResult

from src.common.context_vars.session_context import (
    clear_logger_context,
    clear_session_id,
    set_action_context,
    set_logger_context,
    set_session_id,
)
from src.common.exceptions import CeleryExecutionError
from src.common.logger.logger import log_error, log_info
from src.core.celery.app import app, get_celery_config
from src.core.celery.schema import ActionRequest
from src.core.celery.worker_init import get_action_execution_service, get_worker_loop

celery_cfg = get_celery_config()


@app.task(
    bind=True,
    name="least_action.execute_action",
    soft_time_limit=celery_cfg.action_soft_time_limit,
    time_limit=celery_cfg.action_hard_time_limit,
    queue=celery_cfg.action_queue,
)
def execute_action(self, la_action_object: dict) -> AsyncResult:
    """
    Celery entrypoint for ACTION execution.
    SYNC -> async bridge.
    """
    # Extract session info from action object before parsing
    session_id = la_action_object.get("session_id", "")
    if not session_id:
        raise CeleryExecutionError("Missing session_id in action object")
    task = la_action_object.get("task", {})
    task_laui = task.get("laui", "no-task-laui")
    task_name = task.get("name", "")
    # Actions don't have logical_date in schema, use current time or extract from task_result if available
    logical_date = None
    if task:
        raw = task.get("logical_date")
        if isinstance(raw, datetime):
            logical_date = raw
        elif isinstance(raw, str):
            try:
                logical_date = datetime.fromisoformat(raw)
            except ValueError:
                logical_date = None

    # Set session context for logging
    set_session_id(session_id)
    set_logger_context(
        {"task_laui": task_laui, "task_name": task_name, "logical_date": logical_date}
    )
    set_action_context(la_action_object)
    log_info(
        "action",
        "execute_action",
        "execute_action",
        f"Received action execution request : {la_action_object}",
    )

    loop = get_worker_loop()

    try:
        log_info(
            "action",
            "execute_action",
            "started",
            f"Received action execution request for action_id={task_laui}",
        )

        log_info(
            "action",
            "execute_action",
            "parsingRequest",
            f"Parsing action request with data: {la_action_object}",
        )

        # Parse connection from JSON string to dict if needed
        if "connection" in la_action_object and isinstance(la_action_object["connection"], str):
            la_action_object["connection"] = json.loads(la_action_object["connection"])

        action_request = ActionRequest(**la_action_object)

        log_info(
            "action",
            "execute_action",
            "executing",
            f"Starting action execution for action_id={task_laui}, connection={action_request.connection}",
        )

        result = loop.run_until_complete(
            get_action_execution_service().execute_action(action_request)
        )

        log_info(
            "action",
            "execute_action",
            "completed",
            f"Action execution completed successfully with result: {result}",
        )

        return result

    except SoftTimeLimitExceeded:
        log_error(
            "action",
            "execute_action",
            "timeout",
            f"Action exceeded soft time limit ({celery_cfg.action_soft_time_limit}s)",
        )
        return False

    except Exception as e:
        log_error("action", "execute_action", "failed", f"Action execution failed: {str(e)}")
        return False

    finally:
        log_info("action", "execute_action", "cleanup", "Cleaning up action execution resources")
        clear_session_id()
        clear_logger_context()
