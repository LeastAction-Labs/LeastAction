# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic_mongo import PydanticObjectId

from src.common.types import LAUI, iLAUI
from src.core.catalog.item.schema import ItemBase


class _ItemRevisionBase(ItemBase):
    item_laui: iLAUI
    access: Any = Field(default=None, exclude=True, init=False)


class CreateItemRevision(_ItemRevisionBase):
    pass


class CreateItemRevisionInDB(CreateItemRevision):
    created_at: datetime | None = None
    created_by: PydanticObjectId | None = None
    updated_by: PydanticObjectId | None = None


class ItemRevision(CreateItemRevisionInDB):
    laui: LAUI


class ItemRevisionProjection(BaseModel):
    model_config = ConfigDict(extra="allow")
    laui: LAUI
    item_laui: PydanticObjectId
