# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from enum import Enum, StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic_mongo import PydanticObjectId

from src.core.task.schema import TaskState

# ActionState mirrors TaskState — created dynamically so it stays in sync
# with any future state additions to the task schema.
ActionState = Enum(
    "ActionState",
    {member.name: member.value for member in TaskState},
    type=str,
)


class ActionType(StrEnum):
    PRE_ACTIONS = "pre_actions"
    POST_ACTIONS = "post_actions"
    RUNNING_ACTIONS = "running_actions"
    CREATE_ACTIONS = "create_actions"


class BaseAction(BaseModel):
    pass


class ActionItem(BaseAction):
    model_config = ConfigDict(extra="allow")
    laui: PydanticObjectId
    name: str = ""
    session_id: str | None = None
    connection_laui: str | None = None
    connection: dict | None = Field(default_factory=dict)
    action_variables: dict[str, Any]
    user_laui: str | None = None
    sla: int | None = None
    timeout: int | None = 0
    action_type: str | None = None


class Actions(BaseModel):
    create_actions: list[ActionItem] = []
    pre_actions: list[ActionItem] = []
    running_actions: list[ActionItem] = []
    post_actions: list[ActionItem] = []
