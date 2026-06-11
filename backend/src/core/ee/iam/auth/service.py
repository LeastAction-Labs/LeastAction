# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from fastapi import Request

from src.core.ee.iam.auth.api_request import LoginRequest
from src.core.ee.iam.auth.auth_code_dict import AuthCodeDict
from src.core.ee.iam.refresh_token.service import RefreshTokenService
from src.core.ee.iam.session.service import SessionService
from src.core.ee.iam.user.service import UserService

from .api_request import TokenRequest, TokenResponse
from .credentials.validator import CredentialsValidator


class AuthService:
    def __init__(
        self,
        user_service: UserService,
        session_service: SessionService,
        refresh_token_service: RefreshTokenService,
        auth_code_dict: AuthCodeDict,
    ):
        self.session_service = session_service
        self.user_service = user_service
        self.credentials_validator = CredentialsValidator(
            user_service=user_service,
            refresh_token_service=refresh_token_service,
            auth_code_dict=auth_code_dict,
        )
        self.refresh_token_service = refresh_token_service

    async def create_session(self, token_request: TokenRequest):
        credentials = token_request.credentials
        user = await self.credentials_validator.validate(credentials)
        refresh_token = None

        if token_request.grant_type == "authorization_code":
            refresh_token = await self.refresh_token_service.create_refresh_token(
                user_laui=user.laui
            )

        access_token = self.session_service.generate_access_token(user)
        return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user)

    async def login_user(self, request: LoginRequest):
        user = await self.user_service.authenticate(
            username=request.username, password=request.password
        )
        return user


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service
