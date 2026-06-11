# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic_mongo import PydanticObjectId

from src.common.models import AccessPatch
from src.common.types import LAUI, AccessPatchType, SetAccess, UnsetAccess, iLAUI
from src.core.ee.keto.schema import Permission


class ItemBase(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    item_type: str
    parent_laui: PydanticObjectId | None = None
    is_root: bool | None = False
    project_laui: PydanticObjectId | None = None
    account_laui: PydanticObjectId | None = None


class CreateItem(ItemBase):
    access_patch: AccessPatchType = Field(default=AccessPatch())


class CreateItemInDB(ItemBase):
    access: SetAccess = Field(validation_alias="access_patch")
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    created_by: PydanticObjectId
    updated_by: PydanticObjectId | None = None
    version: int = 1
    access_patch: Any = Field(default=None, exclude=True, init=False)
    last_session_id: str


class UpdateItem(ItemBase):
    laui: iLAUI = Field(exclude=True)
    version: int
    set_access: SetAccess | None = Field(
        validation_alias="access_patch", exclude=True, default=None
    )
    unset_access: UnsetAccess | None = Field(
        validation_alias="access_patch", exclude=True, default=None
    )
    access_patch: Any = Field(default=None, exclude=True, init=False)
    updated_by: PydanticObjectId


class Item(CreateItemInDB):
    laui: LAUI
    access: Any = Field(default=None, exclude=True, init=False)


class ItemProjection(BaseModel):
    model_config = ConfigDict(extra="allow")
    laui: LAUI
    item_type: str
    access: Any = Field(default=None, exclude=True, init=False)


class ItemWithPermission(BaseModel):
    laui: PydanticObjectId
    permission: Permission
