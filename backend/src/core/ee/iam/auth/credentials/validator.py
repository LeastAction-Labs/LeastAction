# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from typing import Any, Protocol

from keycloak.keycloak_openid import KeycloakOpenID
from pydantic_mongo import PydanticObjectId

from src.common.exceptions import AuthenticationError, NotFoundError
from src.common.secrets import get_secret
from src.core.admin.api_request import AdminCreateUserRequest
from src.core.admin.service import AdminService
from src.core.ee.iam.auth.auth_code_dict import AuthCodeDict
from src.core.ee.iam.auth.credentials.credentials import (
    AuthorizationCodeCredentials,
    BaseCredentials,
    Provider,
    RefreshTokenCredentials,
)
from src.core.ee.iam.refresh_token.service import RefreshTokenService
from src.core.ee.iam.user.schema import User
from src.core.ee.iam.user.service import UserService


class ValidatorFunc(Protocol):
    async def __call__(self, creds: Any) -> User: ...


class CredentialsValidator:
    def __init__(
        self,
        admin_service: AdminService,
        user_service: UserService,
        refresh_token_service: RefreshTokenService,
        auth_code_dict: AuthCodeDict,
    ):
        self.user_service = user_service
        self.refresh_token_service = refresh_token_service
        self._validators: dict[type[BaseCredentials], ValidatorFunc] = {
            RefreshTokenCredentials: self._validate_refresh_token,
            AuthorizationCodeCredentials: self._validate_auth_code,
        }
        self.auth_code_dict = auth_code_dict
        self.admin_service = admin_service
        self.keycloak_service = KeycloakOpenID(
            server_url=get_secret("KEYCLOAK_SERVER_URL"),
            client_id="leastaction",
            realm_name="leastaction",
            client_secret_key=get_secret("KEYCLOAK_CLIENT_SECRET"),
        )

    async def validate(self, credentials: BaseCredentials) -> User:
        validator = self._validators.get(type(credentials))
        if not validator:
            raise ValueError(f"Unsupported credential type: {type(credentials)}")
        return await validator(credentials)

    async def _validate_auth_code(self, creds: AuthorizationCodeCredentials) -> User:

        if creds.provider == Provider.KEYCLOAK:
            tokens = self.keycloak_service.token(
                grant_type="authorization_code",
                code=creds.code,
                redirect_uri="http://localhost:8080/api/v1/redirect-with-code",
            )
            userinfo = self.keycloak_service.decode_token(tokens["access_token"])
            email = userinfo.get("email")
            username = userinfo.get("preferred_username")
            try:
                user = await self.user_service.get_user_by_email(email)
            except Exception:
                await self.admin_service.create_user(
                    AdminCreateUserRequest(username=username or email, email=email)
                )
                user = await self.user_service.get_user_by_email(email)
            return user

        try:
            user_data = await self.auth_code_dict.lookup(creds.code)
            user = await self.user_service.find_user(laui=PydanticObjectId(user_data["user_laui"]))
            return user
        except NotFoundError:
            raise AuthenticationError()

    async def _validate_refresh_token(self, creds: RefreshTokenCredentials) -> User:
        refresh_token = await self.refresh_token_service.get_refresh_token_from_token_string(
            token_string=creds.token_string
        )
        user = await self.user_service.find_user(laui=refresh_token.user_laui)
        return user
