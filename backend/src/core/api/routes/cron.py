# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import traceback

from fastapi import APIRouter, Depends, HTTPException

from src.common.context_vars.user_context import get_user_laui
from src.common.exceptions import LAException
from src.common.logger.logger import log_error, log_info
from src.core.cron.cron_manager import CronManager, get_cron_manager
from src.core.cron.schema import CronAction, CronManageRequest, CronManageResponse
from src.core.ee.keto.access_reader import AccessReader, get_access_reader

cron_router = APIRouter()


@cron_router.post("/manage")
async def manage_cron(
    request_data: CronManageRequest,
    cron_manager: CronManager = Depends(get_cron_manager),
    access_reader: AccessReader = Depends(get_access_reader),
):
    """
    Manage cron jobs for a project (START or STOP)
    """
    try:
        log_info(
            "api",
            "cron_router",
            "manage_cron",
            f"user={get_user_laui()} payload={request_data.model_dump()}",
        )
        user_laui = get_user_laui()
        await access_reader.check_item_own_access(
            item_laui=str(request_data.project_laui), user_laui=user_laui
        )

        if request_data.action == CronAction.START:
            success = await cron_manager.start_cron(request_data.project_laui)
            message = f"Cron started successfully for project {request_data.project_laui}"
        elif request_data.action == CronAction.STOP:
            success = await cron_manager.stop_cron(request_data.project_laui)
            message = f"Cron stopped successfully for project {request_data.project_laui}"
        else:
            raise HTTPException(status_code=400, detail=f"Invalid action: {request_data.action}")

        cron_result = CronManageResponse(
            success=success,
            message=message,
            project_laui=str(request_data.project_laui),
            action=request_data.action,
        )
        return cron_result.model_dump()

    except LAException as e:
        log_error(
            "api_traceback",
            "cron_router",
            "manage_cron",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "cron_router",
            "manage_cron",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )
