# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import traceback
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from src.common.context_vars.user_context import get_user_laui
from src.common.exceptions import LAException
from src.common.logger.logger import log_error, log_info
from src.core.ee.keto.access_reader import AccessReader, get_access_reader
from src.core.ee.keto.api_request import GetAccessRelationsRequest, GetPermissionRequest

access_router = APIRouter()


@access_router.get("/get/permission")
async def get_permission(
    request: Annotated[GetPermissionRequest, Query()],
    access_reader: AccessReader = Depends(get_access_reader),
):
    """group laui will override user_laui in case both are passed"""
    try:
        log_info(
            "api",
            "access_router",
            "get_permission",
            f"user={get_user_laui()} payload={request.model_dump()}",
        )
        permission: str = await access_reader.get_permission(
            item_laui=request.item_laui, user_laui=request.user_laui, group_laui=request.group_laui
        )
        return {
            "permission": permission if permission else "none",
            "user_laui": request.user_laui,
            "group_laui": request.group_laui,
        }
    except LAException as e:
        log_error(
            "api_traceback",
            "access_router",
            "get_permission",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "access_router",
            "get_permission",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@access_router.get("/get/access_relations")
async def get_access_relations(
    request: Annotated[GetAccessRelationsRequest, Query()],
    access_reader: AccessReader = Depends(get_access_reader),
):
    try:
        log_info(
            "api",
            "access_router",
            "get_access_relations",
            f"user={get_user_laui()} payload={request.model_dump()}",
        )
        return await access_reader.get_all_access_relations(
            user_laui=get_user_laui(), request=request
        )
    except LAException as e:
        log_error(
            "api_traceback",
            "access_router",
            "get_access_relations",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "access_router",
            "get_access_relations",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )
