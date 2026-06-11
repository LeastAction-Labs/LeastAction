# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import UTC, datetime

from fastapi import Request

from src.common.exceptions import NotFoundError
from src.core.db import MongoDatabase
from src.core.db.transaction import session_context

from .schema import CreateLinkedAccount, CreateLinkedAccountInDB, LinkedAccount


class LinkedAccountRepository:
    def __init__(self, db: MongoDatabase):
        self.db = db
        self.collection_name = "linked_accounts"

    async def create_linked_account(self, user: CreateLinkedAccount) -> str:
        session = session_context.get()
        user_db = CreateLinkedAccountInDB(**user.model_dump(), created_at=datetime.now(UTC))
        db_response = await self.db[self.collection_name].insert_one(
            user_db.model_dump(), session=session
        )
        return str(db_response.inserted_id)

    async def find_linked_account(self, filter: dict[str, any]) -> LinkedAccount:
        session = session_context.get()
        linked_account = await self.db[self.collection_name].find_one(
            filter=filter, session=session
        )
        if linked_account is None:
            raise NotFoundError(message=f"Linked account not found for filter: {filter}")
        return linked_account


async def get_linked_account_repository(request: Request):
    return request.app.state.linked_account_repository
