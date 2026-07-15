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
from src.common.exceptions import LAException
from src.common.logger.logger import log_error, log_info
from src.core.ee.group.api_request import GetGroupsRequest, SearchGroupsRequest
from src.core.ee.group.schema import CreateGroup
from src.core.ee.group.service import GroupService, get_group_service
from src.core.ee.keto.schema import Relation

group_router = APIRouter()


@group_router.post("/create")
async def create_group(
    group: CreateGroup, group_service: GroupService = Depends(get_group_service)
):
    try:
        log_info(
            "api",
            "group_router",
            "create_group",
            f"user={get_user_laui()} payload={group.model_dump()}",
        )
        return await group_service.create_group(group=group)
    except LAException as e:
        log_error(
            "api_traceback",
            "group_router",
            "create_group",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "group_router",
            "create_group",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@group_router.get("/get")
async def get_groups(
    request: Annotated[GetGroupsRequest, Query()],
    group_service: GroupService = Depends(get_group_service),
):
    try:
        log_info(
            "api",
            "group_router",
            "get_groups",
            f"user={get_user_laui()} payload={request.model_dump()}",
        )
        return await group_service.get_groups(request)
    except LAException as e:
        log_error(
            "api_traceback",
            "group_router",
            "get_groups",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "group_router",
            "get_groups",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@group_router.get("/get/{group_laui}")
async def get_group(
    group_laui: PydanticObjectId,
    group_service: GroupService = Depends(get_group_service),
):
    try:
        log_info(
            "api",
            "group_router",
            "get_group",
            f"user={get_user_laui()} payload={{group_laui={group_laui}}}",
        )
        return await group_service.get_group(group_laui)
    except LAException as e:
        log_error(
            "api_traceback",
            "group_router",
            "get_group",
            f"group_laui={group_laui} LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "group_router",
            "get_group",
            f"group_laui={group_laui} unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@group_router.delete("/delete")
async def delete_group(
    group_laui: PydanticObjectId,
    group_service: GroupService = Depends(get_group_service),
):
    try:
        log_info(
            "api",
            "group_router",
            "delete_group",
            f"user={get_user_laui()} payload={{group_laui={group_laui}}}",
        )
        await group_service.delete_group(
            group_laui=group_laui,
        )
    except LAException as e:
        log_error(
            "api_traceback",
            "group_router",
            "delete_group",
            f"group_laui={group_laui} LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "group_router",
            "delete_group",
            f"group_laui={group_laui} unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@group_router.post("/search")
async def search_groups(
    request: SearchGroupsRequest, group_service: GroupService = Depends(get_group_service)
):
    try:
        log_info(
            "api",
            "group_router",
            "search_groups",
            f"user={get_user_laui()} payload={request.model_dump()}",
        )
        return await group_service.search_groups(request)
    except LAException as e:
        log_error(
            "api_traceback",
            "group_router",
            "search_groups",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "group_router",
            "search_groups",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )
