# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from pydantic import ValidationError

from src.common.exceptions import SchemaError, UnprocessableEntityError
from src.common.logger.logger import log_error
from src.core.catalog.config.constants_mappers import (
    parent_laui_is_root_rules,
    system_field_schemas,
)
from src.core.catalog.config.schema import model_creator, schema_loader
from src.core.catalog.config.schema.schema_model import SchemaModel
from src.core.catalog.config.schema.schema_validations import SchemaValidation


class SchemaManager:
    def __init__(self, item_type: str):

        try:
            self._schema_dict = schema_loader.load_json(item_type)
            self._schema_validations: SchemaValidation = SchemaValidation(self._schema_dict)
            self._schema_validations.validate_schema_dict()
            self._schema_model = SchemaModel(**self._schema_dict)
            self.primary_keys = set(self._schema_model.unique_constraints) | {"item_type"}
            self.projection_fields = set(self._schema_model.projection_fields) | {
                "item_type",
                "deleted_at",
            }
            self.version_fields = set(self._schema_model.version_fields)
            self.user_update_fields = set(self._schema_model.user_update_fields)
            self.system_update_fields = set(self._schema_model.system_update_fields)
            self.CreateItemRequest_model = model_creator.create_item_model(self._schema_model)

        except SchemaError as e:
            log_error(
                "api",
                "schema_manager",
                "__init__",
                "Schema validation failed",
            )
            log_error(
                "api_traceback",
                "schema_manager",
                "__init__",
                f"Schema error while initializing item type {item_type}: {e}",
            )
            raise UnprocessableEntityError(
                message="Schema validation failed",
                detail={
                    "summary": f"errors found in {item_type}.json",
                    "validation_context": e.detail,
                },
            )

    def get_validation_error_message(self, validation_error: ValidationError):
        errors = validation_error.errors()

        for error in errors:
            error_column = error["loc"][0]
            expected_format = next(
                (
                    column.model_dump()
                    for column in self._schema_model.columns
                    if column.name == error_column
                ),
                {},
            )
            error["expected_format"] = expected_format

        errors.append(
            {
                "parent_laui": system_field_schemas["parent_laui"],
                "is_root": system_field_schemas["is_root"],
                "rules": parent_laui_is_root_rules,
            }
        )
        return errors
