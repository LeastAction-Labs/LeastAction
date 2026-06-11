# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import traceback
from datetime import UTC, datetime

from src.common.context_vars.session_context import (
    clear_logger_context,
    clear_session_id,
    generate_session_id,
    set_logger_context,
    set_session_id,
)
from src.common.logger.logger import log_error, log_info
from src.core.celery.app import app, get_celery_config
from src.core.celery.worker_init import get_api_client, get_worker_loop
from src.core.cron.cron_executor import CronExecutor
from src.core.cron.schema import CronStatus

celery_cfg = get_celery_config()


@app.task(
    bind=True,
    name="least_action.run_cron",
    queue=celery_cfg.cron_queue,
)
def run_cron(self, project_laui: str, interval: int, system_auth_token: str) -> None:
    """
    Celery entrypoint for CRON execution.
    SYNC → async bridge.

    Args:
        project_laui: Project LAUI to run cron for
        interval: Interval in seconds
        system_auth_token: System authentication token for API calls
    """
    # Generate a unique session ID for this cron run
    session_id = generate_session_id()

    # Set session context for logging and tracking
    set_session_id(session_id)
    set_logger_context({"project_laui": project_laui, "interval": interval, "cron_run": True})

    log_info(
        "celery",
        "run_cron",
        "start",
        f"Cron task started for project_laui={project_laui}, interval={interval}s, celery_task_laui={self.request.id}, session_id={session_id}",
    )

    loop = get_worker_loop()

    try:
        log_info(
            "celery",
            "run_cron",
            "executor_init",
            f"Initializing CronExecutor for project_laui={project_laui} with system auth token",
        )
        cron_executor = CronExecutor(project_laui, interval, get_api_client(), system_auth_token)

        log_info(
            "celery",
            "run_cron",
            "executor_run",
            f"Starting CronExecutor.run() for project_laui={project_laui}",
        )
        loop.run_until_complete(cron_executor.run())

        log_info(
            "celery",
            "run_cron",
            "success",
            f"Cron task completed successfully for project_laui={project_laui}",
        )
    except Exception as e:
        log_error(
            "celery",
            "run_cron",
            "error",
            f"Cron task failed for project_laui={project_laui}: {str(e)}\n{traceback.format_exc()}",
        )
        # Set project cron status to ERROR so the UI reflects the failure
        try:
            api_client = get_api_client()
            project = loop.run_until_complete(
                api_client.get_project(system_auth_token, project_laui)
            )
            folder_metadata = dict(project.get("folder_metadata", {}) or {})
            folder_metadata["cron_status"] = CronStatus.ERROR
            folder_metadata["error"] = str(e)
            folder_metadata["latest_heartbeat"] = datetime.now(UTC).isoformat()
            loop.run_until_complete(
                api_client.update_project_metadata(
                    system_auth_token,
                    item_laui=str(project["laui"]),
                    item_type=project["item_type"],
                    name=project["name"],
                    parent_laui=str(project.get("parent_laui", "")),
                    folder_metadata=folder_metadata,
                    account_laui=str(project["account_laui"])
                    if project.get("account_laui")
                    else None,
                    project_laui=str(project["project_laui"])
                    if project.get("project_laui")
                    else None,
                )
            )
        except Exception as status_err:
            log_error(
                "celery",
                "run_cron",
                "error_status_update",
                f"Failed to set ERROR status for project_laui={project_laui}: {status_err}",
            )
        # MUST re-raise so Celery marks FAILURE
        raise

    finally:
        clear_session_id()
        clear_logger_context()
