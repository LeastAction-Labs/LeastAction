# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import traceback
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic_mongo import PydanticObjectId

from src.common.context_vars.user_context import get_user_laui
from src.common.exceptions import InvalidArgumentError, LAException
from src.common.logger.logger import log_error, log_info
from src.core.api.utils import convert_objectid_to_str
from src.core.catalog.api_request import (
    BaseCreateItemRequest,
    CreateLinkRequest,
    DeleteItemRequest,
    GetItemRevisionsRequest,
    GetItemsFilter,
    SearchRequest,
)
from src.core.catalog.bootstrap import bootstrap_project_structure
from src.core.catalog.orchestrator import ItemOrchestrator, get_item_orchestrator
from src.core.ee.keto.access_reader import AccessReader, get_access_reader
from src.core.ee.keto.schema import Permission
from src.core.validation.schema import ValidateCodeblockRequest
from src.core.validation.service import CodeblockValidator, get_codeblock_validator

catalog_router = APIRouter()


@catalog_router.post("/create")
async def create_item(
    item: BaseCreateItemRequest,
    item_orchestrator: ItemOrchestrator = Depends(get_item_orchestrator),
):
    try:
        log_info(
            "api",
            "catalog_router",
            "create_item",
            f"user={get_user_laui()} payload={item.model_dump()}",
        )
        if item.item_type in ["task", "action"]:
            raise InvalidArgumentError(
                "Invalid item type passed",
                f"use /api/v1/{item.item_type} api to create {item.item_type}",
            )
        return await item_orchestrator.create_item(item)
    except LAException as e:
        log_error(
            "api_traceback",
            "catalog_router",
            "create_item",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "catalog_router",
            "create_item",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@catalog_router.post("/validate")
async def validate_codeblock(
    request: ValidateCodeblockRequest,
    validator: CodeblockValidator = Depends(get_codeblock_validator),
):
    try:
        log_info(
            "api",
            "catalog_router",
            "validate_codeblock",
            f"user={get_user_laui()} payload={request.model_dump()}",
        )
        return validator.validate(request.codeblock, request.item_type).model_dump()
    except LAException as e:
        log_error(
            "api",
            "catalog_router",
            "validate_codeblock",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api",
            "catalog_router",
            "validate_codeblock",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@catalog_router.post("/create/link")
async def create_link(
    link: CreateLinkRequest,
    item_orchestrator: ItemOrchestrator = Depends(get_item_orchestrator),
    access_reader: AccessReader = Depends(get_access_reader),
):
    try:
        log_info(
            "api",
            "catalog_router",
            "create_link",
            f"user={get_user_laui()} payload={link.model_dump()}",
        )
        await access_reader.check_item_edit_access(
            item_laui=str(link.parent_laui), user_laui=get_user_laui()
        )
        await access_reader.check_item_view_access(
            item_laui=str(link.child_laui), user_laui=get_user_laui()
        )
        result = await item_orchestrator.create_link(link)
        return result
    except LAException as e:
        log_error(
            "api_traceback",
            "catalog_router",
            "create_link",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "catalog_router",
            "create_link",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@catalog_router.get("/get/tasks_ready_to_run/{project_laui}")
async def get_tasks_ready_to_run(
    project_laui: PydanticObjectId,
    item_orchestrator: ItemOrchestrator = Depends(get_item_orchestrator),
    access_reader: AccessReader = Depends(get_access_reader),
):
    try:
        log_info(
            "api",
            "catalog_router",
            "get_tasks_ready_to_run",
            f"user={get_user_laui()} payload={{project_laui={project_laui}}}",
        )
        await access_reader.check_item_own_access(
            item_laui=str(project_laui), user_laui=get_user_laui()
        )
        return await item_orchestrator.find_tasks_ready_to_run(project_laui=project_laui)
    except LAException as e:
        log_error(
            "api_traceback",
            "catalog_router",
            "get_tasks_ready_to_run",
            f"project_laui={project_laui} LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "catalog_router",
            "get_tasks_ready_to_run",
            f"project_laui={project_laui} unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@catalog_router.get("/get")
async def get_item(
    request: Annotated[GetItemsFilter, Query()],
    item_orchestrator: ItemOrchestrator = Depends(get_item_orchestrator),
    access_reader: AccessReader = Depends(get_access_reader),
):
    try:
        log_info(
            "api",
            "catalog_router",
            "get_item",
            f"user={get_user_laui()} payload={request.model_dump()}",
        )
        if not request.is_root:
            await access_reader.check_item_view_access(
                item_laui=str(request.item_laui), user_laui=get_user_laui()
            )
        return await item_orchestrator.get_items(request=request)
    except LAException as e:
        log_error(
            "api_traceback",
            "catalog_router",
            "get_item",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "catalog_router",
            "get_item",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@catalog_router.get("/get/item_revisions")
async def get_item_revisions(
    request: Annotated[GetItemRevisionsRequest, Query()],
    item_orchestrator: ItemOrchestrator = Depends(get_item_orchestrator),
):
    try:
        log_info(
            "api",
            "catalog_router",
            "get_item_revisions",
            f"user={get_user_laui()} payload={request.model_dump()}",
        )
        return await item_orchestrator.get_item_revisions(request)
    except LAException as e:
        log_error(
            "api_traceback",
            "catalog_router",
            "get_item_revisions",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "catalog_router",
            "get_item_revisions",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


async def _verify_access_for_delete_item(
    request: DeleteItemRequest,
    access_reader: AccessReader = Depends(get_access_reader),
):
    await access_reader.check_item_delete_access(
        item_laui=str(request.item_laui), user_laui=get_user_laui()
    )
    return request


@catalog_router.post("/delete")
async def delete_item(
    request: Annotated[DeleteItemRequest, Depends(_verify_access_for_delete_item)],
    item_orchestrator: ItemOrchestrator = Depends(get_item_orchestrator),
):
    try:
        log_info(
            "api",
            "catalog_router",
            "delete_item",
            f"user={get_user_laui()} payload={request.model_dump()}",
        )
        await item_orchestrator.delete_item(request=request)
        return {"message": "Item deleted successfully"}
    except LAException as e:
        log_error(
            "api_traceback",
            "catalog_router",
            "delete_item",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "catalog_router",
            "delete_item",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@catalog_router.post("/restore/{item_laui}")
async def restore_item(
    item_laui: PydanticObjectId,
    item_orchestrator: ItemOrchestrator = Depends(get_item_orchestrator),
):
    try:
        log_info(
            "api",
            "catalog_router",
            "restore_item",
            f"user={get_user_laui()} payload={{item_laui={item_laui}}}",
        )
        await item_orchestrator.restore_item(item_laui)
        return {"message": "Item restored successfully"}
    except LAException as e:
        log_error(
            "api_traceback",
            "catalog_router",
            "restore_item",
            f"item_laui={item_laui} LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "catalog_router",
            "restore_item",
            f"item_laui={item_laui} unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@catalog_router.post("/search")
async def search(
    request: SearchRequest,
    item_orchestrator: ItemOrchestrator = Depends(get_item_orchestrator),
    access_reader: AccessReader = Depends(get_access_reader),
):
    try:
        log_info(
            "api",
            "catalog_router",
            "search",
            f"user={get_user_laui()} payload={request.model_dump()}",
        )
        response = await item_orchestrator.search(request=request)
        items = response.items
        item_lauis_access = await access_reader.batch_check_permissions(
            permission_to_check=Permission.VIEW,
            item_lauis=[PydanticObjectId(item.laui) for item in items],
            user_laui=get_user_laui(),
        )
        allowed_items = []
        for item, has_item_access in zip(items, item_lauis_access):
            if has_item_access:
                allowed_items.append(item)
        response.items = allowed_items
        return convert_objectid_to_str(response.model_dump())

    except LAException as e:
        log_error(
            "api_traceback",
            "catalog_router",
            "search",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "catalog_router",
            "search",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@catalog_router.get("/item-types/supported-types")
async def get_supported_types(
    item_type: str = Query(...),
    item_orchestrator: ItemOrchestrator = Depends(get_item_orchestrator),
):
    try:
        log_info(
            "api",
            "catalog_router",
            "get_supported_types",
            f"user={get_user_laui()} payload={{item_type={item_type}}}",
        )
        return item_orchestrator.get_supported_types(item_type)
    except LAException as e:
        log_error(
            "api_traceback",
            "catalog_router",
            "get_supported_types",
            f"item_type={item_type} LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "catalog_router",
            "get_supported_types",
            f"item_type={item_type} unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@catalog_router.post("/bootstrap")
async def bootstrap_project(
    project_laui: str,
    item_orchestrator: ItemOrchestrator = Depends(get_item_orchestrator),
    access_reader: AccessReader = Depends(get_access_reader),
):
    try:
        log_info(
            "api",
            "catalog_router",
            "bootstrap_project",
            f"user={get_user_laui()} payload={{project_laui={project_laui}}}",
        )
        await access_reader.check_item_edit_access(
            item_laui=project_laui, user_laui=get_user_laui()
        )
        created_folders = await bootstrap_project_structure(
            project_laui=project_laui,
            item_orchestrator=item_orchestrator,
        )
        return {"project_laui": project_laui, "folders": created_folders}
    except LAException as e:
        log_error(
            "api_traceback",
            "catalog_router",
            "bootstrap_project",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "catalog_router",
            "bootstrap_project",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )
