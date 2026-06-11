# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import datetime

from pydantic import BaseModel
from pydantic_mongo import PydanticObjectId

from src.common.types import LAUI


class BaseRefreshToken(BaseModel):
    user_laui: PydanticObjectId
    expires_at: datetime
    token_hash: str


class CreateRefreshToken(BaseRefreshToken):
    pass


class CreateRefreshTokenInDB(CreateRefreshToken):
    created_at: datetime
    updated_at: datetime | None = None


class UpdateRefreshToken(BaseModel):
    hash: str
    expires_at: datetime


class UpdateRefreshTokenInDB(UpdateRefreshToken):
    updated_at: datetime


class RefreshToken(CreateRefreshTokenInDB):
    laui: LAUI
