# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import traceback
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from fastapi import Request
from pydantic_mongo import PydanticObjectId
from pymongo.errors import OperationFailure

from src.common.context_vars.session_context import get_session_id
from src.common.context_vars.user_context import get_user_laui
from src.common.decorators.performance import performance_logger
from src.common.exceptions import NotFoundError
from src.common.logger.logger import log_error
from src.common.mutex import lock_multiple_docs
from src.common.types import LAUI
from src.common.utils import transform_access
from src.core.catalog.item.indexes import get_indexes
from src.core.catalog.item.schema import (
    CreateItem,
    CreateItemInDB,
    Item,
    ItemProjection,
    UpdateItem,
)
from src.core.db.transaction import session_context
from src.core.db.types import MongoDatabase
from src.core.task.schema import Task


class ItemRepository:
    def __init__(self, db: MongoDatabase):
        self.db = db
        self.collection_name = "items"
        self.account_laui = None

    async def create_index(self):
        indexes = get_indexes()
        try:
            await self.db[self.collection_name].create_indexes(indexes)
        except OperationFailure:
            await self.db[self.collection_name].drop_indexes()
            await self.db[self.collection_name].create_indexes(indexes)

    async def get_account_laui(self) -> LAUI | None:
        if self.account_laui:
            return self.account_laui
        items: list[ItemProjection] = await self.find_items(filter={"item_type": "folder.account"})
        if items:
            self.account_laui = items[0].laui
        return self.account_laui

    @performance_logger
    async def create_item(self, item: CreateItem) -> PydanticObjectId:
        try:
            session = session_context.get()
            item_db = CreateItemInDB(
                **item.model_dump(),
                created_at=datetime.now(UTC),
                created_by=PydanticObjectId(get_user_laui()),
                last_session_id=get_session_id(),
            )
            db_item = await self.db[self.collection_name].insert_one(
                item_db.model_dump(), session=session
            )
            return db_item.inserted_id
        except Exception as e:
            error_string = traceback.format_exc()
            log_error(
                "api", "item_repository", "create_item", f"Failed to create item, {error_string}"
            )
            log_error(
                "api_traceback",
                "item_repository",
                "create_item",
                f"Failed to create item, {error_string}",
            )
            raise e

    @performance_logger
    async def check_item_exists(
        self, filters: dict[str, Any], projections: dict[str, int] = {"_id": 1}
    ):
        try:
            session = session_context.get()
            item = await self.db[self.collection_name].find_one(
                filters, projections, session=session
            )
            exists = item is not None
            return exists
        except Exception as e:
            error_string = traceback.format_exc()
            log_error(
                "api",
                "item_repository",
                "check_item_exists",
                f"Failed to check item existence, {error_string}",
            )
            log_error(
                "api_traceback",
                "item_repository",
                "check_item_exists",
                f"Failed to check item existence, {error_string}",
            )
            raise e

    @performance_logger
    async def get_item(
        self,
        item_laui: PydanticObjectId,
        projections: dict[str, int] = {},
        include_deleted: bool = False,
    ) -> Item:
        if projections is None:
            projections = {}
        try:
            session = session_context.get()
            # Normalize laui to ObjectId to ensure consistent type matching
            normalized_laui = (
                ObjectId(item_laui) if not isinstance(item_laui, ObjectId) else item_laui
            )
            query = {"_id": normalized_laui}
            if not include_deleted:
                query["deleted_at"] = None  # Exclude soft-deleted items

            item = await self.db[self.collection_name].find_one(query, projections, session=session)

            if item is None:
                log_error(
                    "api", "item_repository", "get_item", f"Item not found with laui: {item_laui}"
                )
                log_error(
                    "api_traceback",
                    "item_repository",
                    "get_item",
                    f"Item not found with laui: {item_laui}",
                )
                raise NotFoundError(f"Item not found with laui: {item_laui}")

            return Item(**item)

        except Exception as e:
            error_string = traceback.format_exc()
            log_error("api", "item_repository", "get_item", f"Failed to get item, {error_string}")
            log_error(
                "api_traceback",
                "item_repository",
                "get_item",
                f"Failed to get item, {error_string}",
            )
            raise e

    @performance_logger
    async def get_multiple_items_by_laui(
        self,
        item_lauis: list[PydanticObjectId],
        projections: dict[str, int] = {},
        include_deleted: bool = False,
    ) -> list[ItemProjection]:
        try:
            session = session_context.get()
            # Convert all lauis to ObjectId to ensure consistent type matching
            normalized_lauis = [
                ObjectId(laui) if not isinstance(laui, ObjectId) else laui for laui in item_lauis
            ]
            query = {"_id": {"$in": normalized_lauis}}
            if not include_deleted:
                query["deleted_at"] = None  # Exclude soft-deleted items
            items_cursor = self.db[self.collection_name].find(query, projections, session=session)
            items_list = await items_cursor.to_list(length=None)

            return [ItemProjection(**item) for item in items_list]
        except Exception as e:
            error_string = traceback.format_exc()
            log_error(
                "api",
                "item_repository",
                "get_multiple_items_by_laui",
                f"Failed to get multiple items, {error_string}",
            )
            log_error(
                "api_traceback",
                "item_repository",
                "get_multiple_items_by_laui",
                f"Failed to get multiple items, {error_string}",
            )
            raise e

    @performance_logger
    async def get_item_by_pk(self, item_pk: str) -> Item:
        try:
            session = session_context.get()
            filter_object = {"pk": item_pk}
            db_item = await self.db[self.collection_name].find_one(filter_object, session=session)
            if db_item:
                return Item(**db_item)
            log_error(
                "api",
                "item_repository",
                "get_item_by_pk",
                f"Item not found with primary keys: {filter_object}",
            )
            log_error(
                "api_traceback",
                "item_repository",
                "get_item_by_pk",
                f"Item not found with primary keys: {filter_object}",
            )
            raise NotFoundError(f"item not found with primary keys: {filter_object}")
        except Exception as e:
            error_string = traceback.format_exc()
            log_error(
                "api",
                "item_repository",
                "get_item_by_pk",
                f"Failed to get item by pk, {error_string}",
            )
            log_error(
                "api_traceback",
                "item_repository",
                "get_item_by_pk",
                f"Failed to get item by pk, {error_string}",
            )
            raise e

    @performance_logger
    async def get_item_projection(
        self, item_laui: PydanticObjectId, projections: dict[str, int] = {"item_type": 1}
    ) -> ItemProjection:
        try:
            session = session_context.get()
            normalized_laui = (
                ObjectId(item_laui) if not isinstance(item_laui, ObjectId) else item_laui
            )
            projections["item_type"] = 1
            item = await self.db[self.collection_name].find_one(
                {"_id": normalized_laui}, projections, session=session
            )
            if item is None:
                log_error(
                    "api",
                    "item_repository",
                    "get_item_projection",
                    f"Item not found with laui: {item_laui}",
                )
                log_error(
                    "api_traceback",
                    "item_repository",
                    "get_item_projection",
                    f"Item not found with laui: {item_laui}",
                )
                raise NotFoundError(f"Item not found with laui: {item_laui}")
            return ItemProjection(**item)
        except Exception as e:
            error_string = traceback.format_exc()
            log_error(
                "api",
                "item_repository",
                "get_item_projection",
                f"Failed to get item_type, {error_string}",
            )
            log_error(
                "api_traceback",
                "item_repository",
                "get_item_projection",
                f"Failed to get item_type, {error_string}",
            )
            raise e

    @performance_logger
    async def find_items(
        self,
        filter: dict[str, Any],
        offset: int = 0,
        limit: int = 0,
        projections: dict[str, int] | None = {},
        sort_by: str | None = None,
        sort_order: str | None = "asc",
    ) -> list[ItemProjection]:
        try:
            session = session_context.get()
            sort_direction = 1 if sort_order != "desc" else -1
            sort_field = sort_by if sort_by else "created_at"
            items = (
                await self.db[self.collection_name]
                .find(filter, projections, session=session)
                .sort(sort_field, sort_direction)
                .skip(offset)
                .limit(limit)
                .to_list(length=None)
            )

            return [ItemProjection(**item) for item in items]
        except Exception as e:
            error_string = traceback.format_exc()
            log_error(
                "api", "item_repository", "find_items", f"Failed to find items, {error_string}"
            )
            log_error(
                "api_traceback",
                "item_repository",
                "find_items",
                f"Failed to find items, {error_string}",
            )
            raise e

    @performance_logger
    async def update_item(self, item: UpdateItem, versioning_required: bool) -> PydanticObjectId:
        async with lock_multiple_docs([item.laui]):
            try:
                session = session_context.get()

                if versioning_required:
                    item.version += 1

                update_item_dict = item.model_dump()
                update_item_dict["updated_at"] = datetime.now(UTC)
                update_item_dict["updated_by"] = PydanticObjectId(get_user_laui())
                update_item_dict["last_session_id"] = get_session_id()

                set_access_dict = transform_access(item.set_access) if item.set_access else {}
                unset_access_dict = transform_access(item.unset_access) if item.unset_access else {}

                normalized_laui = (
                    ObjectId(item.laui) if not isinstance(item.laui, ObjectId) else item.laui
                )
                db_item = await self.db[self.collection_name].update_one(
                    {"_id": normalized_laui},
                    {"$set": update_item_dict | set_access_dict, "$unset": unset_access_dict},
                    session=session,
                )

                return db_item.upserted_id
            except Exception as e:
                error_string = traceback.format_exc()
                log_error(
                    "api",
                    "item_repository",
                    "update_item",
                    f"Failed to update item, {error_string}",
                )
                log_error(
                    "api_traceback",
                    "item_repository",
                    "update_item",
                    f"Failed to update item, {error_string}",
                )
                raise e

    @performance_logger
    async def check_next_page_exists(self, filter: dict[str, Any], offset: int, limit: int) -> bool:
        try:
            session = session_context.get()
            items = (
                await self.db[self.collection_name]
                .find(filter, skip=offset + limit, limit=1, session=session)
                .to_list(length=None)
            )
            has_next = bool(items)
            return has_next
        except Exception as e:
            error_string = traceback.format_exc()
            log_error(
                "api",
                "item_repository",
                "check_next_page_exists",
                f"Failed to check next page, {error_string}",
            )
            log_error(
                "api_traceback",
                "item_repository",
                "check_next_page_exists",
                f"Failed to check next page, {error_string}",
            )
            raise e

    @performance_logger
    async def soft_delete_items(self, item_lauis: list[PydanticObjectId]):
        async with lock_multiple_docs(item_lauis):
            try:
                session = session_context.get()
                normalized_lauis = [
                    ObjectId(laui) if not isinstance(laui, ObjectId) else laui
                    for laui in item_lauis
                ]
                await self.db[self.collection_name].update_many(
                    {"_id": {"$in": normalized_lauis}},
                    {"$set": {"deleted_at": datetime.now(UTC)}},
                    session=session,
                )
            except Exception as e:
                error_string = traceback.format_exc()
                log_error(
                    "api",
                    "item_repository",
                    "soft_delete_items",
                    f"Failed to soft delete items, {error_string}",
                )
                log_error(
                    "api_traceback",
                    "item_repository",
                    "soft_delete_items",
                    f"Failed to soft delete items, {error_string}",
                )
                raise e

    @performance_logger
    async def get_trash_folder_laui(self) -> PydanticObjectId:
        try:
            session = session_context.get()
            trash_folder_dict = {"name": "trash", "item_type": "folder.trash"}
            trash_folder = await self.db[self.collection_name].find_one(
                trash_folder_dict, session=session
            )
            if not trash_folder:
                log_error(
                    "api", "item_repository", "get_trash_folder_laui", "trash folder not found"
                )
                log_error(
                    "api_traceback",
                    "item_repository",
                    "get_item_projection",
                    "trash folder not found",
                )
                raise NotFoundError(
                    "Trash folder not found in the database (expected item with name='trash' and item_type='folder.trash')"
                )
            return PydanticObjectId(trash_folder["_id"])
        except Exception as e:
            error_string = traceback.format_exc()
            log_error(
                "api",
                "item_repository",
                "get_trash_folder_laui",
                f"Failed to get trash folder laui, {error_string}",
            )
            log_error(
                "api_traceback",
                "item_repository",
                "get_trash_folder_laui",
                f"Failed to get trash folder laui, {error_string}",
            )
            raise e

    @performance_logger
    async def hard_delete_items(self, items_lauis: list[PydanticObjectId]):
        try:
            session = session_context.get()
            normalized_lauis = [
                ObjectId(laui) if not isinstance(laui, ObjectId) else laui for laui in items_lauis
            ]
            await self.db[self.collection_name].delete_many(
                {"_id": {"$in": normalized_lauis}}, session=session
            )
        except Exception as e:
            error_string = traceback.format_exc()
            log_error(
                "api",
                "item_repository",
                "hard_delete_items",
                f"Failed to hard delete items, {error_string}",
            )
            log_error(
                "api_traceback",
                "item_repository",
                "hard_delete_items",
                f"Failed to hard delete items, {error_string}",
            )
            raise e

    @performance_logger
    async def restore_items(self, item_lauis: list[PydanticObjectId]):
        async with lock_multiple_docs(item_lauis):
            try:
                session = session_context.get()
                normalized_lauis = [
                    ObjectId(laui) if not isinstance(laui, ObjectId) else laui
                    for laui in item_lauis
                ]
                await self.db[self.collection_name].update_many(
                    {"_id": {"$in": normalized_lauis}},
                    {"$set": {"deleted_at": None}},
                    session=session,
                )
            except Exception as e:
                error_string = traceback.format_exc()
                log_error(
                    "api",
                    "item_repository",
                    "restore_items",
                    f"Failed to restore items, {error_string}",
                )
                log_error(
                    "api_traceback",
                    "item_repository",
                    "restore_items",
                    f"Failed to restore items, {error_string}",
                )
                raise e

    @performance_logger
    async def batch_update_tasks(
        self, task_lauis: list[PydanticObjectId], update_fields: dict[str, Any]
    ) -> int:
        async with lock_multiple_docs(task_lauis):
            try:
                session = session_context.get()

                normalized_lauis = [
                    ObjectId(laui) if not isinstance(laui, ObjectId) else laui
                    for laui in task_lauis
                ]

                update_dict = {**update_fields}
                update_dict["updated_at"] = datetime.now(UTC)
                update_dict["updated_by"] = PydanticObjectId(get_user_laui())

                result = await self.db[self.collection_name].update_many(
                    {"_id": {"$in": normalized_lauis}}, {"$set": update_dict}, session=session
                )

                return result.modified_count
            except Exception as e:
                error_string = traceback.format_exc()
                log_error(
                    "api",
                    "item_repository",
                    "batch_update_tasks",
                    f"Failed to batch update tasks, {error_string}",
                )
                log_error(
                    "api_traceback",
                    "item_repository",
                    "batch_update_tasks",
                    f"Failed to batch update tasks, {error_string}",
                )
                raise e

    @performance_logger
    async def get_tasks_ready_to_run(self, project_laui: PydanticObjectId) -> list[Task]:
        try:
            session = session_context.get()
            current_time = datetime.now(UTC)

            # MongoDB aggregation pipeline to get tasks ready to run
            pipeline = [
                # Stage 1: Match tasks that meet basic criteria
                {
                    "$match": {
                        "item_type": "task",
                        "project_laui": project_laui,
                        "deleted_at": None,
                        "start_date": {"$lt": current_time},
                        "user_set_state": {"$ne": "cancel"},
                        "$and": [
                            {
                                "$or": [
                                    {"end_date": None},  # Use None, not null in Python
                                    {"$expr": {"$lte": ["$next_run_date", "$end_date"]}},
                                ]
                            },
                            {
                                "$or": [
                                    # Path A: Normal scheduled tasks
                                    {
                                        "state": {"$in": ["scheduled", "success", "created"]},
                                        "next_run_date": {"$lte": current_time},
                                    },
                                    # Path B: Retrying tasks
                                    {
                                        "$expr": {
                                            "$and": [
                                                {"$in": ["$state", ["error", "timeout"]]},
                                                {"$ne": ["$total_retries", 0]},
                                                {"$lt": ["$retry_number", "$total_retries"]},
                                                {
                                                    "$lte": [
                                                        {
                                                            "$add": [
                                                                "$last_run_date",
                                                                {
                                                                    "$multiply": [
                                                                        "$retry_interval",
                                                                        60000,
                                                                    ]
                                                                },
                                                            ]
                                                        },
                                                        current_time,
                                                    ]
                                                },
                                            ]
                                        }
                                    },
                                ]
                            },
                        ],
                    }
                },
                # Stage 4: Lookup the workflow (parent) to check its state
                {
                    "$lookup": {
                        "from": self.collection_name,
                        "localField": "parent_laui",
                        "foreignField": "_id",
                        "as": "workflow",
                    }
                },
                # Stage 5: Unwind workflow array (should be single item)
                {"$unwind": {"path": "$workflow", "preserveNullAndEmptyArrays": False}},
                # Stage 6: Filter out tasks whose workflow is not PAUSED
                {
                    "$match": {
                        "workflow.folder_metadata.state": {"$ne": "PAUSE"},
                    }
                },
                # Stage 7: Project only the task fields (remove workflow)
                {"$project": {"workflow": 0, "meets_retry_policy": 0}},
            ]

            tasks_cursor = await self.db[self.collection_name].aggregate(pipeline, session=session)
            tasks_list = await tasks_cursor.to_list(length=None)

            return [Task(**task) for task in tasks_list]
        except Exception as e:
            error_string = traceback.format_exc()
            log_error(
                "api",
                "item_repository",
                "get_tasks_ready_to_run",
                f"Failed to get tasks ready to run, {error_string}",
            )
            log_error(
                "api_traceback",
                "item_repository",
                "get_tasks_ready_to_run",
                f"Failed to get tasks ready to run, {error_string}",
            )
            raise e


def get_item_repository(request: Request) -> ItemRepository:
    return request.app.state.item_repo
