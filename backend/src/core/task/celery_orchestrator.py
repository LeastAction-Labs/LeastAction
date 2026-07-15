# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from bson import ObjectId
from celery.result import AsyncResult
from fastapi import Request

from src.common.exceptions import NotFoundError
from src.common.logger.logger import log_error
from src.core.api.utils import convert_objectid_to_str
from src.core.celery.registry.actions import execute_action
from src.core.celery.registry.crons import run_cron
from src.core.celery.registry.tasks import execute_task
from src.core.celery.schema import Task
from src.core.iam.session.service import SessionService
from src.core.iam.user.service import UserService
from src.core.task.action.schema import ActionItem


class CeleryOrchestrator:
    def __init__(self, session_service: SessionService, user_service: UserService):
        self.session_service = session_service
        self.user_service = user_service
        self.system_token = ""

    async def _get_system_access_token(self) -> str:
        user_doc = await self.user_service.user_repo.db["users"].find_one(
            {"email": "system@leastactionlabs.com"}
        )
        if not user_doc:
            log_error(
                "api", "CeleryOrchestrator", "_get_system_access_token", "System user not found"
            )
            raise NotFoundError("System user (system@leastactionlabs.com) not found in database")

        system_access_token = user_doc.get("system_access_token")
        if not system_access_token:
            log_error(
                "api",
                "CeleryOrchestrator",
                "_get_system_access_token",
                "System access token not found",
            )
            raise NotFoundError("System access token not found for system user")

        return system_access_token

    async def _generate_access_token(self, user_laui: str, expires_in_hours: int = 72) -> str:
        user = await self.user_service.find_user(laui=ObjectId(user_laui))
        if not user:
            log_error(
                "api",
                "CeleryOrchestrator",
                "_generate_access_token",
                f"User not found: {user_laui}",
            )
            raise NotFoundError(f"User not found for laui: {user_laui}")

        return self.session_service.generate_access_token(
            user=user, expires_in_hours=expires_in_hours
        )

    async def run_task(self, task: Task) -> AsyncResult:
        try:
            if not self.system_token:
                self.system_token = await self._get_system_access_token()
            user_laui = str(getattr(task, "updated_by", None) or getattr(task, "created_by", None))
            user_access_token = await self._generate_access_token(user_laui)

            task_data = convert_objectid_to_str(task.model_dump())
            task_data["user_access_token"] = user_access_token

            result = execute_task.apply_async(
                args=[task_data, self.system_token],
                ignore_result=False,
                queue=execute_task.queue,
            )
            return result.id
        except Exception as e:
            log_error(
                "api",
                "CeleryOrchestrator",
                "run_task",
                f"Failed to queue task {task.laui}: {str(e)}",
            )
            raise

    async def run_action(self, action: ActionItem) -> AsyncResult:
        try:
            if not self.system_token:
                self.system_token = await self._get_system_access_token()
            if not action.user_laui:
                raise ValueError("user_laui is required for action execution")

            user_access_token = await self._generate_access_token(action.user_laui)

            action_data = action.model_dump(mode="json")
            action_data["user_access_token"] = user_access_token

            result = execute_action.apply_async(
                args=[action_data, self.system_token],
                ignore_result=False,
                queue=execute_action.queue,
                soft_time_limit=action.timeout,
            )
            return result
        except Exception as e:
            log_error(
                "api",
                "CeleryOrchestrator",
                "run_action",
                f"Failed to queue action {action.laui}: {str(e)}",
            )
            raise

    async def run_cron(self, project_laui: ObjectId, interval: int) -> AsyncResult:
        try:
            if not self.system_token:
                self.system_token = await self._get_system_access_token()
            serialized_project_laui = str(project_laui)
            result = run_cron.apply_async(
                args=[serialized_project_laui, interval, self.system_token],
                ignore_result=False,
                queue=run_cron.queue,
            )
            return result
        except Exception as e:
            log_error("api", "CeleryOrchestrator", "run_cron", f"Failed to start cron: {str(e)}")
            raise

    # def cancel_execution(self, task_id: str):
    #     # graceful cancel (cleanup possible)
    #     app.control.revoke(task_id, terminate=False)

    # def force_cancel_execution(self, task_id: str):
    #     # emergency kill (NO cleanup)
    #     app.control.revoke(task_id, terminate=True, signal="SIGKILL")


def get_celery_orchestrator(request: Request) -> CeleryOrchestrator:
    return request.app.state.celery_orchestrator
