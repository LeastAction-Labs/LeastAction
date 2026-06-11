# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from abc import ABC
from typing import Literal

from pydantic import BaseModel


class BaseCredentials(BaseModel, ABC):
    pass


class UsernamePasswordCredentials(BaseCredentials):
    username: str
    password: str


class AuthorizationCodeCredentials(BaseCredentials):
    code: str
    provider: Literal["least_action"] = "least_action"


class RefreshTokenCredentials(BaseCredentials):
    token_string: str


class ExternalCredentialsValidatorResonse(BaseModel):
    sub: str
    email: str | None = None
