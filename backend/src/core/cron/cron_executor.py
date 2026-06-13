# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import asyncio
import traceback
from datetime import UTC, datetime
from pydantic_mongo import PydanticObjectId
from src.common.logger.logger import log_error, log_info
from src.core.celery.client import APIClient
from src.core.celery.utils import get_stale_heartbeat_threshold_seconds, is_heartbeat_stale
from src.core.cron.schema import CronStatus
from src.core.task.schema import TaskState, TaskUpdateData


class CronExecutor:
    def __init__(
        self, project_id: str, interval: int, api_client: APIClient, system_auth_token: str
    ):
        self.project_id = project_id
        self.interval = interval
        self.api_client = api_client
        # Store the system auth token for explicit passing on each API call
        self.system_auth_token = system_auth_token
        self._stop_event: asyncio.Event | None = None

    async def _update_project_metadata(self, project: dict, folder_metadata: dict) -> None:
        folder_metadata["latest_heartbeat"] = datetime.now(UTC).isoformat()
        # Update project metadata using API client
        parent_laui = project.get("parent_laui", "")

        await self.api_client.update_project_metadata(
            self.system_auth_token,
            item_laui=str(project["laui"]),
            item_type=project["item_type"],
            name=project["name"],
            parent_laui=str(parent_laui),
            folder_metadata=folder_metadata,
            account_laui=str(project["account_laui"]) if project.get("account_laui") else None,
            project_laui=str(project["project_laui"]) if project.get("project_laui") else None,
        )

    async def _update_project_status(
        self,
        status: str,
        error_message: str | None = None,
    ) -> None:
        project_laui = PydanticObjectId(self.project_id)
        project = await self.api_client.get_project(self.system_auth_token, project_laui)
        # Ensure we have a clean copy of folder_metadata to avoid reference issues
        folder_metadata = dict(project.get("folder_metadata", {}) or {})
        folder_metadata["cron_status"] = status
        folder_metadata["latest_heartbeat"] = datetime.now(UTC).isoformat()

        if error_message:
            folder_metadata["error"] = error_message

        await self._update_project_metadata(project, folder_metadata)

    async def _heartbeat_loop(self) -> None:
        """Independent heartbeat loop. Updates heartbeat and checks for stop signals."""
        while not self._stop_event.is_set():
            try:
                project_laui = PydanticObjectId(self.project_id)
                project = await self.api_client.get_project(self.system_auth_token, project_laui)
                folder_metadata = dict(project.get("folder_metadata", {}) or {})
                cron_status = folder_metadata.get("cron_status")

                # Check for stop signals
                if cron_status in [CronStatus.STOP, CronStatus.STOPPED, CronStatus.ERROR]:
                    if cron_status == CronStatus.STOP:
                        folder_metadata["cron_status"] = CronStatus.STOPPED
                        await self._update_project_metadata(project, folder_metadata)
                    log_info(
                        "cron",
                        "CronExecutor",
                        "heartbeat_loop",
                        f"[{self.project_id}] STOP signal detected (status={cron_status}). Exiting...",
                    )
                    self._stop_event.set()
                    return

                # Update heartbeat
                await self._update_project_metadata(project, folder_metadata)

            except Exception as e:
                log_error(
                    "cron",
                    "CronExecutor",
                    "heartbeat_loop",
                    f"[{self.project_id}] Heartbeat error: {str(e)}",
                )

            # Interruptible sleep: wake early if stop_event is set
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval)
                return  # stop_event was set
            except TimeoutError:
                pass  # normal: interval elapsed, continue

    async def _work_loop(self) -> None:
        """Independent work loop. Fetches and executes tasks."""
        while not self._stop_event.is_set():
            try:
                project_laui = PydanticObjectId(self.project_id)

                # Get and validate tasks
                tasks_ready_to_run = await self.api_client.get_tasks_ready_to_run(
                    self.system_auth_token, project_laui
                )

                # Extract task LAUIs from tasks ready to run
                tasks = {"task_lauis": [], "task_names": []}
                for task in tasks_ready_to_run:
                    tasks["task_lauis"].append(str(task.get("laui")))
                    tasks["task_names"].append(str(task.get("name")))

                log_info(
                    "cron",
                    "CronExecutor",
                    "trigger_task_ready_to_run",
                    f"Picked up {len(tasks_ready_to_run)} task(s): {tasks['task_names']}",
                )

                # Execute multiple tasks using the updated API
                await self.api_client.run_multiple_tasks(self.system_auth_token, tasks)

            except Exception as e:
                log_error(
                    "cron",
                    "CronExecutor",
                    "work_loop",
                    f"[{self.project_id}] Error in work iteration: {str(e)}\n{traceback.format_exc()}",
                )

            # Interruptible sleep: wake early if stop_event is set
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval)
                return  # stop_event was set
            except TimeoutError:
                pass  # normal: interval elapsed, continue

    async def _cleanup_stale_heartbeats_loop(self) -> None:
        """Independent loop that checks for stale heartbeats and cleans up stuck tasks."""
        while not self._stop_event.is_set():
            try:
                threshold = get_stale_heartbeat_threshold_seconds()
                running_tasks = await self.api_client.get_running_tasks(
                    self.system_auth_token, self.project_id
                )

                for task in running_tasks:
                    latest_heartbeat = task.get("latest_heartbeat")
                    task_laui = str(task.get("laui", task.get("_id", "")))
                    task_name = task.get("name", "unknown")

                    if is_heartbeat_stale(latest_heartbeat, threshold):
                        log_info(
                            "cron",
                            "CronExecutor",
                            "_cleanup_stale_heartbeats_loop",
                            f"Stale heartbeat detected for task {task_name} ({task_laui})",
                        )
                        try:
                            await self.api_client.update_item(
                                self.system_auth_token,
                                task_laui,
                                update_data=TaskUpdateData(
                                    state=TaskState.FAIL,
                                    last_run_output={
                                        "error": "An error occurred during execution. Task heartbeat went stale."
                                    },
                                    last_system_updated_date=datetime.now(UTC),
                                ),
                            )
                            await self.api_client.finish_task(self.system_auth_token, task_laui)
                            log_info(
                                "cron",
                                "CronExecutor",
                                "_cleanup_stale_heartbeats_loop",
                                f"Cleaned up stale task {task_name} ({task_laui})",
                            )
                        except Exception as task_err:
                            log_error(
                                "cron",
                                "CronExecutor",
                                "_cleanup_stale_heartbeats_loop",
                                f"Failed to clean up stale task {task_laui}: {str(task_err)}",
                            )

            except Exception as e:
                log_error(
                    "cron",
                    "CronExecutor",
                    "_cleanup_stale_heartbeats_loop",
                    f"[{self.project_id}] Cleanup error: {str(e)}",
                )

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval)
                return
            except TimeoutError:
                pass

    async def run(self) -> None:
        """Main scheduler that runs heartbeat and work loops concurrently."""
        try:
            log_info(
                "cron",
                "CronExecutor",
                "run",
                f"Starting scheduler for project_id={self.project_id}, interval={self.interval}s",
            )

            # Check initial project status
            project_laui = PydanticObjectId(self.project_id)
            project = await self.api_client.get_project(self.system_auth_token, project_laui)

            folder_metadata = dict(project.get("folder_metadata", {}) or {})
            cron_status = folder_metadata.get("cron_status")

            if cron_status == CronStatus.STOP:
                await self._update_project_status(CronStatus.STOPPED)
                return

            if cron_status in [CronStatus.STOPPED, CronStatus.ERROR]:
                log_info(
                    "cron",
                    "CronExecutor",
                    "run",
                    f"Project {self.project_id} cron status is {cron_status}. Exiting...",
                )
                return

            # Set status to RUNNING
            folder_metadata["cron_status"] = CronStatus.RUNNING
            await self._update_project_metadata(project, folder_metadata)
            log_info(
                "cron",
                "CronExecutor",
                "run",
                f"Status updated to {CronStatus.RUNNING}, heartbeat initialized",
            )

            # Initialize stop event and run both loops concurrently
            self._stop_event = asyncio.Event()
            await asyncio.gather(
                self._heartbeat_loop(),
                self._work_loop(),
                self._cleanup_stale_heartbeats_loop(),
            )

            log_info(
                "cron",
                "CronExecutor",
                "run",
                f"[{self.project_id}] Executor stopped.",
            )

        except asyncio.CancelledError:
            log_info(
                "cron",
                "CronExecutor",
                "run",
                f"[{self.project_id}] Scheduler cancelled.",
            )

        except Exception as e:
            log_error(
                "cron",
                "CronExecutor",
                "run",
                f"[{self.project_id}] Scheduler error: {str(e)}\n{traceback.format_exc()}",
            )
            raise
