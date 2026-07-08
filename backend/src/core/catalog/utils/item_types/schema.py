# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from enum import Enum


class ItemCategory(Enum):
    ALL = "all"
    FOLDER = "folder"
    NON_FOLDER = "non_folder"


class ChildType(Enum):
    HARD = "hard"
    SOFT = "soft"
