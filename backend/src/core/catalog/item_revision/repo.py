# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import UTC, datetime

from fastapi import Request
from pydantic_mongo import PydanticObjectId

from src.common.exceptions import NotFoundError
from src.common.logger.logger import log_error
from src.core.catalog.item_revision.schema import (
    CreateItemRevision,
    CreateItemRevisionInDB,
    ItemRevision,
    ItemRevisionProjection,
)
from src.core.db.transaction import session_context
from src.core.db.types import MongoDatabase


class ItemRevisionRepository:
    def __init__(self, db: MongoDatabase):
        self.db = db
        self.collection_name = "item_revisions"

    async def get_item_revision(self, item_laui: PydanticObjectId, version: int) -> ItemRevision:
        try:
            session = session_context.get()
            item_revision = await self.db[self.collection_name].find_one(
                {"item_laui": item_laui, "version": version}, session=session
            )
            if item_revision is None:
                raise NotFoundError(f"item_revision not found with {item_laui} and {version}")
            return ItemRevision(**item_revision)
        except Exception as e:
            log_error("api", "item_revision_repository", "_get_item_revision", str(e))
            log_error("api_traceback", "item_revision_repository", "_get_item_revision", str(e))
            raise e from e

    async def _get_item_type(self, item_laui: PydanticObjectId):
        try:
            session = session_context.get()
            item_revision = await self.db[self.collection_name].find_one(
                {"item_laui": item_laui}, {"item_type": 1}, session=session
            )
            if item_revision:
                item_type = item_revision["item_type"]
                return item_type
            else:
                raise NotFoundError(f"item revisions with {item_laui} not found")
        except Exception as e:
            log_error("api", "item_revision_repository", "_get_item_type", str(e))
            log_error("api_traceback", "item_revision_repository", "_get_item_type", str(e))
            raise e from e

    async def create_item_revision(self, item: CreateItemRevision) -> PydanticObjectId:
        try:
            session = session_context.get()
            create_item_in_db = CreateItemRevisionInDB(
                **item.model_dump(), created_at=datetime.now(UTC)
            )
            db_item = await self.db[self.collection_name].insert_one(
                create_item_in_db.model_dump(), session=session
            )
            return db_item.inserted_id
        except Exception as e:
            log_error("api", "item_revision_repository", "create_item_revision", str(e))
            log_error("api_traceback", "item_revision_repository", "create_item_revision", str(e))
            raise e from e

    async def get_item_revisons(
        self,
        item_laui: PydanticObjectId,
        projection_fields: set[str],
    ) -> list[ItemRevisionProjection]:
        try:
            session = session_context.get()
            projection_fields.update({"item_laui", "version"})
            projection_object = dict.fromkeys(projection_fields, 1)
            item_revisions = (
                await self.db[self.collection_name]
                .find({"item_laui": item_laui}, projection_object, session=session)
                .to_list(length=None)
            )
            return [ItemRevisionProjection(**item_revision) for item_revision in item_revisions]
        except Exception as e:
            log_error("api", "item_revision_repository", "get_item_revisons", str(e))
            log_error("api_traceback", "item_revision_repository", "get_item_revisons", str(e))
            raise e from e


def get_item_revision_repository(request: Request):
    return request.app.state.item_revision_repository
