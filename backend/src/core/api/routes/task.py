# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import traceback
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic_mongo import PydanticObjectId

from src.common.context_vars.user_context import get_user_laui
from src.common.exceptions import LAException
from src.common.logger.logger import log_error, log_info
from src.common.types import AccessPatchType
from src.core.api.dependencies import validate_access_for_create_run
from src.core.catalog.api_request import (
    BaseCreateItemRequest,
    MultipleTaskRequest,
    TaskUpdateRequest,
)
from src.core.catalog.orchestrator import ItemOrchestrator, get_item_orchestrator
from src.core.catalog.service import CatalogService, get_catalog_manager
from src.core.ee.keto.access_reader import AccessReader, get_access_reader
from src.core.ee.keto.schema import Permission
from src.core.task.action.schema import Actions

task_router = APIRouter()


@task_router.post("/run")
async def create_run_task(
    request: Annotated[BaseCreateItemRequest, Depends(validate_access_for_create_run)],
    item_orchestrator: ItemOrchestrator = Depends(get_item_orchestrator),
):
    try:
        log_info(
            "api",
            "task_router",
            "create_run_task",
            f"user={get_user_laui()} payload={request.model_dump()}",
        )
        return await item_orchestrator.create_run_task(request)
    except LAException as e:
        log_error(
            "api_traceback",
            "task_router",
            "create_run_task",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "task_router",
            "create_run_task",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


async def _verify_access_and_attach_tasks(
    request: MultipleTaskRequest,
    catalog_service: CatalogService = Depends(get_catalog_manager),
    access_reader: AccessReader = Depends(get_access_reader),
):
    task_lauis_access = await access_reader.batch_check_permissions(
        permission_to_check=Permission.EDIT,
        item_lauis=request.task_lauis,
        user_laui=get_user_laui(),
    )

    filtered_task_lauis = []

    for task_laui, has_task_access in zip(request.taks_lauis, task_lauis_access):
        if has_task_access:
            filtered_task_lauis.append(task_laui)

    tasks = await catalog_service.find_multiple_items_by_laui(
        item_lauis=filtered_task_lauis,
        projections={},
        include_deleted=False,
    )

    lauis_to_check_for_access = set()

    task_lauis_map = {}

    for task in tasks:
        lauis = [task.operator_laui, task.connection_laui, task.parent_laui]
        if getattr(task, "payload_laui", None):
            lauis.append(task.payload_laui)
        if getattr(task, "actions", None):
            actions = Actions(**task.actions) if isinstance(task.actions, dict) else task.actions
            for action_list in [
                actions.pre_actions,
                actions.create_actions,
                actions.running_actions,
                actions.post_actions,
            ]:
                for action in action_list:
                    lauis.append(action.laui)
        task_lauis_map[task] = lauis
        lauis_to_check_for_access.update(lauis)

    item_lauis_access = await access_reader.batch_check_permissions(
        permission_to_check=Permission.VIEW,
        item_lauis=list(lauis_to_check_for_access),
        user_laui=get_user_laui(),
    )

    item_laui_access_map = dict(zip(lauis_to_check_for_access, item_lauis_access))

    filtered_tasks = []

    for task, lauis in task_lauis_map.items():
        if all([[item_laui_access_map[laui] for laui in lauis]]):
            filtered_tasks.append(task)

    request.tasks = filtered_tasks

    return request


@task_router.post("/multiple_tasks")
async def run_multiple_tasks(
    request: Annotated[MultipleTaskRequest, Depends(_verify_access_and_attach_tasks)],
    item_orchestrator: ItemOrchestrator = Depends(get_item_orchestrator),
):
    try:
        log_info(
            "api",
            "task_router",
            "run_multiple_tasks",
            f"user={get_user_laui()} payload={request.model_dump()}",
        )
        return await item_orchestrator.execute_multiple_tasks(request)
    except LAException as e:
        log_error(
            "api_traceback",
            "task_router",
            "run_multiple_tasks",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "task_router",
            "run_multiple_tasks",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


async def validate_task_access(
    task_laui: PydanticObjectId, access_reader: AccessReader = Depends(get_access_reader)
):
    await access_reader.check_item_edit_access(str(task_laui), get_user_laui())


@task_router.post("/update/{task_laui}")
async def update_task(
    task_laui: PydanticObjectId,
    request: TaskUpdateRequest,
    item_orchestrator: ItemOrchestrator = Depends(get_item_orchestrator),
    _verify_access: None = Depends(validate_task_access),
):
    try:
        log_info(
            "api",
            "task_router",
            "update_task",
            f"user={get_user_laui()} payload={{task_laui={task_laui}, {request.model_dump()}}}",
        )
        return await item_orchestrator.update_task(task_laui, request)
    except LAException as e:
        log_error(
            "api_traceback",
            "task_router",
            "update_task",
            f"task_laui={task_laui} LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "task_router",
            "update_task",
            f"task_laui={task_laui} unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@task_router.post("/finish/{task_laui}")
async def finish_task(
    task_laui: PydanticObjectId,
    item_orchestrator: ItemOrchestrator = Depends(get_item_orchestrator),
    _verify_access: None = Depends(validate_task_access),
):
    try:
        log_info(
            "api",
            "task_router",
            "finish_task",
            f"user={get_user_laui()} payload={{task_laui={task_laui}}}",
        )
        return await item_orchestrator.finish_task(task_laui)
    except LAException as e:
        log_error(
            "api_traceback",
            "task_router",
            "finish_task",
            f"task_laui={task_laui} LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "task_router",
            "finish_task",
            f"task_laui={task_laui} unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@task_router.post("/dangerously_reset/{task_laui}")
async def dangerously_reset_task(
    task_laui: PydanticObjectId,
    item_orchestrator: ItemOrchestrator = Depends(get_item_orchestrator),
    _verify_access: None = Depends(validate_task_access),
):
    try:
        log_info(
            "api",
            "task_router",
            "dangerously_reset_task",
            f"user={get_user_laui()} payload={{task_laui={task_laui}}}",
        )
        return await item_orchestrator.dangerously_reset_task(task_laui)
    except LAException as e:
        log_error(
            "api_traceback",
            "task_router",
            "dangerously_reset_task",
            f"task_laui={task_laui} LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "task_router",
            "dangerously_reset_task",
            f"task_laui={task_laui} unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@task_router.get("/diagnose/{task_laui}")
async def diagnose_task(
    task_laui: PydanticObjectId,
    item_orchestrator: ItemOrchestrator = Depends(get_item_orchestrator),
    _verify_access: None = Depends(validate_task_access),
):
    try:
        log_info(
            "api",
            "task_router",
            "diagnose_task",
            f"user={get_user_laui()} payload={{task_laui={task_laui}}}",
        )
        return await item_orchestrator.get_task_diagnositics(task_laui)
    except LAException as e:
        log_error(
            "api_traceback",
            "task_router",
            "diagnose_task",
            f"task_laui={task_laui} LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "task_router",
            "diagnose_task",
            f"task_laui={task_laui} unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )
