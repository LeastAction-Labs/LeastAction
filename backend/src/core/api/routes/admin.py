# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import traceback
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic_mongo import PydanticObjectId

from src.common.context_vars.user_context import get_root_user_laui, get_user_laui
from src.common.exceptions import InvalidArgumentError, LAException
from src.common.logger.logger import log_debug, log_error, log_info
from src.common.utils import load_system_config, update_system_config
from src.core.admin.api_request import (
    AdminCreateUserRequest,
    GetSystemAttributesResponse,
    GetUsersRequest,
    UpdateSystemAttributesRequest,
    UpdateUserPayload,
)
from src.core.admin.service import AdminService, get_admin_service
from src.core.ee.iam.user.service import UserService, get_user_service
from src.core.mcp.server import ALL_MCP_TOOLS, MCP_TOOL_GROUPS

admin_router = APIRouter()


@admin_router.get("/get/system")
def get_system_details():
    try:
        log_info(
            "api",
            "admin_router",
            "get_system_details",
            f"user={get_user_laui()}",
        )
        config = load_system_config()
        return GetSystemAttributesResponse(
            sso_enabled=config.get("sso_enabled", False),
            instance_laui=get_root_user_laui(),
            totp_enabled=config.get("totp_enabled", False),
        )
    except LAException as e:
        log_error(
            "api_traceback",
            "admin_router",
            "get_system_details",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "admin_router",
            "get_system_details",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@admin_router.post("/update/system")
def update_system_attributes(request: UpdateSystemAttributesRequest):
    try:
        update_system_config(request.model_dump())
    except LAException as e:
        log_error(
            "api_traceback",
            "admin_router",
            "update_system_attributes",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "admin_router",
            "update_system_attributes",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


from src.core.api.routes.license import license_router

admin_router.include_router(license_router, prefix="/license")


@admin_router.post("/user/create")
async def admin_create_user(
    request: AdminCreateUserRequest, admin_service: AdminService = Depends(get_admin_service)
):
    """Admin creates a user. Returns a temporary password to hand to the user."""
    try:
        log_info(
            "api",
            "admin_router",
            "admin_create_user",
            f"user={get_user_laui()} payload={request.model_dump()}",
        )
        config = load_system_config()
        if config.get("sso_enabled"):
            raise InvalidArgumentError("SSO is enabled. User creation is not allowed.")
        return await admin_service.create_user(request)
    except LAException as e:
        log_error(
            "api_traceback",
            "admin_router",
            "admin_create_user",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "admin_router",
            "admin_create_user",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@admin_router.get("/user/list")
async def admin_list_users(
    request: Annotated[GetUsersRequest, Query()],
    user_service: UserService = Depends(get_user_service),
):
    try:
        log_info(
            "api",
            "admin_router",
            "admin_list_users",
            f"user={get_user_laui()} payload={request.model_dump()}",
        )
        return await user_service.get_users(request)
    except LAException as e:
        log_error(
            "api_traceback",
            "admin_router",
            "admin_list_users",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "admin_router",
            "admin_list_users",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@admin_router.get("/mcp-tools")
async def get_all_mcp_tools():
    """Return the canonical list of all available MCP tool names."""
    try:
        log_info("api", "admin_router", "get_all_mcp_tools", f"user={get_user_laui()} payload={{}}")
        return {"tools": ALL_MCP_TOOLS, "groups": MCP_TOOL_GROUPS}
    except LAException as e:
        log_error(
            "api_traceback",
            "admin_router",
            "get_all_mcp_tools",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "admin_router",
            "get_all_mcp_tools",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@admin_router.post("/user/update/{user_id}")
async def admin_update_user(
    user_id: PydanticObjectId,
    payload: UpdateUserPayload,
    user_service: UserService = Depends(get_user_service),
):
    """Set which MCP tools a user can access. Pass null to restore full access.
    Also accepts optional chat_agent_laui and chat_connection_laui to configure the default chat agent for business users."""
    try:
        log_info(
            "api",
            "admin_router",
            "admin_update_user",
            f"user={get_user_laui()} payload={{user_id={user_id}, {payload.model_dump()}}}",
        )

        config = load_system_config()
        if config.get("sso_enabled", False):
            log_debug(
                "api",
                "admin_router",
                "admin_update_user",
                "SSO is enabled, setting change_password to False",
            )
            payload.change_password = False

        if payload.allowed_mcp_tools is not None:
            unknown = [t for t in payload.allowed_mcp_tools if t not in ALL_MCP_TOOLS]
            if unknown:
                raise HTTPException(
                    status_code=400,
                    detail={"message": "Bad Request", "detail": f"Unknown tool names: {unknown}"},
                )
        update_user_data = await user_service.update_user(
            laui=PydanticObjectId(user_id), payload=payload
        )
        response = {"message": "User config updated"}
        if update_user_data:
            response.update(update_user_data)
        return response
    except LAException as e:
        log_error(
            "api_traceback",
            "admin_router",
            "admin_update_user",
            f"user_id={user_id} LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "admin_router",
            "admin_update_user",
            f"user_id={user_id} unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@admin_router.delete("/user/delete/{user_id}")
async def admin_delete_user(
    user_id: PydanticObjectId, user_service: UserService = Depends(get_user_service)
):
    """Deletes the user. Owner access required."""
    try:
        log_info(
            "api",
            "admin_router",
            "admin_delete_user",
            f"user={get_user_laui()} payload={{user_id={user_id}}}",
        )
        await user_service.delete_user(PydanticObjectId(user_id))
        return {"message": "User deleted successfully"}
    except LAException as e:
        log_error(
            "api_traceback",
            "admin_router",
            "admin_delete_user",
            f"user_id={user_id} LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "admin_router",
            "admin_delete_user",
            f"user_id={user_id} unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )
