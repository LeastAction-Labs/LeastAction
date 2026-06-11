# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import UTC, datetime, timedelta

from bson import ObjectId
from fastapi import Request
from pydantic_mongo import PydanticObjectId

from src.common.context_vars.session_context import get_session_id
from src.common.context_vars.user_context import get_user_laui
from src.common.exceptions import UnprocessableEntityError
from src.common.logger.logger import log_error, log_warning
from src.common.utils import load_system_config
from src.core.catalog.item.schema import Item
from src.core.catalog.service import CatalogService
from src.core.celery.utils import get_stale_heartbeat_threshold_seconds, is_heartbeat_stale
from src.core.task.action.pre_action_manager import PreActionManager
from src.core.task.action.schema import Actions
from src.core.task.celery_orchestrator import CeleryOrchestrator
from src.core.task.config.config_manager import ConfigManager
from src.core.task.connection.connection_manager import ConnectionManager
from src.core.task.connection.connection_queue_manager import ConnectionQueueManager
from src.core.task.schema import Task, TaskCreationValidationModel, TaskValidationModel
from src.core.task.task_validation_manager import TaskValidationManager


class TaskManager:
    def __init__(
        self,
        task_validation_manager: TaskValidationManager,
        pre_action_manager: PreActionManager,
        celery_orchestrator: CeleryOrchestrator,
        connection_queue_manager: ConnectionQueueManager,
        catalog_service: CatalogService,
        config_manager: ConfigManager,
        connection_manager: ConnectionManager,
    ):
        self.task_validation_manager = task_validation_manager
        self.pre_action_manager = pre_action_manager
        self.celery_orchestrator = celery_orchestrator
        self.connection_queue_manager = connection_queue_manager
        self.catalog_service = catalog_service
        self.config_manager = config_manager
        self.connection_manager = connection_manager
        self.system_config = load_system_config()

    async def validate_task_creation(
        self, task_data: TaskCreationValidationModel
    ) -> TaskCreationValidationModel:
        # TODO check entire breadcrumb for same project relation
        result = await self.task_validation_manager.validate_task_creation(task_data)
        if task_data.actions:
            user_laui = get_user_laui()
            actions = (
                result.actions if isinstance(result.actions, Actions) else Actions(**result.actions)
            )
            if not await self.pre_action_manager.create_actions(actions, user_laui, task=None):
                raise UnprocessableEntityError(
                    message="Task creation failed because a create action failed"
                )
        return result

    async def validate_task_execution(
        self, tasks: list[TaskValidationModel]
    ) -> list[TaskValidationModel]:
        # TODO update error status in db for each task
        result = await self.task_validation_manager.validate_task_execution(tasks)
        return result

    async def execute_tasks(self, task_items: list[Item]) -> dict[str, list]:
        # STEP 1: convert task_items from Item -> TaskValidationModel
        tasks: list[TaskValidationModel] = []
        tasks_to_execute = []
        task_results = []
        for task_item in task_items:
            task_dict = task_item.model_dump()
            task_dict["laui"] = task_item.laui
            tasks.append(TaskValidationModel(**task_dict))

        # STEP 2: Validate
        original_tasks = [TaskValidationModel(**task.model_dump()) for task in tasks]
        validated_tasks = await self.validate_task_execution(tasks)
        validated_task_lauis = [task.laui for task in validated_tasks]
        filtered_original_tasks = [
            task for task in original_tasks if task.laui in validated_task_lauis
        ]

        for original_task, validated_task in zip(
            filtered_original_tasks, validated_tasks, strict=False
        ):
            update_dict = self._get_task_delta(Task(**original_task.model_dump()), validated_task)
            if update_dict:
                update_dict["last_system_updated_date"] = datetime.now(UTC)
                await self.catalog_service.update_task_item(original_task.laui, update_dict)

        # STEP 3: Log validation results
        if not validated_tasks:
            log_warning("api", "TaskManager", "execute_task", "Zero valid tasks after validation")

        # STEP 4: Execute pre_actions
        for task in validated_tasks:
            user_laui = str(task.updated_by) if task.updated_by else str(task.created_by)
            actions = task.actions if isinstance(task.actions, Actions) else Actions(**task.actions)
            pre_action_res = await self.pre_action_manager.pre_actions(actions, user_laui, task)
            if pre_action_res:
                tasks_to_execute.append(task)

        # STEP 5: Connection queue load balancing
        tasks_to_execute: list[Task] = await self.connection_queue_manager.load_balance_tasks(
            tasks_to_execute
        )

        # STEP 5.5: Process payload placeholder replacement for all tasks
        tasks_to_execute = [
            self.config_manager.process_task_execution(task) for task in tasks_to_execute
        ]

        # STEP 6: Send to celery
        for task in tasks_to_execute:
            task.last_run_session_id = get_session_id()
            res = await self.celery_orchestrator.run_task(task)
            task_results.append({"task_laui": str(task.laui), "execution_result_id": str(res)})

        return {"tasks": tasks_to_execute, "task_results": task_results}

    @staticmethod
    def _ensure_utc(dt):
        """Ensure a datetime is timezone-aware (UTC) for safe comparison."""
        if dt is None:
            return None
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt

    async def diagnose_task(self, task_laui: PydanticObjectId) -> dict:
        now = datetime.now(UTC)
        diagnostics = []
        # Fetch the task
        task = await self.catalog_service.find_item(item_laui=task_laui)
        task_dict = task.model_dump()
        task_name = getattr(task, "name", "unknown")
        current_state = getattr(task, "state", None)
        # Fetch project for scheduler status
        project_laui = getattr(task, "project_laui", None)
        project = None
        if project_laui:
            try:
                project = await self.catalog_service.find_item(item_laui=ObjectId(project_laui))
            except Exception:
                pass

        # Fetch related items (include deleted to detect deletions)
        related_lauis = []
        operator_laui = getattr(task, "operator_laui", None)
        connection_laui = getattr(task, "connection_laui", None)
        payload_laui = getattr(task, "payload_laui", None)
        parent_laui = getattr(task, "parent_laui", None)
        attached_config_lauis = getattr(task, "attached_config_lauis", None) or []

        for laui in [operator_laui, connection_laui, payload_laui, parent_laui]:
            if laui:
                related_lauis.append(laui)
        for cfg_laui in attached_config_lauis:
            if cfg_laui:
                related_lauis.append(cfg_laui)

        related_items = {}
        if related_lauis:
            try:
                items = await self.catalog_service.find_multiple_items_by_laui(
                    item_lauis=related_lauis,
                    projections={},
                    include_deleted=True,
                )
                related_items = {str(item.laui): item for item in items}
            except Exception as e:
                log_error(
                    "api", "TaskManager", "diagnose_task", f"Error fetching related items: {e}"
                )

        # Check connection queue
        cq_entry = None
        try:
            task_for_cq = TaskValidationModel(**task_dict)
            cq_entry = await self.connection_queue_manager.get_connection_queue(task_for_cq)
        except Exception:
            pass

        # --- Run all 15 checks ---

        # 1. Next run date in future
        next_run_date = self._ensure_utc(getattr(task, "next_run_date", None))
        detected_1 = next_run_date is not None and next_run_date > now
        desc_1 = (
            f"next_run_date ({next_run_date}) is after current time ({now})."
            if detected_1
            else "next_run_date is not in the future."
        )
        diagnostics.append(
            {
                "case_id": 1,
                "title": "Next run date in future",
                "passed_title": "Next run date reached",
                "description": desc_1,
                "severity": "info",
                "detected": detected_1,
            }
        )

        # 2. Scheduler not running (non-ADHOC tasks)
        frequency = getattr(task, "frequency", "ADHOC")
        detected_2 = False
        desc_2 = "Scheduler check not applicable (ADHOC task)."
        if frequency != "ADHOC" and next_run_date and next_run_date < now and project:
            folder_metadata = getattr(project, "folder_metadata", {}) or {}
            cron_status = folder_metadata.get("cron_status")
            if cron_status not in ["STARTED", "RUNNING"]:
                detected_2 = True
                desc_2 = f"Scheduler is not running (status={cron_status}). Non-ADHOC tasks require an active scheduler."
            else:
                latest_hb = self._ensure_utc(folder_metadata.get("latest_heartbeat"))
                if latest_hb:
                    scheduler_interval = self.system_config.get("project_scheduler_interval", 5)
                    max_delay = timedelta(seconds=scheduler_interval * 3)
                    if (now - latest_hb) > max_delay:
                        detected_2 = True
                        desc_2 = f"Scheduler heartbeat is stale (last: {latest_hb}). Scheduler may have crashed."
                if not detected_2:
                    desc_2 = "Scheduler is running and healthy."
        diagnostics.append(
            {
                "case_id": 2,
                "title": "Scheduler not running",
                "passed_title": "Scheduler running",
                "description": desc_2,
                "severity": "blocking",
                "detected": detected_2,
            }
        )

        # 3. Pre-action failed
        actions_status = getattr(task, "actions_status", None) or {}
        pre_action_statuses = (
            actions_status.get("pre_actions", []) if isinstance(actions_status, dict) else []
        )
        detected_3 = (
            any(
                (s.get("status") if isinstance(s, dict) else getattr(s, "status", None))
                in ["fail", "error", "failed"]
                for s in pre_action_statuses
            )
            if pre_action_statuses
            else False
        )
        desc_3 = (
            "One or more pre-actions have failed."
            if detected_3
            else "No pre-action failures detected."
        )
        diagnostics.append(
            {
                "case_id": 3,
                "title": "Pre-action failed",
                "passed_title": "Pre-action success",
                "description": desc_3,
                "severity": "blocking",
                "detected": detected_3,
            }
        )

        # 4. State is cancelled
        detected_4 = current_state == "cancelled"
        desc_4 = "Task state is cancelled." if detected_4 else "Task state is not cancelled."
        diagnostics.append(
            {
                "case_id": 4,
                "title": "State is cancelled",
                "passed_title": "State not cancelled",
                "description": desc_4,
                "severity": "blocking",
                "detected": detected_4,
            }
        )

        # 5. User set state is cancel
        user_set_state = getattr(task, "user_set_state", None)
        detected_5 = user_set_state == "cancel"
        desc_5 = (
            "User has requested cancellation (user_set_state=cancel)."
            if detected_5
            else "No user cancellation request."
        )
        diagnostics.append(
            {
                "case_id": 5,
                "title": "User cancellation requested",
                "passed_title": "No user cancellation",
                "description": desc_5,
                "severity": "blocking",
                "detected": detected_5,
            }
        )

        # 6. End date passed
        end_date = self._ensure_utc(getattr(task, "end_date", None))
        detected_6 = end_date is not None and end_date < now
        desc_6 = (
            f"Task end_date ({end_date}) has passed." if detected_6 else "End date has not passed."
        )
        diagnostics.append(
            {
                "case_id": 6,
                "title": "End date passed",
                "passed_title": "Within end date",
                "description": desc_6,
                "severity": "blocking",
                "detected": detected_6,
            }
        )

        # 7. State not schedulable
        schedulable_states = ["scheduled", "success"]
        detected_7 = current_state not in schedulable_states
        desc_7 = (
            f"Task state is '{current_state}', not in schedulable states {schedulable_states}."
            if detected_7
            else "Task state is schedulable."
        )
        diagnostics.append(
            {
                "case_id": 7,
                "title": "State not schedulable",
                "passed_title": "State schedulable",
                "description": desc_7,
                "severity": "warning",
                "detected": detected_7,
            }
        )

        # 8. Required item deleted or missing (operator, connection, payload, workflow, configs)
        missing_items = []
        check_items = {
            "operator": operator_laui,
            "connection": connection_laui,
            "payload": payload_laui,
            "workflow": parent_laui,
        }
        for cfg_i, cfg_laui in enumerate(attached_config_lauis):
            check_items[f"config_{cfg_i}"] = cfg_laui

        for item_label, item_laui_val in check_items.items():
            if not item_laui_val:
                continue
            item_key = str(item_laui_val)
            if item_key not in related_items:
                missing_items.append(f"{item_label} ({item_laui_val})")
        detected_8 = len(missing_items) > 0
        parts_8 = []
        if missing_items:
            parts_8.append(f"Missing: {', '.join(missing_items)}")
        desc_8 = (
            "; ".join(parts_8)
            if detected_8
            else "All required items (operator, connection, payload, workflow, configs) exist and are not deleted."
        )
        diagnostics.append(
            {
                "case_id": 8,
                "title": "Required item deleted or missing",
                "passed_title": "All required items present",
                "description": desc_8,
                "severity": "blocking",
                "detected": detected_8,
            }
        )

        # 9. Stuck in connection queue (stale heartbeat)
        threshold = get_stale_heartbeat_threshold_seconds()
        task_heartbeat = getattr(task, "latest_heartbeat", None)
        detected_9 = (
            cq_entry is not None
            and current_state == "running"
            and is_heartbeat_stale(task_heartbeat, threshold)
        )
        desc_9 = (
            "Task is in connection queue with state=running and a stale heartbeat."
            if detected_9
            else "Task is not stuck in connection queue."
        )
        diagnostics.append(
            {
                "case_id": 9,
                "title": "Stuck in connection queue",
                "passed_title": "Not stuck in connection queue",
                "description": desc_9,
                "severity": "blocking",
                "detected": detected_9,
            }
        )

        # 10. Celery not running
        detected_10 = current_state == "queued_in_redis" and (task_heartbeat is None)
        desc_10 = (
            "Task is queued_in_redis but has no heartbeat — celery may not be running."
            if detected_10
            else "No indication that celery is down."
        )
        diagnostics.append(
            {
                "case_id": 10,
                "title": "Celery not running",
                "passed_title": "Celery running",
                "description": desc_10,
                "severity": "warning",
                "detected": detected_10,
            }
        )

        # 11. Start date in future
        start_date = self._ensure_utc(getattr(task, "start_date", None))
        detected_11 = start_date is not None and start_date > now
        desc_11 = (
            f"Task start_date ({start_date}) is in the future."
            if detected_11
            else "Start date has passed or is not set."
        )
        diagnostics.append(
            {
                "case_id": 11,
                "title": "Start date in future",
                "passed_title": "Start date reached",
                "description": desc_11,
                "severity": "blocking",
                "detected": detected_11,
            }
        )

        # 12. Retry count exceeded
        retry_number = getattr(task, "retry_number", 0) or 0
        total_retries = getattr(task, "total_retries", 0) or 0
        detected_12 = total_retries > 0 and retry_number >= total_retries
        desc_12 = (
            f"Retry count ({retry_number}) has reached max retries ({total_retries})."
            if detected_12
            else "Retry count has not been exceeded."
        )
        diagnostics.append(
            {
                "case_id": 12,
                "title": "Retry count exceeded",
                "passed_title": "Within retry limit",
                "description": desc_12,
                "severity": "blocking",
                "detected": detected_12,
            }
        )

        # 13. Task in fail state
        detected_13 = current_state not in ["scheduled", "success"]
        desc_13 = (
            f"Task is in {current_state} state" if detected_13 else "Task is not in fail state."
        )
        diagnostics.append(
            {
                "case_id": 13,
                "title": "Task in fail state",
                "passed_title": "Task not in fail state",
                "description": desc_13,
                "severity": "blocking",
                "detected": detected_13,
            }
        )

        # 14. Connection-operator mapping invalid
        detected_14 = False
        desc_14 = "Connection-operator mapping check skipped."
        if self.system_config.get("enforce_connection_operator_mapping"):
            if operator_laui and connection_laui:
                op_item = related_items.get(str(operator_laui))
                conn_item = related_items.get(str(connection_laui))
                if (
                    op_item
                    and conn_item
                    and getattr(op_item, "deleted_at", None) is None
                    and getattr(conn_item, "deleted_at", None) is None
                ):
                    try:
                        self.connection_manager.validate_connection_operator_mapping(
                            conn_item, op_item
                        )
                        desc_14 = "Connection-operator mapping is valid."
                    except Exception as e:
                        detected_14 = True
                        desc_14 = f"Connection-operator mapping invalid: {str(e)}"
            else:
                desc_14 = "Cannot validate — operator or connection item not available."
        else:
            desc_14 = "enforce_connection_operator_mapping is disabled."
        diagnostics.append(
            {
                "case_id": 14,
                "title": "Connection-operator mapping invalid",
                "passed_title": "Connection-operator mapping valid",
                "description": desc_14,
                "severity": "blocking",
                "detected": detected_14,
            }
        )

        # 15. Workflow paused
        detected_15 = False
        desc_15 = "Workflow is not paused."
        if parent_laui and str(parent_laui) in related_items:
            workflow_item = related_items[str(parent_laui)]
            workflow_status = getattr(workflow_item, "workflow_status", None)
            if workflow_status == "pause":
                detected_15 = True
                desc_15 = "Parent workflow has user_set_state=pause. Task will not be picked up."
        diagnostics.append(
            {
                "case_id": 15,
                "title": "Workflow paused",
                "passed_title": "Workflow active",
                "description": desc_15,
                "severity": "blocking",
                "detected": detected_15,
            }
        )

        issues_found = sum(1 for d in diagnostics if d["detected"])
        return {
            "task_laui": str(task_laui),
            "task_name": task_name,
            "current_state": current_state,
            "issues_found": issues_found,
            "diagnostics": diagnostics,
        }

    @staticmethod
    def _get_task_delta(original_task: Task, executed_task: Task) -> dict:
        update_fields = {}
        fields_to_check = ["payload", "config"]
        for field in fields_to_check:
            if hasattr(executed_task, field) and hasattr(original_task, field):
                new_value = getattr(executed_task, field)
                old_value = getattr(original_task, field, None)
                if new_value != old_value:
                    update_fields[field] = new_value
        return update_fields


def get_task_manager(request: Request):
    return request.app.state.task_manager
