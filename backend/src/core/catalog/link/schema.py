# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import datetime

from pydantic import BaseModel
from pydantic_mongo import PydanticObjectId

from src.common.types import LAUI
from src.core.ee.keto.schema import Permission


class _BaseLink(BaseModel):
    parent_laui: PydanticObjectId | None = None
    child_laui: PydanticObjectId
    parent_type: str | None = None
    child_type: str
    true_parent: bool

    def __eq__(self, other):
        if isinstance(other, _BaseLink):
            return self.child_laui == other.child_laui and self.parent_laui == other.parent_laui
        return False

    def __hash__(self):
        return hash((self.parent_laui, self.child_laui))


class CreateLink(_BaseLink):
    pass


class CreateLinkInDB(CreateLink):
    created_at: datetime


class Link(CreateLink):
    laui: LAUI


class LinkWithPermission(CreateLink):
    permission: Permission
