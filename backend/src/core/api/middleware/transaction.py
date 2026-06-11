# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from src.core.db.transaction import (
    set_transaction_manager_context,
    transaction_manager_context,
)


async def transaction_context_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
):
    token = set_transaction_manager_context(request.app.state.transaction_manager)
    response = await call_next(request)
    transaction_manager_context.reset(token)
    return response
