# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from pydantic_mongo import PydanticObjectId

from src.common.exceptions import AuthenticationError
from src.core.ee.iam.refresh_token.repo import RefreshTokenRepository
from src.core.ee.iam.refresh_token.schema import CreateRefreshToken, RefreshToken


class RefreshTokenService:
    def __init__(self, refresh_token_repo: RefreshTokenRepository):
        self.refresh_token_repo = refresh_token_repo

    def _get_token_string_and_token_hash(self):
        token_string_length = 32
        token_string = secrets.token_hex(token_string_length)
        token_hash = hashlib.sha256(token_string.encode()).hexdigest()
        return token_string, token_hash

    async def create_refresh_token(self, user_laui: PydanticObjectId) -> str:
        token_string, token_hash = self._get_token_string_and_token_hash()
        refresh_token = CreateRefreshToken(
            user_laui=user_laui,
            expires_at=datetime.now(UTC) + timedelta(days=30),
            token_hash=token_hash,
        )
        await self.refresh_token_repo.create_refresh_token(refresh_token)
        return token_string

    async def get_refresh_token_from_token_string(self, token_string: str) -> RefreshToken:
        token_hash = hashlib.sha256(token_string.encode()).hexdigest()
        refresh_token = await self.refresh_token_repo.get_refresh_token_by_token_hash(
            token_hash=token_hash
        )
        if datetime.now(UTC) > refresh_token.expires_at.replace(tzinfo=UTC):
            raise AuthenticationError()
        return refresh_token
