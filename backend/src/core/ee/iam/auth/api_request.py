# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from typing import Literal, Union

from pydantic import BaseModel, model_validator

from src.core.ee.iam.auth.credentials.credentials import (
    AuthorizationCodeCredentials,
    RefreshTokenCredentials,
    UsernamePasswordCredentials,
)
from src.core.ee.iam.user.schema import User

# In future, this will be a Union of all possible request types,
# will contain credentials for other providers in the future(Google, etc)
LoginRequest = UsernamePasswordCredentials  # the older code is using this

Credentials = Union[RefreshTokenCredentials, AuthorizationCodeCredentials]


from src.common.exceptions import InvalidArgumentError


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class TokenRequest(BaseModel):
    grant_type: Literal["refresh_token", "authorization_code"]
    credentials: Credentials

    @model_validator(mode="after")
    def validations(self):
        if self.grant_type == "refresh_token" and not isinstance(
            self.credentials, RefreshTokenCredentials
        ):
            error_msg = f"if grant type is {self.grant_type}: then token_string must be passed in credentials."
            raise InvalidArgumentError(error_msg)

        if self.grant_type == "authorization_code" and (
            not isinstance(self.credentials, AuthorizationCodeCredentials)
        ):
            error_msg = f"if grant type is {self.grant_type}: then code , provider and state must be passed in credentials."
            raise InvalidArgumentError(error_msg)
        return self


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"
    user: User


class AuthRequest(BaseModel):
    client_id: str
    redirect_uri: str
    state: str


class RedirectWithCodeRequest(BaseModel):
    user_laui: str
