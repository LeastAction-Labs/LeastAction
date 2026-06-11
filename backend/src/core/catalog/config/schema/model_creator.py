# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, create_model, model_validator

from src.common.exceptions import UnprocessableEntityError
from src.common.logger.logger import log_error
from src.core.catalog.config.constants_mappers import (
    system_field_schemas,
    types_mapper,
)

from .schema_model import ColumnModel, SchemaModel

_IGNORE_ACCOUNT_AND_PROEJCT_LAUI = ["connection_queue"]
_IGNORE_PROEJCT_LAUI = ["chat_history"]


@model_validator(mode="after")
def _validate_create_item_data(self) -> Any:
    if self.is_root and self.parent_laui:
        log_error(
            "api",
            "model_creator",
            "_validate_create_item_data",
            "Validation error: root item has parent_laui set.",
        )
        log_error(
            "api_traceback",
            "model_creator",
            "_validate_create_item_data",
            "Validation error: root item has parent_laui set.",
        )
        raise UnprocessableEntityError(
            message="Invalid root item structure",
            detail="A root item cannot have a parent folder assigned to it.",
        )

    if not self.is_root and not self.parent_laui:
        log_error(
            "api",
            "model_creator",
            "_validate_create_item_data",
            "Validation error: non root item missing parent_laui.",
        )
        log_error(
            "api_traceback",
            "model_creator",
            "_validate_create_item_data",
            "Validation error: non root item missing parent_laui.",
        )
        raise UnprocessableEntityError(
            message="Missing parent folder",
            detail="Non root items must have a parent folder assigned.",
        )

    item_type = getattr(self, "item_type", None) or ""
    if self.is_root:
        self.project_laui = None
        self.account_laui = None
        return self
    if item_type in _IGNORE_ACCOUNT_AND_PROEJCT_LAUI:
        self.project_laui = None
        self.account_laui = None
        return self
    elif item_type in _IGNORE_PROEJCT_LAUI:
        self.project_laui = None
        if not getattr(self, "account_laui", None):
            raise UnprocessableEntityError(
                message="Missing account_laui",
                detail=f"'{item_type}' must have an account_laui attached.",
            )
        return self
    if item_type.startswith("folder."):
        _account_structural = {"folder.trash", "folder.users", "folder.user"}
        if item_type == "folder.account":
            self.project_laui = None
            self.account_laui = None
        elif item_type == "folder.project":
            self.project_laui = None
            if not getattr(self, "account_laui", None):
                raise UnprocessableEntityError(
                    message="Missing account_laui",
                    detail="A project folder must have an account_laui",
                )
        elif item_type in _account_structural:
            self.project_laui = None
            if not getattr(self, "account_laui", None):
                raise UnprocessableEntityError(
                    message="Missing account_laui",
                    detail=f"'{item_type}' must have an account_laui attached.",
                )
        else:
            if not getattr(self, "project_laui", None):
                raise UnprocessableEntityError(
                    message="Missing project_laui",
                    detail=f"'{item_type}' must have a project_laui attached.",
                )
            if not getattr(self, "account_laui", None):
                raise UnprocessableEntityError(
                    message="Missing account_laui",
                    detail=f"'{item_type}' must have an account_laui attached.",
                )
    else:
        if not getattr(self, "project_laui", None):
            raise UnprocessableEntityError(
                message="Missing project_laui",
                detail=f"'{item_type}' must have a project_laui attached.",
            )
        if not getattr(self, "account_laui", None):
            raise UnprocessableEntityError(
                message="Missing account_laui",
                detail=f"'{item_type}' must have an account_laui attached.",
            )

    return self


def create_item_model(schema_model: SchemaModel):
    item_fields = {}

    # Add system fields
    for system_field_schema in system_field_schemas.values():
        column = ColumnModel(**system_field_schema)
        data_field_type = types_mapper[column.datatype]

        if column.required:
            item_fields[column.name] = (data_field_type, ...)
        else:
            default_value = (
                column.get("default", None)
                if hasattr(column, "get")
                else getattr(column, "default", None)
            )
            # Use Field(default_factory=...) for mutable defaults (dict, list)
            if isinstance(default_value, (dict, list)):
                if isinstance(default_value, dict):
                    item_fields[column.name] = (
                        Optional[data_field_type],
                        Field(default_factory=dict),
                    )
                else:  # list
                    item_fields[column.name] = (
                        Optional[data_field_type],
                        Field(default_factory=list),
                    )
            else:
                item_fields[column.name] = (Optional[data_field_type], default_value)

    # Add schema-specific fields
    schema_columns = schema_model.columns
    for column in schema_columns:
        # Handle enum types
        if column.datatype == "enum":
            enum_values = getattr(column, "enum_values", [])
            data_field_type = Literal[tuple(enum_values)]
        else:
            # Handle regular types
            data_field_type = types_mapper.get(column.datatype)
            if not data_field_type:
                raise UnprocessableEntityError(
                    message=f"Unknown data type '{column.datatype}' for field '{column.name}'",
                )

        # Build string constraints from schema (max_length, min_length)
        str_kwargs: dict = {}
        if column.datatype == "string":
            max_len = getattr(column, "max_length", None)
            min_len = getattr(column, "min_length", None)
            if max_len is not None:
                str_kwargs["max_length"] = max_len
            if min_len is not None:
                str_kwargs["min_length"] = min_len

        # Set field with proper optional handling
        if column.required:
            item_fields[column.name] = (data_field_type, Field(..., **str_kwargs))
        else:
            # Get default value from column if available
            default_value = getattr(column, "default", None)
            # Use Field(default_factory=...) for mutable defaults (dict, list)
            if isinstance(default_value, (dict, list)):
                if isinstance(default_value, dict):
                    item_fields[column.name] = (
                        Optional[data_field_type],
                        Field(default_factory=dict, **str_kwargs),
                    )
                else:  # list
                    item_fields[column.name] = (
                        Optional[data_field_type],
                        Field(default_factory=list, **str_kwargs),
                    )
            else:
                item_fields[column.name] = (
                    Optional[data_field_type],
                    Field(default=default_value, **str_kwargs),
                )

    CreateItemRequest = create_model(
        "CreateItemRequest",
        __base__=BaseModel,
        __validators__={"create_item_custom_validations": _validate_create_item_data},
        **item_fields,
    )
    return CreateItemRequest
