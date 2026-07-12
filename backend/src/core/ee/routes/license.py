# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import traceback

from fastapi import APIRouter, Depends, HTTPException
from pydantic_mongo import PydanticObjectId

from src.common.context_vars.user_context import get_user_laui
from src.common.exceptions import LAException
from src.common.logger.logger import log_error, log_info
from src.core.ee.admin.service import AdminService, get_admin_service
from src.core.ee.license.schema import LicenseUploadRequest, UpdateLicense
from src.core.ee.license.service import LicenseService, get_license_service

license_router = APIRouter()


@license_router.post("/upload")
async def update_license(
    license_request: LicenseUploadRequest, manager: LicenseService = Depends(get_license_service)
):
    try:
        log_info(
            "api",
            "license_router",
            "update_license",
            f"user={get_user_laui()} payload={license_request.model_dump()}",
        )
        license_laui = await manager.add_license(license_request)
        return {
            "status": "success",
            "message": "License files updated successfully",
            "license_laui": str(license_laui),
        }
    except LAException as e:
        log_error(
            "api_traceback",
            "license_router",
            "update_license",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "license_router",
            "update_license",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@license_router.get("/get")
async def get_license(manager: LicenseService = Depends(get_license_service)):
    try:
        log_info(
            "api", "license_router", "get_license_list", f"user={get_user_laui()} payload={{}}"
        )
        licenses = await manager.get_licenses()
        return licenses
    except LAException as e:
        log_error(
            "api_traceback",
            "license_router",
            "get_license_list",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "license_router",
            "get_license_list",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@license_router.get("/get/{license_laui}")
async def get_license_by_laui(
    license_laui: PydanticObjectId, manager: LicenseService = Depends(get_license_service)
):
    try:
        log_info(
            "api",
            "license_router",
            "get_license",
            f"user={get_user_laui()} payload={{license_laui={license_laui}}}",
        )
        return await manager.get_license(license_laui)
    except LAException as e:
        log_error(
            "api_traceback",
            "license_router",
            "get_license",
            f"license_laui={license_laui} LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "license_router",
            "get_license",
            f"license_laui={license_laui} unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@license_router.post("/update")
async def update_license_record(
    license: UpdateLicense, admin_service: AdminService = Depends(get_admin_service)
):
    try:
        log_info(
            "api",
            "license_router",
            "update_license_record",
            f"user={get_user_laui()} payload={license.model_dump()}",
        )
        await admin_service.update_license(license)
    except LAException as e:
        log_error(
            "api_traceback",
            "license_router",
            "update_license_record",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "license_router",
            "update_license_record",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )
