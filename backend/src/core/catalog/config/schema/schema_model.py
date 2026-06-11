# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class DatatypeEnum(str, Enum):
    OBJECT_ID = "ObjectId"
    ARRAY = "array"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    OBJECT = "object"
    FLOAT = "float"
    INT = "int"
    STRING = "string"
    ENUM = "enum"
    ANY = "any"


class ColumnModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    datatype: DatatypeEnum
    required: bool
    enum_values: list[str] | None = None

    @model_validator(mode="after")
    def _validate_enum(self):
        if self.datatype == "enum" and not self.enum_values:
            raise ValidationError("enum_values must be provided when datatype is 'enum'")
        return self


class SchemaModel(BaseModel):
    columns: list[ColumnModel]
    projection_fields: list[str]
    unique_constraints: list[str]
    version_fields: list[str] = Field(default_factory=list)
    user_update_fields: list[str] = Field(default_factory=list)
    system_update_fields: list[str] = Field(default_factory=list)
