# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from typing import Optional

from pydantic import BaseModel, model_validator
from pydantic_mongo import PydanticObjectId

from src.core.api.common import PaginationRequest, PaginationResponse
from src.core.ee.iam.user.api_request import CreateUserResponse
from src.core.ee.iam.user.schema import UserProjection
from src.core.ee.license.schema import UpdateLicense


class GetSystemAttributesResponse(BaseModel):
    sso_enabled: bool
    instance_laui: PydanticObjectId
    totp_enabled: bool


class UpdateSystemAttributesRequest(BaseModel):
    sso_enabled: Optional[bool] = None
    totp_enabled: Optional[bool] = None


class GetUsersRequest(PaginationRequest):
    pass


class GetUsersResponse(BaseModel):
    users: list[UserProjection]
    pagination: PaginationResponse


class UpdateUserPayload(BaseModel):
    allowed_mcp_tools: list[str] | None = None  # None = restore full access
    chat_agent_laui: str | None = None
    chat_connection_laui: str | None = None
    chat_agent_name: str | None = None
    is_active: bool | None = None
    license_laui: PydanticObjectId | None = None
    change_password: bool = False


class AdminCreateUserRequest(BaseModel):
    username: str
    email: str


class AdminCreateUserResponse(CreateUserResponse):
    pass


class AdminLicenseUpdate(UpdateLicense):
    pass
