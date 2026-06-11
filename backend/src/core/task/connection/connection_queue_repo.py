# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import UTC, datetime

from pydantic_mongo import PydanticObjectId

from src.common.context_vars.user_context import get_user_laui
from src.common.exceptions import NotFoundError
from src.common.logger.logger import log_error
from src.common.mutex import lock_multiple_docs
from src.core.db.service import MongoDatabase
from src.core.db.transaction import session_context, transactional
from src.core.task.connection.schema import (
    ConnectionMetrics,
    ConnectionQueue,
    ConnectionWithTasks,
)
from src.core.task.schema import TaskState, TaskValidationModel


class ConnectionQueueRepository:
    def __init__(self, db: MongoDatabase):
        self.db = db

    async def get_connection_queue(self, task: TaskValidationModel) -> ConnectionQueue:
        try:
            cq = await self.db.items.find_one(
                {"item_type": "connection_queue", "task_laui": PydanticObjectId(task.laui)}
            )
            if not cq:
                return None
            return ConnectionQueue(**cq)
        except Exception as e:
            raise e

    async def get_connection_metrics(self, connection_laui: PydanticObjectId) -> ConnectionMetrics:
        try:
            connection = await self.db.items.find_one({"_id": connection_laui})
            if not connection:
                raise NotFoundError(f"connection not found with laui: {connection_laui}")
            return ConnectionMetrics(**connection)
        except Exception as e:
            raise e

    async def get_existing_task_lauis(self, task_lauis: list[str]) -> set[str]:
        try:
            # Convert string IDs to PydanticObjectIds for the query
            object_ids = [PydanticObjectId(laui) for laui in task_lauis]

            cursor = self.db.items.find(
                {"item_type": "connection_queue", "task_laui": {"$in": object_ids}},
                projection={"task_laui": 1, "_id": 0},
            )

            docs = await cursor.to_list(length=len(task_lauis))
            # Return a set of strings for O(1) lookup performance later
            existing_lauis = {str(doc["task_laui"]) for doc in docs}

            return existing_lauis

        except Exception as e:
            log_error(
                "API",
                "connection_queue_repo",
                "get_existing_task_lauis",
                f"Error during bulk existence check: {e}",
            )
            raise e

    @transactional
    async def enqueue_tasks(self, connection_with_tasks: ConnectionWithTasks):
        async with lock_multiple_docs(
            [task.laui for task in connection_with_tasks.tasks]
            + [connection_with_tasks.connection_laui]
        ):
            try:
                session = session_context.get()

                tasks = connection_with_tasks.tasks

                cq_docs_to_insert = [
                    {
                        "name": task.name,
                        "partition": task.partition,
                        "task_laui": PydanticObjectId(task.laui),
                        "item_type": "connection_queue",
                        "parent_laui": task.connection_laui,
                        "created_at": datetime.now(UTC),
                        "access": {},
                    }
                    for task in tasks
                ]
                cqs = await self.db.items.insert_many(
                    cq_docs_to_insert, ordered=True, session=session
                )

                link_docs_to_insert = [
                    {
                        "parent_laui": task.connection_laui,
                        "child_laui": cq_id,
                        "child_type": "connection_queue",
                        "parent_type": "connection",
                        "true_parent": True,
                    }
                    for task, cq_id in zip(tasks, cqs.inserted_ids, strict=False)
                ]
                await self.db.links.insert_many(link_docs_to_insert, session=session)

                task_lauis = [PydanticObjectId(task.laui) for task in tasks]
                await self.db.items.update_many(
                    {"_id": {"$in": task_lauis}},
                    {
                        "$set": {
                            "state": TaskState.QUEUED_FOR_CONNECTION,
                            "last_system_updated_date": datetime.now(UTC),
                            "updated_at": datetime.now(UTC),
                            "updated_by": PydanticObjectId(get_user_laui()),
                        }
                    },
                    session=session,
                )

                connection_laui = connection_with_tasks.connection_laui
                await self.db.items.update_one(
                    {"_id": connection_laui}, {"$inc": {"in_queue": len(tasks)}}, session=session
                )
            except Exception as e:
                log_error(
                    "API",
                    "connection_queue_repo",
                    "enqueue_tasks",
                    f"error in enqueue transaction for connection laui: {connection_with_tasks.connection_laui}, error: {e}",
                )
                raise e

    async def get_connections_with_tasks(self):
        try:
            session = session_context.get()

            pipeline = [
                {"$match": {"item_type": "connection_queue"}},
                {"$group": {"_id": "$parent_laui", "task_lauis": {"$push": "$task_laui"}}},
                {
                    "$lookup": {
                        "from": "items",
                        "localField": "_id",
                        "foreignField": "_id",
                        "as": "connection_doc",
                    }
                },
                {
                    "$lookup": {
                        "from": "items",
                        "localField": "task_lauis",
                        "foreignField": "_id",
                        "as": "tasks",
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "connection_laui": "$_id",
                        "tasks": 1,
                        "sort_dict": {"$arrayElemAt": ["$connection_doc.sort_dict", 0]},
                        "content": {"$arrayElemAt": ["$connection_doc.content", 0]},
                    }
                },
            ]

            result = await (
                await self.db.items.aggregate(pipeline=pipeline, session=session)
            ).to_list(length=None)

            return [ConnectionWithTasks(**entry) for entry in result]
        except Exception as e:
            log_error(
                "API",
                "connection_queue_repo",
                "get_connections_with_tasks",
                f"error fetching connections with tasks, error: {e}",
            )
            raise e

    @transactional
    async def update_connection_with_tasks(
        self, connection_with_tasks: ConnectionWithTasks, pop_count: int
    ):
        async with lock_multiple_docs(
            [connection_with_tasks.connection_laui]
            + [task.laui for task in connection_with_tasks.tasks]
        ):
            try:
                session = session_context.get()

                tasks = connection_with_tasks.tasks
                task_lauis = [PydanticObjectId(task.laui) for task in tasks]

                await self.db.items.update_many(
                    {"_id": {"$in": task_lauis}},
                    {
                        "$set": {
                            "state": TaskState.QUEUED_IN_REDIS,
                            "last_system_updated_date": datetime.now(UTC),
                            "updated_at": datetime.now(UTC),
                            "updated_by": PydanticObjectId(get_user_laui()),
                        }
                    },
                    session=session,
                )

                connection_laui = connection_with_tasks.connection_laui
                await self.db.items.update_one(
                    {"_id": connection_laui},
                    {"$inc": {"current_parallelism": pop_count, "in_queue": -pop_count}},
                    session=session,
                )
            except Exception as e:
                log_error(
                    "API",
                    "connection_queue_repo",
                    "update_connection_with_tasks",
                    f"error in update transaction for connection laui: {connection_with_tasks.connection_laui}, error: {e}",
                )
                raise e

    @transactional
    async def dequeue_task(self, task: TaskValidationModel):
        async with lock_multiple_docs([task.connection_laui]):
            try:
                session = session_context.get()

                cq = await self.db.items.find_one_and_delete(
                    {"task_laui": PydanticObjectId(task.laui), "item_type": "connection_queue"},
                    {"_id": 1},
                    session=session,
                )
                if not cq:
                    log_error(
                        "API",
                        "connection_queue_repo",
                        "dequeue_task",
                        f"connection_queue not found for task_laui: {task.laui}",
                    )
                    raise NotFoundError(f"connection_queue not found for task_laui:{task.laui}")

                await self.db.links.delete_one({"child_laui": cq["_id"]}, session=session)

                connection_laui = task.connection_laui
                await self.db.items.update_one(
                    {"_id": connection_laui}, {"$inc": {"current_parallelism": -1}}, session=session
                )
            except Exception as e:
                log_error(
                    "API",
                    "connection_queue_repo",
                    "dequeue_task",
                    f"error in dequeue transaction for task laui: {task.laui}, error: {e}",
                )
                raise e
