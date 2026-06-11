# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from pydantic_mongo import PydanticObjectId
from pymongo import IndexModel
from pymongo.collation import Collation
from pymongo.errors import OperationFailure

from src.common.exceptions import ConflictError, NotFoundError
from src.core.db import MongoDatabase
from src.core.db.transaction import session_context

from .schema import CreateUser, CreateUserInDB, User, UserProjection, UserType


class UserRepository:
    def __init__(self, db: MongoDatabase):
        self.db = db
        self.collection_name = "users"
        self.root_user = None
        self.system_user = None

    async def create_indexes(self):
        await self.db[self.collection_name].create_indexes(
            indexes=[
                IndexModel("username", unique=True, collation=Collation(locale="en", strength=2)),
                IndexModel("email", unique=True),
                IndexModel("user_type", unique=True, sparse=True),
            ]
        )

    async def create_user(self, user: CreateUser) -> str:
        try:
            session = session_context.get()
            user_db = CreateUserInDB(**user.model_dump(), created_at=datetime.now(UTC))
            user_create_dict = user_db.model_dump()
            if not user_create_dict.get("user_type"):
                user_create_dict.pop("user_type")
            db_response = await self.db[self.collection_name].insert_one(
                user_create_dict, session=session
            )
            return str(db_response.inserted_id)
        except OperationFailure as e:
            if e.code == 11000:
                key = next(iter(e.details["keyPattern"]))
                raise ConflictError(
                    message=f"user with {key}: {getattr(user, key, None)} already exists"
                )

    async def get_user_by_username(self, username: str) -> User:
        session = session_context.get()
        user = await self.db[self.collection_name].find_one({"username": username}, session=session)
        if user is None:
            raise NotFoundError(f"User not found with username: {username}")
        return User(**user)

    async def get_user_by_email(self, email: str) -> User:
        session = session_context.get()
        user = await self.db[self.collection_name].find_one({"email": email}, session=session)
        if user is None:
            raise NotFoundError(f"User not found with username: {email}")
        return User(**user)

    async def find_user(self, laui: PydanticObjectId):
        session = session_context.get()
        user = await self.db[self.collection_name].find_one({"_id": laui}, session=session)
        if user is None:
            raise NotFoundError(f"User not found with laui : {laui}")
        return User(**user)

    async def find_root_user(self) -> User | None:
        if self.root_user:
            return self.root_user
        session = session_context.get()
        user_doc = await self.db[self.collection_name].find_one(
            {"user_type": UserType.ROOT}, session=session
        )
        if not user_doc:
            return None
        root_user = User(**user_doc)
        self.root_user = root_user
        return root_user

    async def find_system_user(self) -> User | None:
        if self.system_user:
            return self.system_user
        session = session_context.get()
        user_doc = await self.db[self.collection_name].find_one(
            {"user_type": UserType.SYSTEM}, session=session
        )
        if not user_doc:
            return None
        system_user = User(**user_doc)
        self.system_user = system_user
        return system_user

    async def find_users(
        self, filter: dict[str, Any], projections: list[str], offset: int = 0, limit: int = 0
    ) -> list[UserProjection]:
        session = session_context.get()
        users = (
            await self.db[self.collection_name]
            .find(filter, projections, session=session)
            .skip(offset)
            .limit(limit)
            .to_list(length=None)
        )
        return [UserProjection(**user) for user in users]

    async def check_next_page_exists(self, filter: dict[str, Any], offset: int, limit: int) -> bool:
        session = session_context.get()
        items = (
            await self.db[self.collection_name]
            .find(filter, session=session)
            .skip(offset + limit)
            .limit(1)
            .to_list(length=None)
        )
        has_next = bool(items)
        return has_next

    async def update_user(self, laui: PydanticObjectId, update_data: dict[str, Any]) -> User:
        """Update user fields."""
        session = session_context.get()
        result = await self.db[self.collection_name].update_one(
            {"_id": laui}, {"$set": update_data}, session=session
        )
        if result.matched_count == 0:
            raise NotFoundError(f"User not found with laui: {laui}")
        # Return updated user
        return await self.find_user(laui)

    async def update_users(
        self, lauis: list[PydanticObjectId], update_data: dict[str, Any]
    ) -> User:
        session = session_context.get()
        await self.db[self.collection_name].update_many(
            {"_id": {"$in": lauis}}, {"$set": update_data}, session=session
        )

    async def delete_user(self, laui: PydanticObjectId):
        session = session_context.get()
        await self.db[self.collection_name].delete_one({"_id": laui}, session=session)


def get_user_repository(request: Request) -> UserRepository:
    return request.app.state.user_repo
