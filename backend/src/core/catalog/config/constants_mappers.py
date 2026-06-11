# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic_mongo import PydanticObjectId

system_fields = [
    "item_type",
    "parent_laui",
    "is_root",
    "access_patch",
    "laui",
    "project_laui",
    "account_laui",
]
system_field_schemas = {
    "item_type": {"name": "item_type", "required": True, "datatype": "string"},
    "access_patch": {
        "name": "access_patch",
        "required": False,
        "datatype": "object",
        "default": {
            "add": {"owners": {}, "editors": {}, "viewers": {}},
            "remove": {"owners": {}, "editors": {}, "viewers": {}},
        },
    },
    "parent_laui": {
        "name": "parent_laui",
        "required": False,
        "datatype": "ObjectId",
        "default": None,
    },
    "is_root": {"name": "is_root", "required": False, "datatype": "boolean", "default": False},
    "project_laui": {
        "name": "project_laui",
        "required": False,
        "datatype": "ObjectId",
        "default": None,
    },
    "account_laui": {
        "name": "account_laui",
        "required": False,
        "datatype": "ObjectId",
        "default": None,
    },
}

immutable_system_fields = [
    "item_type",
    "is_root",
    "parent_laui",
    "laui",
    "project_laui",
    "account_laui",
]
mutable_system_fields = ["access_patch"]

db_fields = [
    "created_at",
    "updated_at",
    "access",
    "version",
    "deleted_at",
    "pk",
    "created_by",
    "updated_by",
]

parent_laui_is_root_rules = {
    "valid_requests": [
        {"is_root": True},
        {"is_root": False, "parent_laui": "valid objectid string"},
        {"parent_laui": "valid objectid string"},
    ],
    "info": [
        "If value passed for is_root is true then parent_laui cannot be present.",
        "If value passed for is_root is false or is_root is null then parent_laui must be present.",
    ],
}

expected_schemas = {
    "name": {"name": "name", "required": True, "datatype": "string"},
}

types_mapper = {
    "ObjectId": PydanticObjectId,
    "array": list[str],
    "array[ObjectId]": list[PydanticObjectId],
    "boolean": bool,
    "datetime": datetime,
    "object": dict[str, Any],
    "float": float,
    "int": int,
    "string": str,
    "enum": str,  # Base type for enums, will be converted to Literal
    "any": Any,
}


def create_enum_type(enum_values: list[str]) -> type:
    """Create a dynamic Enum type from list of values"""
    return Enum("DynamicEnum", {val: val for val in enum_values}, type=str)
