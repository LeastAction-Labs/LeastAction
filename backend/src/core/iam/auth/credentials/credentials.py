# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from abc import ABC
from enum import Enum

from pydantic import BaseModel


class BaseCredentials(BaseModel, ABC):
    pass


class UsernamePasswordCredentials(BaseCredentials):
    username: str
    password: str


class Provider(str, Enum):
    LEASTACTION = "leastaction"
    KEYCLOAK = "keycloak"


class AuthorizationCodeCredentials(BaseCredentials):
    code: str
    provider: Provider


class RefreshTokenCredentials(BaseCredentials):
    token_string: str


class ExternalCredentialsValidatorResponse(BaseModel):
    sub: str | None = None
    username: str | None = None
    email: str
