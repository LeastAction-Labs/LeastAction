# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic_mongo import PydanticObjectId

from src.common.types import LAUI


class UserType(str, Enum):
    SYSTEM = "system"
    ROOT = "root"


class UserBase(BaseModel):
    username: str = Field(default=None, max_length=255)
    email: EmailStr
    password: str | None = Field(default=None, min_length=6)
    must_change_password: bool = False
    is_active: bool = True
    license_laui: PydanticObjectId | None = None
    allowed_mcp_tools: list[str] | None = None  # None = all tools allowed
    chat_agent_laui: str | None = None
    chat_connection_laui: str | None = None
    chat_agent_name: str | None = None
    user_type: UserType | None = None


class CreateUser(UserBase):
    pass


class CreateUserInDB(CreateUser):
    created_at: datetime


class UpdateUser(BaseModel):
    password: str | None = None
    must_change_password: bool | None = None
    allowed_mcp_tools: list[str] | None = None  # None = restore full access
    chat_agent_laui: str | None = None
    chat_connection_laui: str | None = None
    chat_agent_name: str | None = None
    is_active: bool | None = None
    license_laui: PydanticObjectId | None = None


class User(CreateUserInDB):
    laui: LAUI


class UserProjection(BaseModel):
    model_config = ConfigDict(extra="allow")
    laui: LAUI
