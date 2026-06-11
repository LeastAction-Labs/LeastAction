# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from enum import Enum
from typing import Any

from pydantic import BaseModel
from pydantic_mongo import PydanticObjectId

from src.core.task.schema import Task


class ConnectionQueue(BaseModel):
    name: str
    partition: str
    task_laui: PydanticObjectId


class SortOrder(str, Enum):
    ASC = "ascending"
    DESC = "descending"


class ConnectionMetrics(BaseModel):
    max_parallelism: int
    current_parallelism: int
    in_queue: int
    sort_dict: dict[str, SortOrder]


class ConnectionWithTasks(BaseModel):
    connection_laui: PydanticObjectId
    tasks: list[Task]
    sort_dict: dict[str, SortOrder] = {}
    content: dict[str, Any] = {}
