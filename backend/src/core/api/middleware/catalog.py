# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse, Response

from src.common.context_vars.catalog_context import catalog_context
from src.common.exceptions import LAException
from src.core.catalog.config.catalog_loader import load_catalog_config


async def catalog_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:

    try:
        routes_using_catalog_service = [
            "/api/v1/action/",
            "/api/v1/ai/",
            "/api/v1/catalog/",
            "/api/v1/cron/",
            "/api/v1/task/",
            "/api/v1/query/",
            "/api/v1/embed/",
        ]

        path = request.url.path

        normalized_path = path if path.endswith("/") else f"{path}/"

        if not any(normalized_path.startswith(route) for route in routes_using_catalog_service):
            return await call_next(request)

        catalog_config = load_catalog_config()

        with catalog_context(config=catalog_config):
            return await call_next(request)

    except LAException as e:
        return JSONResponse(
            status_code=e.http_status_code, content={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"message": "Internal server error", "detail": f"{str(e)}"}
        )
