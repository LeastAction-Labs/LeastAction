# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from collections import defaultdict
from typing import Any

from pydantic import ValidationError

from src.common.exceptions import SchemaError
from src.common.utils import compare_common_keys
from src.core.catalog.config.constants_mappers import (
    db_fields,
    expected_schemas,
    system_field_schemas,
    system_fields,
)
from src.core.catalog.config.schema.schema_model import ColumnModel, SchemaModel


class SchemaValidation:
    def __init__(self, schema_dict: dict[str, Any]):
        self._schema_dict = schema_dict

    def _extra_validations(self):
        error_dict = defaultdict(dict)
        item_fields = self.get_item_fields()
        schema_columns = self._schema_dict.get("columns")
        invalid_column_fields = []

        if schema_columns is not None and isinstance(schema_columns, list):
            name_column = {}
            for index, field in enumerate(schema_columns):
                try:
                    field_model = ColumnModel.model_validate(field)
                    if field_model.name in system_fields or field_model.name in db_fields:
                        invalid_column_fields.append(field["name"])
                    if field["name"] == "name":
                        name_column = field
                except ValidationError as e:
                    field_name = f"column_{index + 1}"
                    if field.get("name"):
                        field_name = field["name"]
                    error_dict["item_field_schemas"][field_name] = e.errors()

            if name_column:
                if not compare_common_keys(
                    name_column, expected_schemas["name"], ["name", "datatype", "required"]
                ):
                    error_dict["columns"]["expected_columns"] = {
                        "name": {"type": "invalid", "expected": expected_schemas["name"]}
                    }

            else:
                error_dict["columns"]["expected_columns"] = {
                    "name": {"type": "missing", "expected": expected_schemas["name"]}
                }

        if invalid_column_fields:
            error_dict["columns"] = {
                "invalid_fields": invalid_column_fields,
                "info": "custom validations cannot be provided for system fields",
            }

        schema_unique_constraints = self._schema_dict.get("unique_constraints")
        if schema_unique_constraints is not None and isinstance(schema_unique_constraints, list):
            schema_unique_constraints = set(schema_unique_constraints)
            if schema_unique_constraints:
                invalid_primary_keys = [
                    field for field in schema_unique_constraints if field not in item_fields
                ]
                if invalid_primary_keys:
                    error_dict["unique_constraints"] = {
                        "invalid_fields": invalid_primary_keys,
                        "info": "only item_fields can be part of unique_constraints",
                    }
            else:
                error_dict["unique_constraints"] = "unique_constraints cannot be empty"

        schema_projection_fields = self._schema_dict.get("projection_fields")
        if schema_projection_fields is not None and isinstance(schema_projection_fields, list):
            schema_projection_fields = set(schema_projection_fields)
            if schema_projection_fields:
                invalid_projection_fields = [
                    field for field in schema_projection_fields if field not in item_fields
                ]
                if invalid_projection_fields:
                    error_dict["projection_fields"] = {
                        "invalid_fields": invalid_projection_fields,
                        "info": "only item_fields can be part of projection_fields",
                    }

        schema_version_fields = self._schema_dict.get("version_fields")
        if schema_version_fields is not None and isinstance(schema_version_fields, list):
            schema_version_fields = set(schema_version_fields)
            if schema_version_fields:
                invalid_version_fields = [
                    field for field in schema_version_fields if field not in item_fields
                ]
                if invalid_version_fields:
                    error_dict["version_fields"] = {
                        "invalid_fields": invalid_version_fields,
                        "info": "only item_fields can be part of version_fields",
                    }

        for system_field, system_field_schema in system_field_schemas.items():
            try:
                ColumnModel.model_validate(system_field_schema)
            except ValidationError as e:
                error_dict["system_field_schemas"][system_field] = e.errors()

        if error_dict:
            error_dict["item_fields"] = item_fields
            error_dict["system_fields"] = system_fields

        return error_dict

    def get_item_fields(self) -> list[str]:
        item_fields = list(system_fields + db_fields)
        schema_columns = self._schema_dict.get("columns")
        if schema_columns is not None and isinstance(schema_columns, list):
            for field in schema_columns:
                try:
                    ColumnModel.model_validate(field)
                    item_fields.append(field["name"])
                except ValidationError:
                    continue
        return item_fields

    def validate_schema_dict(self):
        errors = {}
        try:
            SchemaModel.model_validate(self._schema_dict)
        except ValidationError as e:
            validation_errors = e.errors()
            for error in validation_errors:
                if error["type"] == "missing" and len(error["loc"]) == 1:
                    if error["loc"] in (("unique_constraints",), ("projection_fields",)):
                        error["expected"] = {"datatype": "list", "list_item_datatype": "string"}
                    else:
                        error["expected"] = {
                            "datatype": "list",
                            "list_item_datatype": {
                                "name": "string",
                                "datatype": "string",
                                "required": "boolean",
                            },
                        }
            errors["validation_errors"] = validation_errors

        finally:
            business_logic_errors = self._extra_validations()
            if business_logic_errors:
                errors["business_logic_errors"] = dict(business_logic_errors)

            if errors:
                raise SchemaError(
                    message=f"Schema validation failed: {len(errors)} error type(s) found",
                    detail=errors,
                )
