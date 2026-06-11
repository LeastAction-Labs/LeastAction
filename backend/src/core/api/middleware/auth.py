# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse, Response
from pydantic_mongo import PydanticObjectId

from src.common.context_vars.user_context import user_context
from src.common.exceptions import LAException
from src.core.ee.iam.session.service import get_session_service
from src.core.ee.iam.user.repo import get_user_repository


async def auth_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:

    if request.method == "OPTIONS":
        return await call_next(request)

    # TODO: We should be excluding public routes when all the apis are access controlled
    private_routes = [
        "/api/v1/access",
        "/api/v1/action",
        "/api/v1/admin",
        "/api/v1/ai",
        "/api/v1/catalog/",
        "/api/v1/check/",
        "/api/v1/cron/",
        "/api/v1/docs",
        "/api/v1/group",
        "/api/v1/query",
        "/api/v1/task",
        "/api/v1/user",
        "/mcp",
    ]

    if not any(request.url.path.startswith(route) for route in private_routes):
        return await call_next(request)

    session_service = get_session_service(request)

    if request.url.path.startswith("/mcp"):
        auth_header = request.headers.get("authorization", "")
        token = auth_header[7:] if auth_header.startswith("Bearer ") else None
        missing_token_detail = "Missing or invalid Authorization Bearer token"
    else:
        token = request.cookies.get("frontend_token")
        missing_token_detail = "Missing frontend token in cookies"

    if not token:
        return JSONResponse(
            status_code=401, content={"message": "Unauthorized", "detail": missing_token_detail}
        )
    try:
        claims = session_service.verify_jwt_token(token)
        request.state.token_claims = claims
        user_repo = get_user_repository(request)
        root_user = await user_repo.find_root_user()
        system_user = await user_repo.find_system_user()
        user = await user_repo.find_user(PydanticObjectId(claims.sub))
        with user_context(
            user=user,
            root_user_laui=root_user.laui if root_user else None,
            system_user_laui=system_user.laui,
            token=token,
        ):
            return await call_next(request)
    except ValueError as e:
        return JSONResponse(
            status_code=401,
            content={"message": "Unauthorized", "detail": f"Token verification failed: {str(e)}"},
        )
    except LAException as e:
        return JSONResponse(
            status_code=e.http_status_code, content={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"message": "Internal server error", "detail": f"{str(e)}"}
        )
