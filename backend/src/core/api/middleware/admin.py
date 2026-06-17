# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse, Response

from src.common.context_vars.user_context import get_user_laui, is_root_user, is_system_user
from src.common.exceptions import LAException
from src.core.catalog.item.repo import get_item_repository
from src.core.ee.keto.access_reader import get_access_reader


async def admin_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    try:
        if request.url.path.startswith("/api/v1/admin"):
            item_repo = get_item_repository(request)
            access_reader = get_access_reader(request)
            if is_root_user() or is_system_user():
                return await call_next(request)
            account_laui = await item_repo.get_account_laui()
            await access_reader.check_item_own_access(
                item_laui=account_laui, user_laui=get_user_laui()
            )
        return await call_next(request)
    except LAException as e:
        return JSONResponse(
            status_code=e.http_status_code, content={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"message": "Internal server error", "detail": f"{str(e)}"}
        )
