# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import inspect
from types import ModuleType
from typing import Any

from src.common.exceptions import CeleryExecutionError, InvalidOperatorError
from src.core.celery.schema import TaskRequest


class OperatorExecutor:
    def __init__(self, operator_module: ModuleType, task: TaskRequest):
        self.module = operator_module
        self.task = task
        self.client: Any | None = None
        self.result: Any | None = None
        self.completion_details: Any | None = None
        self.cancelled: bool = False

    def validate(self) -> None:
        required = ["initialize", "run", "check_completion", "finish"]
        missing = []
        for name in required:
            if not hasattr(self.module, name):
                missing.append(name)
            elif not callable(getattr(self.module, name)):
                missing.append(f"{name} (not callable)")

        if missing:
            raise InvalidOperatorError(
                message="Operator module is missing required methods",
                detail={
                    "operator_laui": self.task.operator_laui,
                    "missing_methods": missing,
                },
            )

        if inspect.iscoroutinefunction(self.module.run):
            raise InvalidOperatorError(
                message=f"Operator {self.task.operator_laui} run() must be synchronous (async functions are not supported)",
                detail={
                    "operator_laui": self.task.operator_laui,
                    "reason": "Async run() is not allowed.",
                },
            )

    def initialize(self) -> Any:
        try:
            # Override exclude to include payload and connection fields
            least_action_task_object = self.task.model_dump(exclude=set())
            self.client = self.module.initialize(least_action_task_object)
            return self.client
        except Exception as e:
            raise CeleryExecutionError(
                message="Failed to initialize operator",
                detail={"operator_laui": self.task.operator_laui, "error": str(e)},
            )

    def run(self) -> Any:
        if self.client is None:
            raise CeleryExecutionError(
                message="Operator client is not available (cancelled or not initialized)",
                detail={"operator_laui": self.task.operator_laui},
            )

        try:
            # Override exclude to include payload and connection fields
            least_action_task_object = self.task.model_dump(exclude=set())
            self.result = self.module.run(least_action_task_object, self.client)
            return self.result
        except Exception as e:
            raise CeleryExecutionError(
                message="Failed to run operator",
                detail={"operator_laui": self.task.operator_laui, "error": str(e)},
            )

    def check_completion(self) -> Any:
        try:
            # Override exclude to include payload and connection fields
            least_action_task_object = self.task.model_dump(exclude=set())
            self.completion_details = self.module.check_completion(
                least_action_task_object, self.client, self.result
            )
            return self.completion_details
        except Exception as e:
            raise CeleryExecutionError(
                message="Failed to check completion",
                detail={"operator_laui": self.task.operator_laui, "error": str(e)},
            )

    def finish(self) -> None:
        try:
            if self.client:
                # Override exclude to include payload and connection fields
                least_action_task_object = self.task.model_dump(exclude=set())
                self.module.finish(
                    least_action_task_object, self.client, self.completion_details, self.result
                )
        except Exception:
            pass
        finally:
            self.client = None
