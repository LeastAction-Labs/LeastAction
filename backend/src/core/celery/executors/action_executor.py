# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import inspect
import sys
import traceback
from pathlib import Path
from typing import Any

from src.common.exceptions import (
    CeleryExecutionError,
    InvalidArgumentError,
    NotFoundError,
    UnprocessableEntityError,
)
from src.common.logger.logger import log_error, log_info
from src.core.celery.client import APIClient
from src.core.celery.schema import ActionRequest
from src.core.celery.utils import create_module_from_codeblock, load_module
from src.core.task.action.schema import ActionState
from src.core.task.schema import TaskUpdateData


class ActionExecutionService:
    def __init__(self, api_client: APIClient, action_dir: Path) -> None:
        self.api_client = api_client
        self.action_dir = action_dir
        self.action_dir.mkdir(parents=True, exist_ok=True)

    async def _get_action_item(
        self, action_laui: str, session_id: str, auth_token: str
    ) -> dict[str, Any]:
        try:
            action_item = await self.api_client.get_item(auth_token, action_laui, session_id)

            if not action_item:
                raise NotFoundError(
                    message=f"Action not found with laui: {action_laui}",
                    detail={"action_laui": action_laui, "session_id": session_id},
                )

            return action_item

        except NotFoundError:
            raise

        except Exception as e:
            log_error(
                "action",
                "ActionExecutionService",
                "_get_action_item",
                f"Failed to retrieve action item {action_laui}: {str(e)}",
            )
            raise UnprocessableEntityError(
                message="Failed to retrieve action item",
                detail={
                    "action_laui": action_laui,
                    "session_id": session_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )

    def _validate_action_module(self, action_module, action_laui: str) -> None:
        if not hasattr(action_module, "run"):
            available_attrs = [attr for attr in dir(action_module) if not attr.startswith("_")]
            raise CeleryExecutionError(
                message="Action module does not have a 'run' function",
                detail={"action_laui": action_laui, "available_attributes": available_attrs},
            )

        if not callable(action_module.run):
            raise CeleryExecutionError(
                message="Action module 'run' attribute is not callable",
                detail={"action_laui": action_laui},
            )

        if inspect.iscoroutinefunction(action_module.run):
            raise CeleryExecutionError(
                message="Action run() must be synchronous", detail={"action_laui": action_laui}
            )

    async def execute_action(self, la_action_object: ActionRequest) -> dict[str, Any]:
        action_files_path: list[Path] | None = None
        action_module = None
        status: str = ""

        log_info(
            "action",
            "ActionExecutionService",
            "execute_action",
            f"Starting action execution for laui={la_action_object.laui}",
        )

        try:
            action_item = await self._get_action_item(
                str(la_action_object.laui),
                la_action_object.session_id,
                la_action_object.user_access_token,
            )

            # Extract and validate codeblock
            codeblock = getattr(action_item, "codeblock", {})
            if not codeblock:
                raise NotFoundError(
                    message="No codeblock found for action",
                    detail={"action_laui": la_action_object.laui},
                )

            # Create and load module
            action_files_path = create_module_from_codeblock(
                codeblock, self.action_dir, la_action_object.session_id
            )
            if not action_files_path:
                raise UnprocessableEntityError(
                    message="No files created from codeblock",
                    detail={"action_laui": la_action_object.laui},
                )

            # Step 4: Load module
            main_action_module_path = action_files_path[0]

            log_info(
                "action",
                "ActionExecutionService",
                "execute_action",
                f"STEP 4: Loading module from {main_action_module_path}",
            )

            action_module = load_module(main_action_module_path)

            log_info(
                "action",
                "ActionExecutionService",
                "execute_action",
                f"STEP 4 COMPLETE: Module loaded. Name: {getattr(action_module, '__name__', 'Unknown')}",
            )

            # Step 5: Validate module
            log_info(
                "action",
                "ActionExecutionService",
                "execute_action",
                "STEP 5: Validating action module",
            )

            self._validate_action_module(action_module, str(la_action_object.laui))

            log_info(
                "action",
                "ActionExecutionService",
                "execute_action",
                "STEP 5 COMPLETE: Module validated successfully",
            )

            # Execute action
            action_object_dict = la_action_object.model_dump()
            result = action_module.run(action_object_dict, **la_action_object.action_variables)

            status = ActionState.SUCCESS if result else ActionState.ERROR
            log_info(
                "action",
                "ActionExecutionService",
                "execute_action",
                f"Action {la_action_object.laui} executed with result={result}, status={status}",
            )
            return {"result": result}

        except (NotFoundError, InvalidArgumentError, UnprocessableEntityError) as e:
            status = ActionState.ERROR
            log_error(
                "action",
                "ActionExecutionService",
                "execute_action",
                f"Known error occurred during execution: {type(e).__name__}",
            )
            log_error(
                "action",
                "ActionExecutionService",
                "execute_action",
                f"Error message: {e.message if hasattr(e, 'message') else str(e)}",
            )
            log_error(
                "action",
                "ActionExecutionService",
                "execute_action",
                f"Error details: {e.detail if hasattr(e, 'detail') else 'No details available'}",
            )
            log_error(
                "action",
                "ActionExecutionService",
                "execute_action",
                f"Traceback: {traceback.format_exc()}",
            )
            raise

        except CeleryExecutionError as e:
            status = ActionState.ERROR
            log_error(
                "action",
                "ActionExecutionService",
                "execute_action",
                f"Celery execution error: {type(e).__name__}",
            )
            log_error(
                "action",
                "ActionExecutionService",
                "execute_action",
                f"Error message: {e.message if hasattr(e, 'message') else str(e)}",
            )
            log_error(
                "action",
                "ActionExecutionService",
                "execute_action",
                f"Error details: {e.detail if hasattr(e, 'detail') else 'No details available'}",
            )
            log_error(
                "action",
                "ActionExecutionService",
                "execute_action",
                f"{type(e).__name__}: {e.message if hasattr(e, 'message') else str(e)}\n{traceback.format_exc()}",
            )
            raise

        except Exception as e:
            status = ActionState.ERROR
            log_error(
                "action",
                "ActionExecutionService",
                "execute_action",
                f"Unhandled exception: {str(e)}\n{traceback.format_exc()}",
            )
            raise CeleryExecutionError(
                message="Action execution failed",
                detail={
                    "action_laui": la_action_object.laui,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                },
            )

        finally:
            log_info("action", "ActionExecutionService", "execute_action", "Entering cleanup phase")
            try:
                if action_module and hasattr(action_module, "__name__"):
                    module_name = action_module.__name__
                    if module_name in sys.modules:
                        del sys.modules[module_name]
                        log_info(
                            "action",
                            "ActionExecutionService",
                            "execute_action",
                            f"Removed module {module_name} from sys.modules",
                        )

                if la_action_object.action_type != "create_actions":
                    # Fetch the latest task from the database to get current actions_status
                    # This prevents race conditions where concurrent updates overwrite each other
                    try:
                        latest_task = await self.api_client.get_item(
                            la_action_object.user_access_token,
                            str(la_action_object.task.get("laui")),
                        )
                        # Get actions_status from the latest task data
                        actions_status = latest_task.model_dump().get(
                            "actions_status",
                            {"pre_actions": [], "running_actions": [], "post_actions": []},
                        )
                    except Exception as e:
                        log_error(
                            "action",
                            "ActionExecutionService",
                            "execute_action",
                            f"Failed to fetch latest task for actions_status update: {e}. Using task from action object.",
                        )
                        # Fallback to the task from action object
                        actions_status = la_action_object.task.get(
                            "actions_status",
                            {"pre_actions": [], "running_actions": [], "post_actions": []},
                        )

                    # Ensure the action_type key exists
                    if la_action_object.action_type not in actions_status:
                        actions_status[la_action_object.action_type] = []

                    actions_status[la_action_object.action_type].append(
                        {
                            "laui": str(la_action_object.laui),
                            "name": la_action_object.name,
                            "status": status,
                        }
                    )
                    task_laui = await self.api_client.update_item(
                        la_action_object.user_access_token,
                        str(la_action_object.task.get("laui")),
                        TaskUpdateData(actions_status=actions_status),
                    )

                if action_files_path:
                    log_info(
                        "action",
                        "ActionExecutionService",
                        "execute_action",
                        f"Cleaning up {len(action_files_path)} files",
                    )
                    for file_path in action_files_path:
                        try:
                            if file_path.exists():
                                file_path.unlink(missing_ok=True)
                                log_info(
                                    "action",
                                    "ActionExecutionService",
                                    "execute_action",
                                    f"Deleted file {file_path}",
                                )
                        except Exception as e:
                            log_error(
                                "action",
                                "ActionExecutionService",
                                "execute_action",
                                f"Failed to delete file {file_path}: {type(e).__name__} - {str(e)}",
                            )

                log_info(
                    "action", "ActionExecutionService", "execute_action", "Cleanup phase complete"
                )
            except Exception as e:
                log_error(
                    "action",
                    "ActionExecutionService",
                    "execute_action",
                    f"Error in finally block - {str(e)}",
                )
