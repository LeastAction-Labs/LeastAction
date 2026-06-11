# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from pydantic_mongo import PydanticObjectId

from src.common.exceptions import LicenseError, NotFoundError
from src.core.db.transaction import transactional
from src.core.ee.iam.user.schema import CreateUser
from src.core.ee.iam.user.service import UserService
from src.core.ee.license.schema import UpdateLicense, UserListPatch
from src.core.ee.license.service import LicenseService

from .api_request import AdminCreateUserRequest, AdminLicenseUpdate, UpdateUserPayload


class AdminService:
    def __init__(self, user_service: UserService, license_service: LicenseService):
        self.user_service = user_service
        self.license_service = license_service

    @transactional
    async def create_user(self, request: AdminCreateUserRequest):
        try:
            license = await self.license_service.get_vacant_license()
            create_user_response = await self.user_service.create_user(
                user=CreateUser(**request.model_dump(), license_laui=license.laui),
                auto_generate=True,
            )
            await self.license_service.update_license(
                license=UpdateLicense(
                    laui=license.laui,
                    user_list_patch=UserListPatch(
                        add=[PydanticObjectId(create_user_response.user_laui)]
                    ),
                )
            )
            return create_user_response

        except NotFoundError:
            raise LicenseError(
                message="Maximum User Limit Reached",
                detail="There are no vacant slots remaining for new users. Please remove existing users to free up seats, or purchase additional licenses.",
            )

    @transactional
    async def update_license(self, request: AdminLicenseUpdate):
        patched_user_lauis = await self.license_service.update_license(license=request)
        if patched_user_lauis:
            await self.user_service.update_users(
                lauis=patched_user_lauis,
                payload=UpdateUserPayload(
                    license_laui=request.laui if request.user_list_patch.add else None
                ),
            )


from fastapi import Request


def get_admin_service(request: Request) -> AdminService:
    return request.app.state.admin_service
