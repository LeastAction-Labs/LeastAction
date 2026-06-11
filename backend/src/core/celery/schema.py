# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from typing import Any

from pydantic import ConfigDict, Field

from src.core.task.action.schema import ActionItem
from src.core.task.schema import Task


class ActionRequest(ActionItem):
    session_id: str = "no-session"
    task_result: dict[str, Any] | None = Field(default_factory=dict)
    model_config = ConfigDict(extra="allow")
    user_access_token: str


class TaskRequest(Task):
    user_access_token: str
    pass
