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

from src.common.models import Access, AccessPatch


def coerce_set_access(access_patch: dict | None):
    if access_patch is None:
        return {}  # Return empty dict which will be coerced to Access()
    return access_patch.get("add", {})


def coerce_unset_access(access_patch: dict | None):
    if access_patch is None:
        return {}  # Return empty dict which will be coerced to Access()
    return access_patch.get("remove", {})


type SetAccess = Annotated[Access, BeforeValidator(coerce_set_access)]

type UnsetAccess = Annotated[Access, BeforeValidator(coerce_unset_access)]

type AccessPatchType = AccessPatch
