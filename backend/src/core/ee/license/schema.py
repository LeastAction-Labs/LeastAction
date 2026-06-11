# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, model_validator
from pydantic_mongo import PydanticObjectId

from src.common.exceptions import UnprocessableEntityError
from src.common.types import LAUI


class LicenseTier(str, Enum):
    FREE = "free"
    ENTERPRISE = "enterprise"
    BUSINESS = "business"


class LicenseStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REFUNDED = "refunded"


class LicenseClaims(BaseModel):
    permanent_seats: int
    trial_seats: int
    tier: LicenseTier
    user_laui: PydanticObjectId
    expiry_date: datetime | None = None
    trial_start_date: datetime | None = None
    trial_end_date: datetime | None = None


class LicenseBase(LicenseClaims):
    license_id: str
    public_key: str
    status: LicenseStatus = LicenseStatus.ACTIVE
    user_list: list[PydanticObjectId] = []
    limit_exceeded: bool = False


class CreateLicense(LicenseBase):
    pass


class CreateLicenseInDB(CreateLicense):
    created_at: datetime
    updated_at: datetime | None = None


class License(CreateLicenseInDB):
    laui: LAUI


class UserListPatch(BaseModel):
    add: list[PydanticObjectId] = []
    remove: list[PydanticObjectId] = []

    @model_validator(mode="after")
    def check_only_one_action(self):
        actions = [bool(self.add), bool(self.remove)]
        active_count = sum(actions)

        if active_count > 1:
            raise UnprocessableEntityError(
                "invalid user_list_patch field",
                "You can only perform one action (add, remove, or replace) at a time.",
            )

        if active_count == 0:
            raise UnprocessableEntityError(
                "invalid user_list_patch field",
                "You must provide at least one action: add, remove, or replace.",
            )

        return self


class UpdateLicense(BaseModel):
    laui: PydanticObjectId
    user_list_patch: UserListPatch | None = None
    status: LicenseStatus | None = None
    limit_exceeded: bool | None = None


class LicenseUploadRequest(BaseModel):
    license_id: str
    public_key: str


class LicenseProjection(BaseModel):
    laui: LAUI
    license_id: str
    tier: LicenseTier
    status: LicenseStatus
