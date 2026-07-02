# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import traceback
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from src.common.context_vars.user_context import get_user_laui
from src.common.exceptions import LAException
from src.common.logger.logger import log_error, log_info
from src.core.api.dependencies import validate_access_for_create_run
from src.core.catalog.api_request import BaseCreateItemRequest
from src.core.catalog.orchestrator import ItemOrchestrator, get_item_orchestrator

action_router = APIRouter()


@action_router.post("/run")
async def execute_action(
    request: Annotated[BaseCreateItemRequest, Depends(validate_access_for_create_run)],
    item_orchestrator: ItemOrchestrator = Depends(get_item_orchestrator),
):
    try:
        log_info(
            "api",
            "action_router",
            "execute_action",
            f"user={get_user_laui()} payload={request.model_dump()}",
        )
        return await item_orchestrator.execute_action(request)
    except LAException as e:
        log_error(
            "api_traceback",
            "action_router",
            "execute_action",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "action_router",
            "execute_action",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )
