# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import traceback

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pydantic_mongo import PydanticObjectId

from src.common.context_vars.user_context import get_user_laui
from src.common.exceptions import InvalidArgumentError, LAException
from src.common.logger.logger import log_error, log_info
from src.common.utils import load_system_config
from src.core.api.utils import convert_objectid_to_str
from src.core.iam.user.api_request import SearchUsersRequest
from src.core.iam.user.service import UserService, get_user_service

user_router = APIRouter()


class UpdateMarketplaceTokenRequest(BaseModel):
    marketplace_access_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@user_router.get("/me")
async def get_current_user(
    user_service: UserService = Depends(get_user_service),
):
    """Get the current authenticated user's profile info."""
    try:
        log_info("api", "user_router", "get_current_user", f"user={get_user_laui()} payload={{}}")
        user_laui = get_user_laui()
        if not user_laui:
            raise HTTPException(
                status_code=401,
                detail={"message": "Unauthorized", "detail": "User not authenticated"},
            )

        user_laui_obj = PydanticObjectId(user_laui)
        user = await user_service.find_user(user_laui_obj)
        return convert_objectid_to_str(user.model_dump(exclude="password"))
    except LAException as e:
        log_error(
            "api_traceback",
            "user_router",
            "get_current_user",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "user_router",
            "get_current_user",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@user_router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    user_service: UserService = Depends(get_user_service),
):
    """Change the current user's password. Required on first login when must_change_password is True."""
    try:
        log_info(
            "api",
            "user_router",
            "change_password",
            f"user={get_user_laui()} payload={{current_password=***, new_password=***}}",
        )
        config = load_system_config()
        if config.get("sso_enabled", False):
            raise InvalidArgumentError(
                "Password change is not allowed when SSO is enabled",
            )
        user_laui = get_user_laui()
        if not user_laui:
            raise HTTPException(
                status_code=401,
                detail={"message": "Unauthorized", "detail": "User not authenticated"},
            )

        user_laui_obj = PydanticObjectId(user_laui)
        await user_service.change_password(
            user_laui_obj, request.current_password, request.new_password
        )
        return {"message": "Password changed successfully"}
    except LAException as e:
        log_error(
            "api_traceback",
            "user_router",
            "change_password",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "user_router",
            "change_password",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@user_router.post("/search")
async def search_users(
    request: SearchUsersRequest, user_service: UserService = Depends(get_user_service)
):
    try:
        log_info(
            "api",
            "user_router",
            "search_users",
            f"user={get_user_laui()} payload={request.model_dump()}",
        )
        return await user_service.search_users(request)
    except LAException as e:
        log_error(
            "api_traceback",
            "user_router",
            "search_users",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "user_router",
            "search_users",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )
