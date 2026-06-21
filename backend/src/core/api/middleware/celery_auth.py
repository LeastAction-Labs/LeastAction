# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse, Response

from src.common.exceptions import AuthenticationError, LAException
from src.core.ee.iam.session.service import get_session_service
from src.core.ee.iam.user.repo import get_user_repository


async def access_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:

    celery_only_routes = [
        "/api/v1/task/update",
        "/api/v1/task/finish",
        "/api/v1/catalog/get/task_ready_to_run",
    ]

    if not any(request.url.path.startswith(route) for route in celery_only_routes):
        return await call_next(request)

    celery_auth_token = request.cookies.get("celery_token")

    if not celery_auth_token:
        return JSONResponse(
            status_code=401,
            content={"message": "Unauthenitcated", "detail": "Missing celery token"},
        )

    session_service = get_session_service(request)
    user_repo = get_user_repository(request)

    try:
        claims = session_service.verify_jwt_token(celery_auth_token)
        request.state.token_claims = claims
        system_user = await user_repo.find_system_user()
        if system_user and system_user.laui != claims.sub:
            raise AuthenticationError("tampered celery auth token")
        return await call_next(request)
    except LAException as e:
        return JSONResponse(
            status_code=e.http_status_code, content={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"message": "Internal server error", "detail": f"{str(e)}"}
        )
