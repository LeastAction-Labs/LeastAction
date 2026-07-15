# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import UTC, datetime

from src.common.exceptions import NotFoundError
from src.core.db.transaction import session_context
from src.core.db.types import MongoDatabase
from src.core.iam.refresh_token.schema import (
    CreateRefreshToken,
    CreateRefreshTokenInDB,
    RefreshToken,
)


class RefreshTokenRepository:
    def __init__(self, db: MongoDatabase):
        self.db = db
        self.collection_name = "refresh_tokens"

    async def create_refresh_token(self, refresh_token: CreateRefreshToken) -> str:
        session = session_context.get()
        refresh_token_in_db = CreateRefreshTokenInDB(
            **refresh_token.model_dump(),
            created_at=datetime.now(UTC),
        )
        db_response = await self.db[self.collection_name].insert_one(
            refresh_token_in_db.model_dump(), session=session
        )
        return str(db_response.inserted_id)

    async def get_refresh_token_by_token_hash(self, token_hash: str) -> RefreshToken:
        session = session_context.get()
        refresh_token = await self.db[self.collection_name].find_one(
            {"token_hash": token_hash}, session=session
        )
        if not refresh_token:
            raise NotFoundError(f"Refresh token with token_hash: {token_hash} not found.")
        return RefreshToken(**refresh_token)
