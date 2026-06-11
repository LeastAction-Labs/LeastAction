# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from pydantic_mongo import PydanticObjectId


class LinkedAccountBase(BaseModel):
    provider: Literal["google", "github"]
    sub: str
    user_laui: PydanticObjectId


class CreateLinkedAccount(LinkedAccountBase):
    pass


class CreateLinkedAccountInDB(CreateLinkedAccount):
    created_at: datetime


class LinkedAccount(CreateLinkedAccountInDB):
    laui: PydanticObjectId
