# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.common.types import LAUI, iLAUI
from src.core.ee.models import Access, AccessPatch
from src.core.ee.types import AccessPatchType, SetAccess, UnsetAccess


class _GroupBase(BaseModel):
    name: str
    description: str | None = None


class CreateGroup(_GroupBase):
    access_patch: AccessPatchType = AccessPatch()


class CreateGroupInDB(_GroupBase):
    access: SetAccess = Field(validation_alias="access_patch")
    created_at: datetime
    updated_at: datetime = Field(default=None, init=None)
    last_session_id: str


class GroupInDB(_GroupBase):
    access: Access
    created_at: datetime
    updated_at: datetime | None = None


class UpdateGroup(_GroupBase):
    laui: iLAUI = Field(exclude=True)
    set_access: SetAccess = Field(validation_alias="access_patch", exclude=True)
    unset_access: UnsetAccess = Field(validation_alias="access_patch", exclude=True)


class Group(GroupInDB):
    laui: LAUI


class GroupProjection(BaseModel):
    model_config = ConfigDict(extra="allow")
    laui: LAUI
    name: str
