# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from fastapi import Request
from pydantic_mongo import PydanticObjectId

from src.common.context_vars.session_context import get_session_id
from src.common.exceptions import UnprocessableEntityError
from src.common.mutex import lock_pk
from src.core.api.utils import convert_objectid_to_str
from src.core.catalog.api_request import (
    BaseCreateItemRequest,
    CreateItemResponse,
    CreateLinkRequest,
    CreateLinkResponse,
    DeleteItemRequest,
    GetItemRevisionsRequest,
    GetItemsFilter,
    MultipleTaskRequest,
    MultipleTaskResponse,
    SearchItemsFilter,
    SearchItemsResponse,
    SearchRequest,
    TaskUpdateRequest,
)
from src.core.catalog.service import CatalogService
from src.core.task.action.pre_action_manager import PreActionManager
from src.core.task.action.schema import ActionItem, Actions
from src.core.task.connection.connection_queue_manager import ConnectionQueueManager
from src.core.task.schema import Task, TaskCreationValidationModel, TaskState, TaskValidationModel
from src.core.task.task_manager import TaskManager
from src.core.validation.service import CodeblockValidator
from src.core.version_manager.service import VersionManager


class ItemOrchestrator:
    def __init__(
        self,
        task_manager: TaskManager,
        catalog_service: CatalogService,
        pre_action_manager: PreActionManager,
        connection_queue_manager: ConnectionQueueManager,
        codeblock_validator: CodeblockValidator,
        version_manager: VersionManager,
    ) -> None:
        self.task_manager = task_manager
        self.catalog_service = catalog_service
        self.pre_action_manager = pre_action_manager
        self.connection_queue_manager = connection_queue_manager
        self.codeblock_validator = codeblock_validator
        self.version_manager = version_manager

    async def create_item(self, request: BaseCreateItemRequest) -> CreateItemResponse:
        pk = self.catalog_service._build_pk(
            item=request, schema_manager=self.catalog_service._get_schema_manager(request.item_type)
        )
        async with lock_pk(pk):
            existing_item = await self.catalog_service.find_existing_item_by_pk(item=request)
            if existing_item:
                item_model = self.catalog_service.validate_item_schema(request, exclude_unset=True)
            else:
                item_model = self.catalog_service.validate_item_schema(request)

            if getattr(item_model, "status", None) == "deprecated":
                raise UnprocessableEntityError(
                    message="Item is deprecated",
                    detail="You cannot import or create this item because it is marked as deprecated.",
                )

            version_compatibility = getattr(item_model, "version_compatibility", None)
            if version_compatibility:
                patterns = (
                    version_compatibility.get("core", [])
                    if isinstance(version_compatibility, dict)
                    else version_compatibility
                )
                self.version_manager.check_compatibility(patterns)

            # Safety-net codeblock validation for operators and actions.
            # Covers new creates, updates that change the codeblock, and skips updates that don't touch it
            # (exclude_unset=True drops absent fields, so getattr returns None).
            base_type = (item_model.item_type).split(".")[0]
            if base_type in ("operator", "action"):
                codeblock = getattr(item_model, "codeblock", None)
                if codeblock:
                    result = self.codeblock_validator.validate(codeblock, item_model.item_type)
                    if not result.valid:
                        raise UnprocessableEntityError(
                            message="Codeblock validation failed",
                            detail=f"The code block has errors or warnings. Errors: {[e.model_dump() for e in result.errors]}, Warnings: {[w.model_dump() for w in result.warnings]}.",
                        )
                    item_model.validation_results = result.model_dump()

            if item_model.item_type == "task":
                task_data = TaskCreationValidationModel(**item_model.model_dump())
                item_model = await self.task_manager.validate_task_creation(task_data)

            if existing_item:
                await self.catalog_service.update_existing_item(
                    new_item=item_model, existing_item=existing_item
                )
                return CreateItemResponse(item_laui=str(existing_item.laui))

            item_laui = await self.catalog_service.create_item(item_model)
            if item_model.item_type == "task":
                await self._link_tasks(task_laui=item_laui, task_data=task_data)
            return CreateItemResponse(item_laui=str(item_laui))

    async def update_task(self, task_laui: PydanticObjectId, request: TaskUpdateRequest):
        update_dict = request.model_dump(exclude_none=True, mode="python")
        updated_laui = await self.catalog_service.update_task_item(task_laui, update_dict)
        return CreateItemResponse(item_laui=str(updated_laui))

    async def delete_item(self, request: DeleteItemRequest):
        await self.catalog_service.delete_item(request=request)

    async def restore_item(self, item_laui: PydanticObjectId):
        await self.catalog_service.restore_item(item_laui)

    async def get_items(self, request: GetItemsFilter):
        if request.only_item_laui_passed:
            item = await self.catalog_service.find_item(
                item_laui=ObjectId(request.item_laui), include_deleted=request.is_deleted
            )
            item_dict = item.model_dump(mode="python", by_alias=True)
            return convert_objectid_to_str(item_dict)
        result = await self.catalog_service.find_items(request)
        return convert_objectid_to_str(result.model_dump())

    async def search(self, request: SearchRequest) -> SearchItemsResponse:
        print(request)
        result = await self.catalog_service.search(request)
        return convert_objectid_to_str(result.model_dump())

    async def create_link(self, request: CreateLinkRequest):
        id: PydanticObjectId = await self.catalog_service.create_link(request)
        return CreateLinkResponse(link_laui=str(id))

    async def get_item_revisions(self, request: GetItemRevisionsRequest):
        result = await self.catalog_service.get_item_revisions(request)
        return convert_objectid_to_str(result.model_dump())

    async def find_tasks_ready_to_run(self, project_laui: PydanticObjectId):
        tasks = await self.catalog_service.find_tasks_ready_to_run(project_laui=project_laui)
        tasks_dict = [task.model_dump(mode="python", by_alias=True) for task in tasks]
        return convert_objectid_to_str(tasks_dict)

    async def create_run_task(self, request: BaseCreateItemRequest) -> CreateItemResponse:
        task_item = None
        task_laui = None
        item_laui = getattr(request, "item_laui", None)
        if item_laui:
            task_laui = item_laui
            task_item = await self.catalog_service.find_item(
                item_laui=ObjectId(task_laui), include_deleted=False
            )
            if task_item.item_type != "task":
                raise UnprocessableEntityError(
                    message="Cannot run this item",
                    detail=f"The item at '{item_laui}' is a '{task_item.item_type}'. You can only run 'task' items.",
                )
        else:
            if request.item_type != "task":
                raise UnprocessableEntityError(
                    message="Cannot run this item",
                    detail=f"You requested a '{request.item_type}', but you can only run 'task' items.",
                )
            create_response = await self.create_item(request)
            task_laui = create_response.item_laui
            task_item = await self.catalog_service.find_item(
                item_laui=ObjectId(task_laui), include_deleted=False
            )

        task_item.last_run_session_id = get_session_id()
        task_item.user_set_state = None
        task_update_data = {"user_set_state": None}
        if getattr(request, "logical_date", None):
            task_item.logical_date = request.logical_date
            task_update_data["logical_date"] = request.logical_date
        await self.catalog_service.update_task_item(task_laui, task_update_data)
        await self.task_manager.execute_tasks([task_item])
        return CreateItemResponse(item_laui=task_item.laui)

    async def execute_multiple_tasks(self, request: MultipleTaskRequest) -> MultipleTaskResponse:
        tasks = await self.catalog_service.find_multiple_items_by_laui(
            item_lauis=request.task_lauis, projections={}
        )
        for task in tasks:
            task.last_run_session_id = get_session_id()

        task_results = await self.task_manager.execute_tasks(request.tasks)
        return MultipleTaskResponse(task_results=task_results["task_results"])

    async def execute_action(self, request: BaseCreateItemRequest) -> dict[str, Any]:
        action_item = None
        action_laui = None
        action_variables = getattr(request, "action_variables", None)
        connection_laui = getattr(request, "connection_laui", None)
        item_laui = getattr(request, "item_laui", None)
        if item_laui:
            action_laui = item_laui
            action_item = await self.catalog_service.find_item(
                item_laui=ObjectId(action_laui), include_deleted=False
            )
            if action_item.item_type.split(".")[0] != "action":
                raise UnprocessableEntityError(
                    message="Cannot run this item",
                    detail=f"Item '{item_laui}' is a '{action_item.item_type}' and cannot be run. Only 'action' items are supported.",
                )
            if request.item_type.split(".")[0] != "action":
                raise UnprocessableEntityError(
                    message="Item type mismatch",
                    detail=f"The request type must be an 'action', but got '{request.item_type}' instead.",
                )
        else:
            if request.item_type.split(".")[0] != "action":
                raise UnprocessableEntityError(
                    message="Cannot run this item",
                    detail=f"The type '{request.item_type}' cannot be run. Only 'action' items are supported.",
                )
            create_response = await self.create_item(request)
            action_laui = create_response.item_laui
            action_item = await self.catalog_service.find_item(
                item_laui=ObjectId(action_laui), include_deleted=False
            )

        user_laui = (
            str(action_item.updated_by) if action_item.updated_by else str(action_item.created_by)
        )
        action = ActionItem(
            laui=action_laui,
            name=action_item.name,
            session_id=get_session_id(),
            connection_laui=connection_laui,
            action_variables=action_variables,
        )
        res = await self.pre_action_manager.create_actions(
            Actions(create_actions=[action]), user_laui
        )
        return {"result": res}

    async def finish_task(self, task_laui: PydanticObjectId):
        task = await self.catalog_service.find_item(item_laui=task_laui)
        await self.connection_queue_manager.dequeue_task(task)

    async def dangerously_reset_task(self, task_laui: PydanticObjectId):
        task = await self.catalog_service.find_item(item_laui=task_laui)
        previous_state = task.state

        task_for_queue = TaskValidationModel(**task.model_dump())
        cq = await self.connection_queue_manager.get_connection_queue(task_for_queue)

        removed_from_queue = False
        queue_message = None
        if not cq:
            queue_message = "Task was not present in the connection queue"
        else:
            await self.connection_queue_manager.dequeue_task(task_for_queue)
            removed_from_queue = True

        update_dict = {
            "state": TaskState.SCHEDULED,
            "last_run_output": {},
            "user_set_state": None,
            "actions_status": {"pre_actions": [], "running_actions": [], "post_actions": []},
            "last_system_updated_date": datetime.now(UTC),
        }
        if task_for_queue.frequency == "ADHOC":
            update_dict["state"] = TaskState.CREATED
        await self.catalog_service.update_task_item(task_laui, update_dict)
        response = {
            "task_laui": str(task_laui),
            "removed_from_queue": removed_from_queue,
            "previous_state": previous_state,
        }
        if queue_message:
            response["message"] = queue_message
        return response

    async def get_task_diagnositics(self, task_laui: PydanticObjectId):
        return await self.task_manager.diagnose_task(task_laui)

    def get_supported_types(self, item_type: str) -> dict:
        return {
            "supported_children_types": self.catalog_service.get_supported_children_types(
                item_type
            ),
            "supported_parent_types": self.catalog_service.get_supported_parent_types(item_type),
        }

    @staticmethod
    def _get_task_delta(original_task: Task, executed_task: Task) -> dict:
        update_fields = {}
        fields_to_check = executed_task.model_fields.keys()
        for field in fields_to_check:
            if field in ["connection", "last_system_updated_date"]:
                continue
            if hasattr(executed_task, field) and hasattr(original_task, field):
                new_value = getattr(executed_task, field)
                old_value = getattr(original_task, field)
                if new_value != old_value:
                    update_fields[field] = new_value

        return update_fields

    async def _link_tasks(
        self, task_laui: PydanticObjectId, task_data: TaskCreationValidationModel
    ):
        actions = task_data.actions
        if not actions:
            return
        if isinstance(actions, dict):
            actions = Actions(**actions)
        if not actions.pre_actions:
            return
        for action in actions.pre_actions:
            if action.name == "LeastActionCheckIfAreParentsDone":
                try:
                    parent_tasks = action.action_variables.get("parents")
                except AttributeError:
                    raise UnprocessableEntityError(
                        message="Missing parents parameter",
                        detail="The action 'LeastActionCheckIfAreParentsDone' failed because no 'parents' field was provided.",
                    )
                for parent_task in parent_tasks:
                    try:
                        parent_task_laui = await self._get_parent_task_laui(parent_task, task_data)
                        await self.catalog_service.link_tasks(parent_task_laui, task_laui)
                    except Exception as e:
                        raise UnprocessableEntityError(
                            message="Failed to link tasks",
                            detail=f"Could not link this task to its parent task. Error details: {str(e)}.",
                        )

    async def _get_parent_task_laui(
        self, parent_task: dict, child_task: TaskCreationValidationModel
    ) -> str:
        task_name = parent_task.get("task_name", "")
        search_filter = SearchItemsFilter(
            item_type="task",
            name=task_name,
            project_laui=child_task.project_laui,
            account_laui=child_task.account_laui,
            partition=child_task.partition,
            get_by_pk=True,
        )
        search_request = SearchRequest(item_filter=search_filter)
        try:
            result = await self.catalog_service.search(search_request)
        except Exception:
            raise
        if not result.items:
            raise UnprocessableEntityError(
                message="Parent task not found",
                detail=f"The parent task dependency named '{task_name}' could not be found in this project.",
            )

        parent_laui = str(result.items[0].laui)
        return parent_laui


def get_item_orchestrator(request: Request):
    return request.app.state.item_orchestrator
