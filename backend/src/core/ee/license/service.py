# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import UTC, datetime

import jwt
from fastapi import Request
from pydantic import ValidationError
from pydantic_mongo import PydanticObjectId

from src.common.exceptions import LicenseError
from src.core.ee.license.repo import LicenseRepository
from src.core.ee.license.schema import (
    CreateLicense,
    License,
    LicenseClaims,
    LicenseStatus,
    LicenseTier,
    LicenseUploadRequest,
    UpdateLicense,
)


class LicenseService:
    def __init__(self, license_repo: LicenseRepository):
        self.license_repo = license_repo

    async def get_license(self, license_laui: PydanticObjectId) -> License:
        return await self.license_repo.get_license(license_laui=license_laui)

    def _decode_license(self, license_id: str, public_key: str) -> LicenseClaims:
        try:
            decoded = jwt.decode(
                license_id, public_key, algorithms=["RS256"], options={"verify_exp": True}
            )
            return LicenseClaims(**decoded)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, ValidationError) as e:
            raise LicenseError(f"Tampered license: {license_id[:-10]}", f"{str(e)}")

    async def verify_license(self, license: License) -> LicenseClaims:
        license_claims = self._decode_license(
            license_id=license.license_id, public_key=license.public_key
        )
        if license_claims.tier == LicenseTier.FREE and license_claims.trial_end_date:
            if license_claims.trial_end_date <= datetime.now(UTC):
                raise LicenseError(f"Free trial expired for license: {license.license_id[:-10]}")
        if license_claims.tier == LicenseTier.BUSINESS and license_claims.expiry_date:
            if license_claims.expiry_date <= datetime.now(UTC):
                await self.license_repo.update_license(
                    license=UpdateLicense(laui=license.laui, status=LicenseStatus.EXPIRED)
                )
                raise LicenseError(f"License expired  : {license.license_id[:-10]}")
        return license_claims

    async def get_vacant_license(self):
        return await self.license_repo.get_license_by_filter(filter={"limit_exceeded": False})

    async def add_license(self, license_request: LicenseUploadRequest):
        license_claims = self._decode_license(
            license_id=license_request.license_id, public_key=license_request.public_key
        )
        return await self.license_repo.create_license(
            license=CreateLicense(**license_claims.model_dump(), **license_request.model_dump())
        )

    async def update_license(self, license: UpdateLicense) -> list[PydanticObjectId]:

        if not license.user_list_patch:
            await self.license_repo.update_license(license)
            return []

        license_in_db = await self.license_repo.get_license(license.laui)
        license_claims = self._decode_license(
            license_id=license_in_db.license_id, public_key=license_in_db.public_key
        )

        max_seats = (
            license_claims.permanent_seats
            if license_claims.tier == LicenseTier.BUSINESS
            else license_claims.trial_seats
        )

        if license.user_list_patch.add:
            license.user_list_patch.add = [
                user for user in license.user_list_patch.add if user not in license_in_db.user_list
            ]
            seats_left = max_seats - len(license_in_db.user_list)
            if len(license.user_list_patch.add) > seats_left:
                raise LicenseError(
                    "Seat limit issue",
                    f"The remaining seats are: {seats_left},you are trying to add: {len(license.user_list_patch.add)}",
                )
            if len(license.user_list_patch.add) == seats_left:
                license.limit_exceeded = True
            await self.license_repo.update_license(license)
            return license.user_list_patch.add

        license.user_list_patch.remove = [
            user for user in license.user_list_patch.remove if user in license_in_db.user_list
        ]

        if license.user_list_patch.remove:
            if license_in_db.limit_exceeded:
                license.limit_exceeded = False
            await self.license_repo.update_license(license)
        return license.user_list_patch.remove

    async def get_licenses(self):
        return await self.license_repo.find_licenses()


def get_license_service(request: Request) -> LicenseService:
    return request.app.state.license_service
