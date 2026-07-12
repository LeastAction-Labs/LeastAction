# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from typing import Any

from pydantic import BaseModel
from pydantic_mongo import PydanticObjectId

from src.core.api.common import PaginationRequest, PaginationResponse
from src.core.iam.user.schema import UserProjection


class SearchUsersRequest(PaginationRequest):
    username: str | None = None
    email: str | None = None
    user_lauis: list[PydanticObjectId] | None = []

    @property
    def get_filters(self) -> dict[str, Any]:
        filters = {}
        if self.username:
            filters["username"] = {"$regex": self.username, "$options": "i"}
        if self.email:
            filters["email"] = {"$regex": self.email, "$options": "i"}
        if self.user_lauis:
            filters = {}
            filters["_id"] = {"$in": self.user_lauis}
        return filters


class SearchUsersResponse(BaseModel):
    users: list[UserProjection]
    pagination: PaginationResponse


class CreateUserResponse(BaseModel):
    username: str | None = None
    temp_password: str | None = None
    user_laui: str
