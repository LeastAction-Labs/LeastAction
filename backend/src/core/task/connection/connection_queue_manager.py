# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import asyncio

from aioredlock import LockError
from pydantic_mongo import PydanticObjectId
from pymongo.errors import OperationFailure

from src.common.decorators.performance import performance_logger
from src.common.exceptions import NotFoundError
from src.common.logger.logger import log_error, log_warning
from src.core.db.transaction import session_context
from src.core.task.connection.connection_queue_repo import ConnectionQueueRepository
from src.core.task.connection.schema import ConnectionWithTasks, SortOrder
from src.core.task.schema import Task, TaskState, TaskValidationModel


class ConnectionQueueManager:
    def __init__(self, connection_queue_repo: ConnectionQueueRepository):
        self.connection_queue_repo = connection_queue_repo

    @performance_logger
    async def get_connection_queue(self, task: TaskValidationModel):
        return await self.connection_queue_repo.get_connection_queue(task)

    @performance_logger
    async def dequeue_task(self, task: TaskValidationModel):
        max_retries = 5
        for attempt in range(max_retries):
            try:
                await self.connection_queue_repo.dequeue_task(task)
                return
            except (OperationFailure, LockError) as e:
                log_warning("API", "connection_queue_manager", "dequeue_task", f"db error: {e}")
                wait_time = 0.1 * (2**attempt)
                await asyncio.sleep(wait_time)
                session_context.set(None)
            except NotFoundError:
                if attempt < max_retries - 1:
                    wait_time = 0.1 * (2**attempt)
                    await asyncio.sleep(wait_time)
                else:
                    log_error(
                        "API",
                        "connection_queue_manager",
                        "dequeue_task",
                        f"connection_queue not found for task {task.laui} after {max_retries} retries — entry already consumed",
                    )
                    return

    @performance_logger
    async def load_balance_tasks(self, incoming_tasks: list[TaskValidationModel]) -> list[Task]:
        new_tasks = await self._filter_already_queued(incoming_tasks) if incoming_tasks else []
        connections_with_tasks = self._group_by_connection(new_tasks)

        for connection_with_tasks in connections_with_tasks:
            await self._enqueue_tasks(connection_with_tasks)

        connections_with_tasks = await self.connection_queue_repo.get_connections_with_tasks()

        runnable_tasks: list[Task] = []
        for connection_with_tasks in connections_with_tasks:
            runnable = await self._pick_runnable_tasks(connection_with_tasks)
            runnable_tasks.extend(runnable)

        return runnable_tasks

    @performance_logger
    async def _filter_already_queued(
        self, tasks: list[TaskValidationModel]
    ) -> list[TaskValidationModel]:
        all_lauis = [task.laui for task in tasks]
        existing_lauis = await self.connection_queue_repo.get_existing_task_lauis(all_lauis)
        filtered = [task for task in tasks if task.laui not in existing_lauis]

        return filtered

    @performance_logger
    def _group_by_connection(self, tasks: list[TaskValidationModel]) -> list[ConnectionWithTasks]:
        groups: dict[PydanticObjectId, ConnectionWithTasks] = {}
        for task in tasks:
            if task.connection_laui not in groups:
                groups[task.connection_laui] = ConnectionWithTasks(
                    connection_laui=task.connection_laui, tasks=[]
                )
            groups[task.connection_laui].tasks.append(task)
        return list(groups.values())

    def _sort_tasks(self, tasks: list[Task], sort_dict: dict[str, SortOrder]) -> list[Task]:
        sorted_tasks = tasks
        for sort_by, order in reversed(list(sort_dict.items())):
            sorted_tasks = sorted(
                sorted_tasks,
                key=lambda task: getattr(task, sort_by, 0),
                reverse=(order == SortOrder.DESC),
            )
        return sorted_tasks

    @performance_logger
    async def _enqueue_tasks(self, connection_with_tasks: ConnectionWithTasks):
        max_retries = 5
        for attempt in range(max_retries):
            try:
                await self.connection_queue_repo.enqueue_tasks(connection_with_tasks)
                return
            except (OperationFailure, LockError) as e:
                log_warning(
                    "API", "connection_queue_manager", "_enqueue_tasks", f"db error, retrying: {e}"
                )
                wait_time = 0.1 * (2**attempt)
                await asyncio.sleep(wait_time)
                session_context.set(None)
            except Exception as e:
                raise e

    @performance_logger
    async def _pick_runnable_tasks(self, connection_with_tasks: ConnectionWithTasks) -> list[Task]:
        queued_tasks = [
            task
            for task in connection_with_tasks.tasks
            if task.state == TaskState.QUEUED_FOR_CONNECTION
        ]
        sorted_tasks = self._sort_tasks(queued_tasks, connection_with_tasks.sort_dict)

        pop_count = await self._update_connection_with_tasks(
            connection_laui=connection_with_tasks.connection_laui, sorted_tasks=sorted_tasks
        )

        selected_tasks = sorted_tasks[:pop_count]

        for task in selected_tasks:
            task.connection = connection_with_tasks.content

        return selected_tasks

    @performance_logger
    async def _update_connection_with_tasks(
        self,
        connection_laui: PydanticObjectId,
        sorted_tasks: list[Task],
    ) -> int:
        max_retries = 5
        for attempt in range(max_retries):
            try:
                connection_metrics = await self.connection_queue_repo.get_connection_metrics(
                    connection_laui
                )
                available_parallelism = (
                    connection_metrics.max_parallelism - connection_metrics.current_parallelism
                )
                pop_count = min(available_parallelism, connection_metrics.in_queue)
                connection_with_tasks_for_update = ConnectionWithTasks(
                    connection_laui=connection_laui, tasks=sorted_tasks[:pop_count]
                )
                await self.connection_queue_repo.update_connection_with_tasks(
                    connection_with_tasks=connection_with_tasks_for_update, pop_count=pop_count
                )
                return pop_count
            except (OperationFailure, LockError) as e:
                log_warning(
                    "API", "connection_queue_manager", "_enqueue_tasks", f"db error, retrying: {e}"
                )
                wait_time = 0.1 * (2**attempt)
                await asyncio.sleep(wait_time)
                session_context.set(None)
