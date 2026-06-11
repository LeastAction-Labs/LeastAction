# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.

from pydantic import BaseModel, model_validator

from src.common.exceptions import UnprocessableEntityError

from .schema import AccessRelation, Permission


class GetAccessRelationsRequest(BaseModel):
    skip: int | None = 0
    page_token: str | None = None
    per_page: int | None = 250
    permission: Permission | None = Permission.OWN


class GetAccessRelationsResponse(BaseModel):
    access_relations: list[AccessRelation]
    next_page_token: str | None = None
    skip: int


class GetPermissionRequest(BaseModel):
    item_laui: str
    user_laui: str | None = None
    group_laui: str | None = None

    @model_validator(mode="after")
    def validate(self):
        if not self.group_laui and not self.user_laui:
            raise UnprocessableEntityError(
                "Query params invalid", "Either one of user_laui or group_laui must be passed"
            )
        return self
