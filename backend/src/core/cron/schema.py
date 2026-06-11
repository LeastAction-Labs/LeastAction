# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from pydantic_mongo import PydanticObjectId


class CronAction(StrEnum):
    START = "START"
    STOP = "STOP"


class CronStatus(StrEnum):
    STARTED = "STARTED"
    RUNNING = "RUNNING"
    STOP = "STOP"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


class CronManageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_laui: PydanticObjectId
    action: CronAction


class CronManageResponse(BaseModel):
    success: bool
    message: str
    project_laui: str
    action: CronAction
