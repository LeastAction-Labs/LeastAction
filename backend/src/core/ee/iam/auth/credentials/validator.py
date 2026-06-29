# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from typing import Any, Protocol

from pydantic_mongo import PydanticObjectId

from src.common.exceptions import AuthenticationError, NotFoundError
from src.core.ee.iam.auth.auth_code_dict import AuthCodeDict
from src.core.ee.iam.auth.credentials.credentials import (
    AuthorizationCodeCredentials,
    BaseCredentials,
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
        user_service: UserService,
        refresh_token_service: RefreshTokenService,
        auth_code_dict: AuthCodeDict,
    ):
        self.user_service = user_service
        self.refresh_token_service = refresh_token_service
        self._validators: dict[type[BaseCredentials], ValidatorFunc] = {
            RefreshTokenCredentials: self._validate_refresh_token,
            AuthorizationCodeCredentials: self._validate_external_auth_code,
        }
        self.auth_code_dict = auth_code_dict

    async def validate(self, credentials: BaseCredentials) -> User:
        validator = self._validators.get(type(credentials))
        if not validator:
            raise ValueError(f"Unsupported credential type: {type(credentials)}")
        return await validator(credentials)

    async def _validate_external_auth_code(self, creds: AuthorizationCodeCredentials) -> User:

        if creds.provider == "least_action":
            try:
                user_data = await self.auth_code_dict.lookup(creds.code)
                user = await self.user_service.find_user(
                    laui=PydanticObjectId(user_data["user_laui"])
                )
                return user
            except NotFoundError:
                raise AuthenticationError()

        """
        validation_result  = validate_external_creds(creds)
        try:
            linked_account  = await self.linked_account_service.get_linked_account_by_sub_and_provider(
                sub = validation_result.sub ,
                provider = creds.provider
            )
            user = await self.user_service.find_user(laui = linked_account.user_laui)
            return user
        except NotFoundError as e :
            user_laui = await self.user_service.create_user(
                CreateUser( email = validation_result.email )
            )
            await self.linked_account_service.create_linked_account(
                linked_account = CreateLinkedAccount(
                    provider = creds.provider ,
                    sub = validation_result.sub ,
                    user_laui = PydanticObjectId(user_laui)
                )
            )
            user = await self.user_service.find_user( laui = PydanticObjectId(user_laui) )
            return user
        """

    async def _validate_refresh_token(self, creds: RefreshTokenCredentials) -> User:
        refresh_token = await self.refresh_token_service.get_refresh_token_from_token_string(
            token_string=creds.token_string
        )
        user = await self.user_service.find_user(laui=refresh_token.user_laui)
        return user
