# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse, Response
from pydantic_mongo import PydanticObjectId

from src.common.context_vars.user_context import get_root_user_laui, get_system_user_laui, get_user
from src.common.exceptions import AuthorizationError, LAException, LicenseError
from src.core.ee.iam.user.repo import get_user_repository
from src.core.ee.license.service import get_license_service


async def license_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    license_check_routes = [
        "/api/v1/access",
        "/api/v1/action",
        "/api/v1/admin",
        "/api/v1/ai",
        "/api/v1/catalog/",
        "/api/v1/check/",
        "/api/v1/cron/",
        "/api/v1/group",
        "/api/v1/task",
        "/api/v1/user",
        "/api/v1/login",
        "/mcp",
    ]
    try:
        if request.method == "OPTIONS" or not any(
            request.url.path.startswith(route) for route in license_check_routes
        ):
            return await call_next(request)

        user = get_user()
        root_user_laui = get_root_user_laui()
        system_user_laui = get_system_user_laui()

        if not user:
            user_repo = get_user_repository(request)
            query_params = request.query_params
            username = query_params.get("username")
            user = await user_repo.get_user_by_username(username)
            root_user = await user_repo.find_root_user()
            root_user_laui = root_user.laui if root_user else None
            system_user_laui = (await user_repo.find_system_user()).laui

        if user.laui == system_user_laui or user.laui == root_user_laui:
            return await call_next(request)

        if not user.is_active:
            raise AuthorizationError("User is deactivated")

        if not user.license_laui:
            raise LicenseError("User not assigned with any license")
        license_service = get_license_service(request)
        license = await license_service.get_license(license_laui=user.license_laui)
        if PydanticObjectId(user.laui) not in license.user_list:
            raise LicenseError("User not assigned with any license")
        license_claims = await license_service.verify_license(license=license)
        if license_claims.instance_id != PydanticObjectId(root_user_laui):
            raise LicenseError("Using license created for a different system")

        return await call_next(request)

    except LAException as e:
        return JSONResponse(
            status_code=e.http_status_code, content={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"message": "Internal server error", "detail": f"{str(e)}"}
        )
