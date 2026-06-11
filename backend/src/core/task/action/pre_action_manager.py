# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import UTC, datetime

from fastapi import Request

from src.common.context_vars.session_context import get_session_id
from src.common.logger.logger import log_error
from src.common.utils import load_system_config
from src.core.api.utils import convert_objectid_to_str
from src.core.catalog.service import CatalogService
from src.core.task.action.schema import ActionItem, Actions
from src.core.task.celery_orchestrator import CeleryOrchestrator
from src.core.task.schema import TaskValidationModel


class PreActionManager:
    def __init__(self, celery_orchestrator: CeleryOrchestrator, catalog_manager: CatalogService):
        self.timeout = int(load_system_config()["action_timeout_seconds"])
        self.celery_orchestrator = celery_orchestrator
        self.catalog_manager = catalog_manager

    async def _run_action_with_timeout(
        self,
        actions_list: list[ActionItem],
        action_type: str,
        user_laui: str,
        task: TaskValidationModel,
        wait_for_result: bool = False,
    ):
        if not actions_list:
            return True if wait_for_result else None

        for idx, action_item in enumerate(actions_list, 1):
            try:
                action_item.session_id = get_session_id()
                action_item.task = convert_objectid_to_str(task.model_dump()) if task else {}
                action_item.user_laui = user_laui
                action_item.timeout = max(self.timeout, action_item.timeout)
                action_item.action_type = action_type

                # Fetch connection content if connection_laui is provided
                if action_item.connection_laui:
                    try:
                        connection, e = await self.catalog_manager.safe_find_item(
                            action_item.connection_laui
                        )
                        if connection:
                            item_type = connection.item_type
                            connection_type = item_type.split(".")
                            if connection_type[0] != "connection":
                                log_error(
                                    "api",
                                    "PreActionManager",
                                    "_run_action_with_timeout",
                                    f"Invalid connection type for {action_item.connection_laui}: '{item_type}', expected 'connection.*'",
                                )
                                return False
                            action_item.connection = connection.content
                        else:
                            log_error(
                                "api",
                                "PreActionManager",
                                "_run_action_with_timeout",
                                f"Connection not found: {action_item.connection_laui}, reason: {str(e)}",
                            )
                            return False
                    except Exception as conn_error:
                        log_error(
                            "api",
                            "PreActionManager",
                            "_run_action_with_timeout",
                            f"Error fetching connection {action_item.connection_laui}: {str(conn_error)}",
                        )
                        return False
                action_item.action_type = action_type
                if idx == 1 and action_type == "pre_actions":
                    update_dict = {}
                    update_dict["last_system_updated_date"] = datetime.now(UTC)
                    update_dict["actions_status"] = {
                        "pre_actions": [],
                        "running_actions": [],
                        "post_actions": [],
                    }
                    await self.catalog_manager.update_task_item(task.laui, update_dict)
                async_result = await self.celery_orchestrator.run_action(action_item)

                if wait_for_result:
                    try:
                        current_result = async_result.get(timeout=self.timeout)

                        # Extract the result value from dict responses
                        if isinstance(current_result, dict) and "result" in current_result:
                            current_result = current_result["result"]

                        if not current_result:
                            log_error(
                                "api",
                                "PreActionManager",
                                "_run_action_with_timeout",
                                f"{action_type} {action_item.laui} returned False",
                            )
                            return False

                    except Exception as e:
                        log_error(
                            "api",
                            "PreActionManager",
                            "_run_action_with_timeout",
                            f"{action_type} {action_item.laui} timed out or failed: {str(e)}",
                        )
                        return False

            except Exception as e:
                log_error(
                    "api",
                    "PreActionManager",
                    "_run_action_with_timeout",
                    f"Error executing {action_type} {action_item.laui}: {str(e)}",
                )
                if wait_for_result:
                    return False

        return True if wait_for_result else None

    async def create_actions(
        self, la_actions_object: Actions, user_laui: str, task: TaskValidationModel | None = None
    ) -> bool:
        return await self._run_action_with_timeout(
            la_actions_object.create_actions, "create_actions", user_laui, task, True
        )

    async def pre_actions(
        self, la_actions_object: Actions, user_laui: str, task: TaskValidationModel | None
    ) -> bool:
        if not la_actions_object.pre_actions:
            return True
        return await self._run_action_with_timeout(
            la_actions_object.pre_actions,
            "pre_actions",
            user_laui,
            task,
            wait_for_result=True,
        )


def get_pre_action_manager(request: Request) -> PreActionManager:
    return request.app.state.pre_action_manager
