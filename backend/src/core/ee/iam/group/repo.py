# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from pydantic_mongo import PydanticObjectId

from src.common.context_vars.session_context import get_session_id
from src.common.exceptions import NotFoundError
from src.common.utils import transform_access
from src.core.db import MongoDatabase
from src.core.db.transaction import session_context
from src.core.ee.iam.group.schema import CreateGroup, CreateGroupInDB, Group, UpdateGroup

from .schema import GroupProjection


class GroupRepository:
    def __init__(self, db: MongoDatabase):
        self.db = db
        self.collection_name = "groups"

    async def create_group(self, group: CreateGroup) -> str:
        try:
            session = session_context.get()
            print(group.model_dump())
            group_db = CreateGroupInDB(
                **group.model_dump(), created_at=datetime.now(UTC), last_session_id=get_session_id()
            )
            db_response = await self.db[self.collection_name].insert_one(
                group_db.model_dump(), session=session
            )
            return str(db_response.inserted_id)
        except Exception as e:
            raise e

    async def find_group(self, laui: PydanticObjectId):
        try:
            session = session_context.get()
            group = await self.db[self.collection_name].find_one({"_id": laui}, session=session)
            if group is None:
                raise NotFoundError(f"Group not found with laui : {laui}")
            return Group(**group)
        except Exception as e:
            raise e

    async def find_group_by_name(self, name: str):
        try:
            session = session_context.get()
            group = await self.db[self.collection_name].find_one({"name": name}, session=session)
            if group is None:
                raise NotFoundError(f"Group not found with name : {name}")
            return Group(**group)
        except Exception as e:
            raise e

    async def find_groups(
        self, filter: dict[str, Any], projections: list[str], offset: int = 0, limit: int = 0
    ) -> list[GroupProjection]:
        session = session_context.get()
        groups = (
            await self.db[self.collection_name]
            .find(filter, projections, session=session)
            .skip(offset)
            .limit(limit)
            .to_list(length=None)
        )
        return [GroupProjection(**group) for group in groups]

    async def check_next_page_exists(self, filter: dict[str, Any], offset: int, limit: int) -> bool:
        session = session_context.get()
        items = (
            await self.db[self.collection_name]
            .find(filter, session=session)
            .skip(offset + limit)
            .limit(1)
            .to_list(length=None)
        )
        return bool(items)

    async def update_group(self, group: UpdateGroup) -> PydanticObjectId:
        try:
            session = session_context.get()

            update_item_dict = group.model_dump()
            update_item_dict["updated_at"] = datetime.now(UTC)
            update_item_dict["last_session_id"] = get_session_id()

            set_access_dict = transform_access(group.set_access)
            unset_access_dict = transform_access(group.unset_access)

            db_item = await self.db[self.collection_name].update_one(
                {"_id": group.laui},
                {"$set": update_item_dict | set_access_dict, "$unset": unset_access_dict},
                session=session,
            )
            return db_item.upserted_id
        except Exception as e:
            raise e

    async def delete_group(self, group_laui: PydanticObjectId):
        try:
            session = session_context.get()
            await self.db[self.collection_name].delete_one({"_id": group_laui}, session=session)
        except Exception as e:
            raise e


async def get_group_repository(request: Request):
    return request.app.state.group_repository
