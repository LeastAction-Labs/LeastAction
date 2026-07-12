# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from typing import Any

from pydantic import BaseModel
from pydantic_mongo import PydanticObjectId

from src.core.api.common import PaginationRequest, PaginationResponse
from src.core.ee.group.schema import GroupProjection
from src.core.ee.keto.schema import Relation


class GetGroupsRequest(PaginationRequest):
    relation: Relation = Relation.OWNERS


class GetGroupsResponse(PaginationResponse):
    groups: list[GroupProjection]


class GetGroupResponse(BaseModel):
    name: str
    description: str | None = None
    members: list[str]
    admins: list[str]
    owners: list[str]


class SearchGroupsRequest(PaginationRequest):
    name: str | None = None
    group_lauis: list[PydanticObjectId] | None = None
    exact_match: bool | None = False

    @property
    def get_filters(self) -> dict[str, Any]:
        filters = {}
        if self.name:
            if self.exact_match:
                filters["name"] = self.name
            else:
                filters["name"] = {"$regex": self.name, "$options": "i"}
        if self.group_lauis:
            filters = {}
            filters["_id"] = {"$in": self.group_lauis}
        return filters


class SearchGroupsResponse(BaseModel):
    groups: list[GroupProjection]
    pagination: PaginationResponse
