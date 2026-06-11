# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.common.context_vars.session_context import generate_session_id, session_id_context


class SessionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, session_header: str = "X-Session-ID"):
        super().__init__(app)
        self.session_header = session_header

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        incoming = request.headers.get(self.session_header)
        new_session_id = incoming if incoming else generate_session_id()
        token = session_id_context.set(new_session_id)

        try:
            response = await call_next(request)
            response.headers[self.session_header] = new_session_id
            return response
        finally:
            # Reset the context variable to prevent leaking to other requests
            session_id_context.reset(token)
