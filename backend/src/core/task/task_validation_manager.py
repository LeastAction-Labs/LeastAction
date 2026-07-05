# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from pydantic_mongo import PydanticObjectId

from src.common.exceptions import TaskValidationError, UnprocessableEntityError
from src.core.catalog.api_request import GetItemsFilter
from src.core.catalog.item.schema import ItemProjection
from src.core.catalog.service import CatalogService
from src.core.catalog.utils.item_types.service import ItemTypesManager
from src.core.task.action.schema import Actions
from src.core.task.config.config_manager import ConfigManager
from src.core.task.connection.connection_manager import ConnectionManager
from src.core.task.schema import TaskCreationValidationModel, TaskState, TaskValidationModel


class TaskValidationManager:
    def __init__(
        self,
        connection_manager: ConnectionManager,
        config_manager: ConfigManager,
        catalog_manager: CatalogService,
        item_types_manager: ItemTypesManager,
    ):
        self.connection_manager = connection_manager
        self.config_manager = config_manager
        self.catalog_manager = catalog_manager
        self.item_types_manager = item_types_manager

    async def validate_task_creation(
        self, task_data: TaskCreationValidationModel
    ) -> TaskCreationValidationModel:
        """
        Validates a task for creation.
        Returns the validated task data with merged config and parsed payload.
        """
        operator_laui = task_data.operator_laui
        payload_laui = task_data.payload_laui
        workflow_laui = task_data.parent_laui
        connection_laui = task_data.connection_laui
        frequency = task_data.frequency

        # If task has direct payload text but no payload_laui, clear payload_laui to ""
        if task_data.payload and not payload_laui:
            task_data.payload_laui = None
            payload_laui = None

        errors = []

        # Validate frequency and dates
        self._validate_frequency(frequency, errors)
        self._validate_dates(frequency, task_data.start_date, task_data.end_date, errors)

        # Set logical_date based on task type
        if frequency == "ADHOC":
            # For ADHOC tasks, use user-provided logical_date or fallback to current time
            if not task_data.logical_date:
                task_data.logical_date = datetime.now(UTC)
        else:
            if not task_data.logical_date:
                task_data.logical_date = task_data.start_date
            task_data.state = TaskState.SCHEDULED

        # Set next_run_date: start_date if provided, else current UTC time.
        # Preserve an already-set value (e.g. carried over from an existing task on
        # update) so scheduling progress is not rewound to start_date.
        if not task_data.next_run_date:
            task_data.next_run_date = (
                task_data.start_date if task_data.start_date else datetime.now(UTC)
            )

        action_lauis = []
        if task_data.actions:
            actions = (
                Actions(**task_data.actions)
                if isinstance(task_data.actions, dict)
                else task_data.actions
            )
            for action in actions.pre_actions:
                action_lauis.append(action.laui)
            for action in actions.create_actions:
                action_lauis.append(action.laui)
            for action in actions.running_actions:
                action_lauis.append(action.laui)
            for action in actions.post_actions:
                action_lauis.append(action.laui)

        # Batch fetch all items (with full projections to get content for payload)
        item_lauis = [operator_laui, connection_laui, workflow_laui]
        item_lauis.extend(action_lauis)
        if payload_laui:
            item_lauis.append(payload_laui)

        items_map = await self._get_multiple_non_deleted_items(
            item_lauis, errors, projections={"item_type": 1, "name": 1}
        )

        # Validate item types
        operator = None
        connection = None
        if operator_laui in items_map:
            operator = items_map[operator_laui]
            self._validate_item_type(operator, "operator", operator_laui, errors)
        else:
            errors.append(f"Operator item not found: {operator_laui}")

        if connection_laui in items_map:
            connection = items_map[connection_laui]
            self._validate_item_type(connection, "connection", connection_laui, errors)
        else:
            errors.append(f"Connection item not found: {connection_laui}")

        if workflow_laui in items_map:
            workflow = items_map[workflow_laui]
            self._validate_workflow_item_type(workflow, errors)
        else:
            errors.append(f"Workflow item not found: {workflow_laui}")

        if payload_laui and payload_laui in items_map:
            payload_item = items_map[payload_laui]
            self._validate_item_type(payload_item, "payload", payload_laui, errors)

        # Validate action item types and set action names
        for action_laui in action_lauis:
            if action_laui in items_map:
                action_item = items_map[action_laui]
                self._validate_item_type(action_item, "action", action_laui, errors)

        if task_data.actions:
            actions = (
                Actions(**task_data.actions)
                if isinstance(task_data.actions, dict)
                else task_data.actions
            )
            for action_list in [
                actions.pre_actions,
                actions.create_actions,
                actions.running_actions,
                actions.post_actions,
            ]:
                for action in action_list:
                    if action.laui in items_map:
                        action.name = items_map[action.laui].name
            task_data.actions = actions.model_dump()

        # Validate connection-operator mapping if both are valid
        if operator and connection and not errors:
            try:
                self.connection_manager.validate_connection_operator_mapping(connection, operator)
            except Exception as e:
                errors.append(str(e))

        # Raise all errors together
        if errors:
            raise UnprocessableEntityError(
                message="Task validation failed",
                detail=f"We found some problems with your task configurations: {'; '.join(errors)}.",
            )

        # All validations passed, now get merged config and replace placeholders
        task_data.config = await self._get_merged_config(task_data)

        # Use task-level retry fields if explicitly set, otherwise fall back to config.
        # Config retry values may live at top level (e.g. {"total_retries": 3}) or nested
        # under defaults.task (e.g. {"defaults": {"task": {"total_retries": 3}}}); check both.
        config_defaults_task = task_data.config.get("defaults", {}).get("task", {})
        task_data.total_retries = (
            task_data.total_retries
            if task_data.total_retries
            else (
                task_data.config.get("total_retries")
                or config_defaults_task.get("total_retries", 0)
            )
        )
        task_data.retry_interval = (
            task_data.retry_interval
            if task_data.retry_interval
            else (
                task_data.config.get("retry_interval")
                or config_defaults_task.get("retry_interval", 0)
            )
        )

        # TODO : Create time placeholder replacement
        # task_data.payload = self._parse_payload(
        #     task_data.config,
        #     items_map,
        #     payload=payload,
        #     payload_laui=payload_laui,
        # )

        return task_data

    async def validate_task_execution(
        self, tasks: list[TaskValidationModel]
    ) -> list[TaskValidationModel]:
        """
        Validates multiple tasks for execution.
        Returns a list of validated tasks, excluding any that fail validation.
        """
        if not tasks:
            return []

        try:
            all_item_lauis = set()
            for task in tasks:
                all_item_lauis.add(task.operator_laui)
                all_item_lauis.add(task.connection_laui)
                all_item_lauis.add(task.parent_laui)

                if task.payload_laui:
                    all_item_lauis.add(task.payload_laui)
            errors = []
            # Fetch items with specific fields needed for validation
            # Include content field for payload items, codeblock for operators, etc.
            projection_fields = {
                "item_type": 1,
                "content": 1,  # For payload items
                "attached_config_lauis": 1,  # For workflow/config items
            }
            all_items = await self._get_multiple_non_deleted_items(
                list(all_item_lauis), errors, projections=projection_fields
            )

            # Collect TaskValidationErrors and log them
            if errors:
                validation_error = TaskValidationError(
                    f"Errors fetching items: {'; '.join(errors)}"
                )

            # Validate and build final task list
            final_tasks = []
            for task in tasks:
                try:
                    validated_task = self._validate_individual_task_execution(all_items, task)
                    if validated_task:
                        final_tasks.append(validated_task)
                except TaskValidationError:
                    pass
                except Exception:
                    raise

            return final_tasks

        except TaskValidationError:
            return []
        except Exception:
            raise

    def _validate_workflow_item_type(self, item: ItemProjection, errors: list[str]) -> None:
        supported_types = self.item_types_manager.get_supported_item_types(item.item_type)
        if "task" not in supported_types:
            errors.append(
                f"Invalid item_type task for workflow. Supported types: {supported_types}"
            )

    @staticmethod
    def _validate_payload_constraints(
        items: dict[ObjectId, ItemProjection],
        task_data: TaskValidationModel,
    ) -> TaskValidationModel:
        if task_data.payload_laui:
            payload_item = items[ObjectId(task_data.payload_laui)]
            if payload_item is not None:
                task_data.payload = payload_item.content

        return task_data

    def _validate_frequency(self, frequency: str, errors: list[str]) -> None:
        if frequency == "ADHOC":
            return

        if not self._is_valid_cron(frequency):
            errors.append(f"Invalid cron expression: {frequency}")

    @staticmethod
    def _validate_dates(
        frequency: str,
        start_date: datetime | None,
        end_date: datetime | None,
        errors: list[str],
    ) -> None:
        if frequency == "ADHOC":
            if start_date:
                errors.append("start_date cannot be set for ADHOC tasks")
            return

        if not start_date:
            errors.append("start_date is required for scheduled tasks")
            return
        if end_date and end_date < start_date:
            errors.append("end_date must be greater than or equal to start_date")

    @staticmethod
    def _validate_item_type(
        item: ItemProjection,
        expected_type: str,
        item_laui: PydanticObjectId,
        errors: list[str],
    ) -> None:
        item_type = item.item_type.split(".")[0]
        if item_type != expected_type:
            errors.append(
                f"Item {item_laui} is not of type {expected_type}, found {item_type} instead"
            )

    @staticmethod
    def _validate_all_items_exists(items: dict, task: TaskValidationModel) -> bool:
        # TODO validate item type for each, if updation is allowed after task creation
        if ObjectId(task.operator_laui) not in items:
            return False
        if ObjectId(task.parent_laui) not in items:
            return False
        return ObjectId(task.connection_laui) in items

    def _validate_individual_task_execution(
        self, items: dict, task: TaskValidationModel
    ) -> TaskValidationModel | None:
        if not self._validate_all_items_exists(items, task):
            return []
        task = self._validate_payload_constraints(items, task)
        if task.operator_laui and task.connection_laui:
            try:
                self.connection_manager.validate_connection_operator_mapping(
                    items[ObjectId(task.connection_laui)], items[ObjectId(task.operator_laui)]
                )
            except Exception:
                return []

        final_task = self.config_manager.process_task_execution(task, "actions")
        final_task.connection = items[ObjectId(task.connection_laui)]
        return final_task

    @staticmethod
    def _is_valid_cron(cron_expr: str) -> bool:
        parts = cron_expr.split()
        return len(parts) == 5

    def _parse_payload(
        self,
        config: dict[str, Any],
        items_map: dict[ObjectId, ItemProjection],
        payload: str = None,
        payload_laui: ObjectId = None,
    ) -> str | None:
        """Parse and return the payload with placeholders replaced"""
        # Get builtin system variables
        builtin_vars = self.config_manager.get_builtin_variables()

        # Extract parameters from config and combine with builtin vars
        config_parameters = config.get("parameters", {})
        all_parameters = {**config_parameters, **builtin_vars}

        if payload_laui and payload_laui in items_map:
            payload_item = items_map[payload_laui]
            payload_content = getattr(payload_item, "content", "")
            result = self.config_manager.replace_placeholders(payload_content, all_parameters)
            return result
        elif payload:
            result = self.config_manager.replace_placeholders(payload, all_parameters)
            return result
        else:
            return None

    async def _get_multiple_non_deleted_items(
        self,
        item_lauis: list[PydanticObjectId],
        errors: list[str],
        projections: dict[str, int] = None,
    ) -> dict[PydanticObjectId, ItemProjection]:
        if projections is None:
            projections = {"item_type": 1}
        if not item_lauis:
            return {}
        try:
            # Filter out None values
            valid_lauis = [item_laui for item_laui in item_lauis if item_laui is not None]

            if not valid_lauis:
                return {}

            items = await self.catalog_manager.find_multiple_items_by_laui(
                item_lauis=valid_lauis,
                projections=projections,
                include_deleted=False,
            )

            # Create a map of found items
            items_map = {ObjectId(item.laui): item for item in items}

            # Check for missing items and add errors
            for item_laui in valid_lauis:
                if item_laui not in items_map:
                    errors.append(f"Item with laui {item_laui} not found")

            return items_map

        except Exception as e:
            errors.append(f"Failed to fetch items: {str(e)}")
            return {}

    async def _get_all_attached_configs(self, task_data: TaskValidationModel) -> dict[str, Any]:
        # Get task config IDs
        task_config_lauis = task_data.attached_config_lauis or []

        # Get workflow configs (configs that are children of the workflow)
        workflow_laui = task_data.parent_laui
        workflow_config_response = await self.catalog_manager.find_items(
            GetItemsFilter(
                item_laui=PydanticObjectId(workflow_laui),
                item_type="config",
                parent_or_child="child",
                per_page=100,
            )
        )
        workflow_config_items = [node.item for node in workflow_config_response.items]

        if not task_config_lauis and not workflow_config_items:
            return {"task_configs": [], "workflow_configs": []}

        # Validate task config IDs format and convert to PydanticObjectId
        errors = []
        try:
            task_config_lauis = [PydanticObjectId(config_laui) for config_laui in task_config_lauis]
        except Exception as e:
            raise UnprocessableEntityError(f"Invalid ID format in attached_config_lauis: {str(e)}")

        # Fetch task configs in batch (with full projections to get content field)
        task_configs = []
        if task_config_lauis:
            configs_map = await self._get_multiple_non_deleted_items(
                task_config_lauis, errors, projections={}
            )

            # Validate all are configs
            for config_laui in task_config_lauis:
                if config_laui in configs_map:
                    self._validate_item_type(
                        configs_map[config_laui], "config", config_laui, errors
                    )

            if errors:
                raise UnprocessableEntityError(
                    message="Config verification failed",
                    detail=f"config lookup issues: {'; '.join(errors)}.",
                )

            for config_laui in task_config_lauis:
                if config_laui in configs_map:
                    task_configs.append(configs_map[config_laui].model_dump())

        # Workflow configs are already fetched via find_items
        workflow_configs = [item.model_dump() for item in workflow_config_items]

        return {
            "task_configs": task_configs,
            "workflow_configs": workflow_configs,
        }

    async def _get_merged_config(self, task_data: TaskValidationModel) -> dict[str, Any]:
        configs_data = await self._get_all_attached_configs(task_data)
        merge_result = self.config_manager.merge_configs(task_data.config, configs_data)
        merged_config = merge_result["merged_config"]
        return merged_config
