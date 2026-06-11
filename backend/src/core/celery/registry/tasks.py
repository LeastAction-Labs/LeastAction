# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from typing import Any

from celery.exceptions import SoftTimeLimitExceeded
from celery.result import AsyncResult

from src.common.context_vars.session_context import (
    clear_logger_context,
    clear_session_id,
    set_logger_context,
    set_session_id,
)
from src.common.exceptions import CeleryExecutionError
from src.common.logger.logger import log_error, log_info
from src.core.celery.app import app, celery_cfg, get_celery_config
from src.core.celery.schema import TaskRequest
from src.core.celery.worker_init import get_task_execution_service, get_worker_loop

celery_cfg = get_celery_config()


@app.task(
    bind=True,
    name="least_action.execute_task",
    soft_time_limit=celery_cfg.task_soft_time_limit,
    time_limit=celery_cfg.task_hard_time_limit,
    queue=celery_cfg.task_queue,
)
def execute_task(self, la_task_object: dict[str, Any]) -> AsyncResult:
    """
    Celery entrypoint for TASK execution.
    SYNC -> async bridge.
    """
    # Extract session info from task object before parsing
    session_id = la_task_object.get("last_run_session_id", "")
    if not session_id:
        raise CeleryExecutionError("Missing session_id in task object")
    task_laui = str(la_task_object.get("laui", ""))
    if not task_laui:
        raise CeleryExecutionError("Missing laui (task_laui) in task object")

    logical_date = la_task_object.get("logical_date", "adhoc-no-logical-date")

    # Set session context for logging
    set_session_id(session_id)
    set_logger_context(
        {
            "task_laui": task_laui,
            "logical_date": logical_date,
            "task_name": la_task_object.get("name", "no-name"),
        }
    )

    loop = get_worker_loop()

    try:
        log_info(
            "celery",
            "executeTask",
            "started",
            f"Task received: task_laui={task_laui}, operator={la_task_object.get('operator_laui', 'unknown')}",
        )

        task_request = TaskRequest(**la_task_object)

        result = loop.run_until_complete(
            get_task_execution_service().execute_task(task_request, celery_task_id=self.request.id)
        )

        return result

    except SoftTimeLimitExceeded:
        log_error(
            "celery",
            "executeTask",
            "timeout",
            f"Task exceeded soft time limit ({celery_cfg.task_soft_time_limit}s)",
        )
        raise

    except Exception as e:
        log_error("celery", "executeTask", "failed", f"Task execution failed: {str(e)}")
        raise

    finally:
        clear_session_id()
        clear_logger_context()
