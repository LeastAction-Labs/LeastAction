# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import os
from enum import Enum


class ENV(Enum):
    TEST = "test"
    PROD = "prod"
    DEV = "dev"


def get_env() -> ENV:
    env = os.getenv("ENV")
    if env is None:
        return ENV.PROD
    return ENV(env)
