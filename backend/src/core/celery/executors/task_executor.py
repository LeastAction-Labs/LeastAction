# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import asyncio
import json
import sys

# from src.common.session_context import get_session_id
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi.encoders import jsonable_encoder

from src.common.exceptions import CeleryExecutionError, InvalidOperatorError
from src.common.logger.logger import log_error, log_info, log_warning
from src.common.utils import load_system_config
from src.core.celery.client import APIClient
from src.core.celery.executors.operator_executor import OperatorExecutor
from src.core.celery.schema import TaskRequest
from src.core.celery.utils import create_module_from_codeblock, load_module
from src.core.task.action.action_manager import ActionManager
from src.core.task.action.schema import ActionItem, Actions
from src.core.task.schema import TaskState, TaskUpdateData, task_state_map
from src.core.task.utils import calculate_logical_date, calculate_next_run_date


class TaskExecutionService:
    def __init__(self, api_client: APIClient, operators_dir: Path, action_manager: ActionManager):
        self.api_client = api_client
        self.celery_cfg = load_system_config()["celery"]
        self.action_manager = action_manager
        self.operator_dir = operators_dir
        self.operator_dir.mkdir(parents=True, exist_ok=True)

    async def _update_heartbeat(self, la_task_object: TaskRequest) -> None:
        try:
            await self.api_client.update_item(
                la_task_object.user_access_token,
                str(la_task_object.laui),
                update_data=TaskUpdateData(
                    latest_heartbeat=datetime.now(UTC), state=TaskState.RUNNING
                ),
            )
        except Exception as e:
            log_error(
                "celery",
                "TaskExecutionService",
                "_update_heartbeat",
                f"Error updating heartbeat: {str(e)}",
            )

    async def _check_cancellation(self, la_task_object: TaskRequest) -> bool:
        try:
            item = await self.api_client.get_item(
                la_task_object.user_access_token,
                la_task_object.laui,
                la_task_object.last_run_session_id,
            )

            user_set_state = getattr(item, "user_set_state", None)
            return bool(item and user_set_state == "cancel")
        except Exception as e:
            log_error(
                "celery",
                "TaskExecutionService",
                "_check_cancellation",
                f"Error checking cancellation: {str(e)}",
            )
            return False

    def _cleanup(self, module, files) -> None:
        if module and module.__name__ in sys.modules:
            del sys.modules[module.__name__]
        if files:
            for f in files:
                try:
                    f.unlink(missing_ok=True)
                except Exception:
                    pass

    async def _execute_running_actions(
        self,
        running_actions: list[ActionItem],
        elapsed: float,
        la_task_object: TaskRequest,
        sla_actions_executed: set,
    ) -> None:
        try:
            actions_to_execute: list[ActionItem] = []

            for action in running_actions:
                try:
                    if action.sla is None:
                        continue

                    sla_threshold = action.sla * 60
                    if elapsed > sla_threshold and action.laui not in sla_actions_executed:
                        actions_to_execute.append(action)

                except Exception as e:
                    log_error(
                        "celery",
                        "TaskExecutionService",
                        "_execute_running_actions",
                        f"Error processing action {getattr(action, 'laui', 'unknown')}: {str(e)}",
                    )

            if not actions_to_execute:
                return

            try:
                actions_item = Actions(running_actions=actions_to_execute)
                await self.action_manager.running_actions(
                    actions_item, la_task_object.user_access_token, la_task_object.model_dump()
                )
                sla_actions_executed.update(action.laui for action in actions_to_execute)
                log_info(
                    "celery",
                    "TaskExecutionService",
                    "_execute_running_actions",
                    f"Executed {len(actions_to_execute)} SLA actions",
                )

            except Exception as e:
                log_error(
                    "celery",
                    "TaskExecutionService",
                    "_execute_running_actions",
                    f"Failed to execute running actions: {str(e)}",
                )

        except Exception as e:
            log_error(
                "celery",
                "TaskExecutionService",
                "_execute_running_actions",
                f"Unexpected error: {str(e)}",
            )

    async def _execute_post_actions(self, la_task_object: TaskRequest) -> None:
        try:
            if not la_task_object.actions or not la_task_object.actions.post_actions:
                return

            try:
                actions_item = Actions(post_actions=la_task_object.actions.post_actions)
                await self.action_manager.post_actions(
                    actions_item, la_task_object.user_access_token, la_task_object.model_dump()
                )
                log_info(
                    "celery",
                    "TaskExecutionService",
                    "_execute_post_actions",
                    f"Executed {len(la_task_object.actions.post_actions)} post-actions",
                )

            except Exception as e:
                log_error(
                    "celery",
                    "TaskExecutionService",
                    "_execute_post_actions",
                    f"Failed to execute post-actions: {str(e)}",
                )

        except Exception as e:
            log_error(
                "celery",
                "TaskExecutionService",
                "_execute_post_actions",
                f"Unexpected error: {str(e)}",
            )

    async def execute_task(
        self, la_task_object: TaskRequest, system_auth_token: str, celery_task_id: str | None = None
    ) -> None:
        start_time = datetime.now(UTC)
        task_history_details = {
            "task_laui": str(la_task_object.laui),
            "task_name": la_task_object.name,
            "operator_laui": str(la_task_object.operator_laui),
            "session_id": la_task_object.last_run_session_id,
            "partition": la_task_object.partition or "ALL",
            "state": la_task_object.state,
            "user_set_state": la_task_object.user_set_state,
            "start_time": start_time.isoformat(),
            "duration_seconds": 0,
            "logical_date": la_task_object.logical_date.isoformat()
            if la_task_object.logical_date
            else None,
            "data_interval_start": la_task_object.data_interval_start.isoformat()
            if la_task_object.data_interval_start
            else None,
            "data_interval_end": la_task_object.data_interval_end.isoformat()
            if la_task_object.data_interval_end
            else None,
            "prev_interval_start": la_task_object.prev_interval_start.isoformat()
            if la_task_object.prev_interval_start
            else None,
            "prev_interval_end": la_task_object.prev_interval_end.isoformat()
            if la_task_object.prev_interval_end
            else None,
            "task_instance_start_date": la_task_object.task_instance_start_date.isoformat()
            if la_task_object.task_instance_start_date
            else None,
            "task_instance_end_date": la_task_object.task_instance_end_date.isoformat()
            if la_task_object.task_instance_end_date
            else None,
            "last_run_date": la_task_object.last_run_date.isoformat()
            if la_task_object.last_run_date
            else None,
            "next_run_date": la_task_object.next_run_date.isoformat()
            if la_task_object.next_run_date
            else None,
            "frequency": la_task_object.frequency or "ADHOC",
            "iteration": la_task_object.iteration,
            "retry_number": la_task_object.retry_number,
            "total_retries": la_task_object.total_retries,
            "retry_interval": la_task_object.retry_interval,
            "can_retry": la_task_object.can_retry,
            "task_reschedule_count": la_task_object.task_reschedule_count,
            "executor": la_task_object.executor,
            "task_instance": la_task_object.task_instance,
            "priority": la_task_object.priority,
            "actions_status": {
                "pre_actions": la_task_object.actions_status.get("pre_actions", []),
                "running_actions": la_task_object.actions_status.get("running_actions", []),
                "post_actions": la_task_object.actions_status.get("post_actions", []),
            },
            "output": {},
        }
        log_info("task_history", "task", "execute_task", json.dumps(task_history_details))
        operator_files = None
        operator_module = None
        operator_exec: OperatorExecutor | None = None
        status: str = ""
        last_run_output: dict[str, Any] = {}
        run_task: asyncio.Task | None = None
        la_task_object.actions = Actions(**la_task_object.actions)
        try:
            try:
                await self.api_client.update_item(
                    la_task_object.user_access_token,
                    system_auth_token,
                    str(la_task_object.laui),
                    update_data=TaskUpdateData(
                        latest_heartbeat=datetime.now(UTC),
                        state=TaskState.RUNNING,
                        data_interval_start=la_task_object.logical_date,
                        data_interval_end=calculate_logical_date(
                            la_task_object.frequency, la_task_object.logical_date
                        ),
                        task_instance_start_date=datetime.now(UTC),
                        session_id=la_task_object.last_run_session_id,
                        executor=celery_task_id,
                    ),
                )
                log_info(
                    "celery",
                    "TaskExecutionService",
                    "execute_task",
                    f"Starting task {la_task_object.laui}, operator={la_task_object.operator_laui}",
                )
                print(
                    f"[celery] [TaskExecutionService] [execute_task] Starting task {la_task_object.laui}, operator={la_task_object.operator_laui}"
                )
            except Exception as e:
                print(
                    f"[celery] [TaskExecutionService] [execute_task] Starting task update error: {str(e)}"
                )
                log_error(
                    "celery",
                    "TaskExecutionService",
                    "execute_task",
                    f"Starting task update error: {str(e)}",
                )

            item = await self.api_client.get_item(
                la_task_object.user_access_token,
                la_task_object.operator_laui,
                la_task_object.last_run_session_id,
            )

            if not item or not getattr(item, "codeblock", None):
                raise InvalidOperatorError("Operator codeblock missing")

            operator_files = create_module_from_codeblock(
                item.codeblock, self.operator_dir, str(la_task_object.last_run_session_id)
            )
            main_file = operator_files[0]

            max_codeblock_retries = 3
            for codeblock_attempt in range(max_codeblock_retries):
                if main_file.stat().st_size > 0:
                    break
                wait_time = 0.5 * (2**codeblock_attempt)
                log_warning(
                    "celery",
                    "TaskExecutionService",
                    "execute_task",
                    f"Operator file empty, re-fetching (attempt {codeblock_attempt + 1}/{max_codeblock_retries}) in {wait_time}s, operator={la_task_object.operator_laui}",
                )
                await asyncio.sleep(wait_time)
                try:
                    item = await self.api_client.get_item(
                        la_task_object.user_access_token,
                        la_task_object.operator_laui,
                        la_task_object.last_run_session_id,
                    )
                except Exception as fetch_err:
                    is_last = codeblock_attempt == max_codeblock_retries - 1
                    log_fn = log_error if is_last else log_warning
                    log_fn(
                        "celery",
                        "TaskExecutionService",
                        "execute_task",
                        f"get_item failed on re-fetch attempt {codeblock_attempt + 1}/{max_codeblock_retries}, operator={la_task_object.operator_laui}: {fetch_err}",
                    )
                    if is_last:
                        raise
                    continue
                if not item or not getattr(item, "codeblock", None):
                    raise InvalidOperatorError("Operator codeblock missing")
                operator_files = create_module_from_codeblock(
                    item.codeblock, self.operator_dir, str(la_task_object.last_run_session_id)
                )
                main_file = operator_files[0]
            else:
                log_error(
                    "celery",
                    "TaskExecutionService",
                    "execute_task",
                    f"Operator file still empty after {max_codeblock_retries} re-fetches, operator={la_task_object.operator_laui}",
                )
                raise InvalidOperatorError(
                    message="Operator codeblock wrote an empty file",
                    detail={
                        "operator_laui": str(la_task_object.operator_laui),
                        "file": str(main_file),
                    },
                )

            operator_module = load_module(main_file)

            operator_exec = OperatorExecutor(operator_module, la_task_object)
            operator_exec.validate()

            # STEP 1: Initialize operator
            operator_exec.initialize()

            # STEP 2: Start run() in managed thread
            run_task = asyncio.create_task(asyncio.to_thread(operator_exec.run))

            # STEP 3: Poll for completion and cancellation
            elapsed = 0
            timeout_seconds = self.celery_cfg["check_completion_timeout_seconds"]
            poll_interval = self.celery_cfg.get("poll_interval_seconds")
            sla_actions_executed = set[Any]()
            running_actions: list[ActionItem] = []
            if la_task_object.actions and hasattr(la_task_object.actions, "running_actions"):
                running_actions = la_task_object.actions.running_actions

            is_async = False
            run_processed = False

            while elapsed < timeout_seconds:
                await self._update_heartbeat(la_task_object)

                if await self._check_cancellation(la_task_object):
                    log_info(
                        "celery", "TaskExecutionService", "execute_task", "Task cancelled by user"
                    )
                    operator_exec.cancelled = True
                    status = TaskState.CANCELLED
                    last_run_output["message"] = "Task cancelled by user"
                    operator_exec.finish()
                    await asyncio.sleep(3)
                    if run_task:
                        run_task.cancel()
                        try:
                            await run_task
                        except asyncio.CancelledError:
                            pass
                    break

                # Check and execute SLA actions
                if running_actions:
                    await self._execute_running_actions(
                        running_actions, elapsed, la_task_object, sla_actions_executed
                    )

                # Process run() result once when it completes
                if not run_processed and run_task.done():
                    try:
                        run_result = run_task.result()
                    except Exception as e:
                        log_error(
                            "celery",
                            "TaskExecutionService",
                            "execute_task",
                            f"Operator run failed: {str(e)}\n{traceback.format_exc()}",
                        )
                        raise CeleryExecutionError(
                            message="Operator run failed",
                            detail={"error": str(e)},
                        )

                    if not isinstance(run_result, dict):
                        run_result = {"status": "success", "output": run_result}

                    operator_exec.result = run_result
                    last_run_output["run_output"] = run_result
                    run_processed = True

                    execution_type = run_result.get("execution_type")

                    if execution_type != "async":
                        # Sync: run() already has the final status
                        raw_status = run_result.get("status", "failed")
                        status = task_state_map.get(raw_status, TaskState.ERROR)
                        # Populate completion_details so finish() receives a
                        # real payload instead of None. For sync operators
                        # check_completion() is an immediate pass-through.
                        try:
                            completion_payload = operator_exec.check_completion()
                            last_run_output["completion_output"] = completion_payload
                        except Exception as e:
                            log_error(
                                "celery",
                                "TaskExecutionService",
                                "execute_task",
                                f"check_completion failed for sync operator: {str(e)}",
                            )
                        break
                    else:
                        # Async: run() dispatched a job, poll check_completion() below
                        is_async = True

                # For async operators, poll check_completion on every iteration after run() completes
                if is_async:
                    completion_payload = operator_exec.check_completion()
                    completion_status = completion_payload.get("status", "failed")

                    task_state = task_state_map.get(completion_status, TaskState.ERROR)

                    if completion_status.lower() not in ["running", "pending"]:
                        last_run_output["completion_output"] = completion_payload
                        status = task_state
                        break

                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

            if elapsed >= timeout_seconds and not status:
                log_error(
                    "celery",
                    "TaskExecutionService",
                    "execute_task",
                    f"Task timed out after {elapsed}s",
                )
                operator_exec.cancelled = True
                status = TaskState.TIMEOUT
                last_run_output["message"] = "Operation timed out"

        except InvalidOperatorError as e:
            log_error(
                "celery",
                "TaskExecutionService",
                "execute_task",
                f"Invalid operator: {str(e)}\n{traceback.format_exc()}",
            )
            status = TaskState.FAIL
            last_run_output["error"] = str(e)

        except CeleryExecutionError as e:
            actual_error = e.detail.get("error", str(e)) if e.detail else str(e)
            log_error(
                "celery",
                "TaskExecutionService",
                "execute_task",
                f"Execution error: {actual_error}\n{traceback.format_exc()}",
            )
            status = TaskState.ERROR
            last_run_output["error"] = actual_error

        except Exception as e:
            log_error(
                "celery",
                "TaskExecutionService",
                "execute_task",
                f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
            )
            status = TaskState.ERROR
            last_run_output["error"] = str(e)

        finally:
            duration = datetime.now(UTC) - start_time
            task_history_details = {
                "task_laui": str(la_task_object.laui),
                "task_name": la_task_object.name,
                "operator_laui": str(la_task_object.operator_laui),
                "session_id": la_task_object.last_run_session_id,
                "partition": la_task_object.partition or "ALL",
                "state": status or la_task_object.state,
                "user_set_state": la_task_object.user_set_state,
                "start_time": start_time.isoformat(),
                "duration_seconds": duration.total_seconds(),
                "logical_date": la_task_object.logical_date.isoformat()
                if la_task_object.logical_date
                else None,
                "data_interval_start": la_task_object.data_interval_start.isoformat()
                if la_task_object.data_interval_start
                else None,
                "data_interval_end": la_task_object.data_interval_end.isoformat()
                if la_task_object.data_interval_end
                else None,
                "prev_interval_start": la_task_object.prev_interval_start.isoformat()
                if la_task_object.prev_interval_start
                else None,
                "prev_interval_end": la_task_object.prev_interval_end.isoformat()
                if la_task_object.prev_interval_end
                else None,
                "task_instance_start_date": la_task_object.task_instance_start_date.isoformat()
                if la_task_object.task_instance_start_date
                else None,
                "task_instance_end_date": la_task_object.task_instance_end_date.isoformat()
                if la_task_object.task_instance_end_date
                else None,
                "last_run_date": la_task_object.last_run_date.isoformat()
                if la_task_object.last_run_date
                else None,
                "next_run_date": la_task_object.next_run_date.isoformat()
                if la_task_object.next_run_date
                else None,
                "frequency": la_task_object.frequency or "ADHOC",
                "iteration": la_task_object.iteration,
                "retry_number": la_task_object.retry_number,
                "total_retries": la_task_object.total_retries,
                "retry_interval": la_task_object.retry_interval,
                "can_retry": la_task_object.can_retry,
                "task_reschedule_count": la_task_object.task_reschedule_count,
                "executor": la_task_object.executor,
                "task_instance": la_task_object.task_instance,
                "priority": la_task_object.priority,
                "actions_status": {
                    "pre_actions": la_task_object.actions_status.get("pre_actions", []),
                    "running_actions": la_task_object.actions_status.get("running_actions", []),
                    "post_actions": la_task_object.actions_status.get("post_actions", []),
                },
                "output": last_run_output or {},
            }
            log_info("task_history", "task", "execute_task", json.dumps(task_history_details))
            log_info(
                "celery",
                "TaskExecutionService",
                "execute_task",
                f"Task {la_task_object.laui} finished - status: {status}, duration: {duration.total_seconds()}s",
            )

            try:
                if status != TaskState.CANCELLED and operator_exec:
                    operator_exec.finish()
            except Exception as e:
                log_error(
                    "celery",
                    "TaskExecutionService",
                    "execute_task",
                    f"Error in operator finish(): {str(e)}",
                )

            try:
                task_update_data = TaskUpdateData(
                    state=status,
                    last_run_output=jsonable_encoder(last_run_output),
                    duration=int(duration.total_seconds()),
                    last_run_date=datetime.now(UTC),
                    task_instance_end_date=datetime.now(UTC),
                    last_run_session_id=la_task_object.last_run_session_id,
                )

                if status == TaskState.SUCCESS:
                    task_update_data.prev_interval_start = la_task_object.logical_date
                    task_update_data.logical_date = calculate_logical_date(
                        la_task_object.frequency, la_task_object.logical_date
                    )
                    task_update_data.prev_interval_end = task_update_data.logical_date
                    task_update_data.retry_number = 0
                    task_update_data.next_run_date = calculate_next_run_date(
                        la_task_object.frequency, la_task_object.next_run_date
                    )
                if status in [TaskState.ERROR, TaskState.TIMEOUT]:
                    task_update_data.retry_number = la_task_object.retry_number + 1

                await self.api_client.update_item(
                    la_task_object.user_access_token,
                    system_auth_token,
                    str(la_task_object.laui),
                    task_update_data,
                )

                await self.api_client.finish_task(
                    la_task_object.user_access_token, system_auth_token, la_task_object.laui
                )
            except Exception as e:
                log_error(
                    "celery",
                    "TaskExecutionService",
                    "execute_task",
                    f"Error updating task item: {str(e)}\n{traceback.format_exc()}",
                )

            try:
                await self._execute_post_actions(la_task_object)
            except Exception as e:
                log_error(
                    "celery",
                    "TaskExecutionService",
                    "execute_task",
                    f"Error executing post-actions: {str(e)}",
                )
                status = TaskState.ERROR

            self._cleanup(operator_module, operator_files)
