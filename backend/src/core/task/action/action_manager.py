# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from typing import Any

from fastapi import Request

from src.common.context_vars.session_context import get_session_id
from src.common.logger.logger import log_error
from src.common.utils import load_system_config
from src.core.api.utils import convert_objectid_to_str
from src.core.celery.client import APIClient
from src.core.task.action.schema import ActionItem, Actions


class ActionManager:
    def __init__(self, api_client: APIClient, action_task: Any):
        self.api_client = api_client
        self.action_task = action_task
        self.timeout = int(load_system_config()["action_timeout_seconds"])

    async def _run_action_with_timeout(
        self,
        actions_list: list[ActionItem],
        action_type: str,
        user_access_token: str,
        system_access_token: str,
        task: dict[str, Any],
    ):
        if not actions_list:
            return None

        for _idx, action_item in enumerate(actions_list, 1):
            try:
                action_item.session_id = get_session_id()
                if task:
                    action_item.task = convert_objectid_to_str(task)
                action_item.user_laui = None  # Not needed in ActionManager, token passed directly
                action_item.timeout = max(self.timeout, action_item.timeout)

                # Fetch connection content if connection_laui is provided
                if action_item.connection_laui:
                    try:
                        connection = await self.api_client.get_item(
                            user_access_token, action_item.connection_laui
                        )
                        if connection:
                            item_type = connection.get("item_type", "")
                            connection_type = item_type.split(".")
                            if connection_type[0] != "connection":
                                log_error(
                                    "api",
                                    "ActionManager",
                                    "_run_action_with_timeout",
                                    f"Invalid connection type for {action_item.connection_laui}: '{item_type}', expected 'connection.*'",
                                )
                                continue
                            action_item.connection = connection.get("content", "")
                        else:
                            log_error(
                                "api",
                                "ActionManager",
                                "_run_action_with_timeout",
                                f"Connection not found: {action_item.connection_laui}",
                            )
                    except Exception as conn_error:
                        log_error(
                            "api",
                            "ActionManager",
                            "_run_action_with_timeout",
                            f"Error fetching connection {action_item.connection_laui}: {str(conn_error)}",
                        )

                try:
                    action_data = action_item.model_dump(mode="json")
                    action_data["user_access_token"] = user_access_token
                    action_data["action_type"] = action_type

                    self.action_task.apply_async(
                        args=[action_data, system_access_token],
                        ignore_result=False,
                        queue=self.action_task.queue,
                        soft_time_limit=action_item.timeout,
                    )
                except Exception as e:
                    log_error(
                        "api",
                        "ActionManager",
                        "_run_action_with_timeout",
                        f"Failed to queue {action_type} {action_item.laui}: {str(e)}",
                    )
                    raise

            except Exception as e:
                log_error(
                    "api",
                    "ActionManager",
                    "_run_action_with_timeout",
                    f"Error executing {action_type} {action_item.laui}: {str(e)}",
                )

        return None

    async def running_actions(
        self,
        la_actions_object: Actions,
        user_access_token: str,
        system_access_token: str,
        task: dict[str, Any],
    ) -> None:
        if not la_actions_object.running_actions:
            return
        await self._run_action_with_timeout(
            la_actions_object.running_actions,
            "running_actions",
            user_access_token,
            system_access_token,
            task,
        )

    async def post_actions(
        self,
        la_actions_object: Actions,
        user_access_token: str,
        system_access_token: str,
        task: dict[str, Any],
    ) -> None:
        if not la_actions_object.post_actions:
            return
        await self._run_action_with_timeout(
            la_actions_object.post_actions,
            "post_actions",
            user_access_token,
            system_access_token,
            task,
        )


def get_action_manager(request: Request) -> ActionManager:
    return request.app.state.action_manager
