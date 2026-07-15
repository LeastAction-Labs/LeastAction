# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from typing import Annotated

from bson import ObjectId
from pydantic import AliasChoices, BeforeValidator, Field
from pydantic_mongo import PydanticObjectId


def ensure_str(input: ObjectId | PydanticObjectId) -> str:
    return str(input)


LAUI = Annotated[
    str, Field(validation_alias=AliasChoices("_id", "laui")), BeforeValidator(ensure_str)
]

iLAUI = PydanticObjectId
