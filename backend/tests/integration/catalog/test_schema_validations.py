# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import pytest
from pydantic import __version__ as _pv

from src.common.exceptions import SchemaError
from src.core.catalog.config.constants_mappers import system_fields
from src.core.catalog.config.schema.schema_validations import SchemaValidation

PYDANTIC_MISSING_URL = f"https://errors.pydantic.dev/{'.'.join(_pv.split('.')[:2])}/v/missing"

pytestmark = pytest.mark.anyio


def test_system_field_in_columns_fail():
    exception_raised = False
    try:
        schema_validation = SchemaValidation(schema_dict=schema_with_system_field_in_column)
        schema_validation.validate_schema_dict()
    except SchemaError as e:
        print(exception_raised)
        exception_raised = True
        assert e.detail == {
            "business_logic_errors": {
                "columns": {
                    "invalid_fields": ["parent_laui"],
                    "info": "custom validations cannot be provided for system fields",
                },
                "item_fields": schema_validation.get_item_fields(),
                "system_fields": system_fields,
            }
        }
    finally:
        print(exception_raised)
        assert exception_raised == True


def test_invalid_field_in_unique_constraints_and_system_field_in_columns_fail():
    exception_raised = False
    try:
        schema_validation = SchemaValidation(
            schema_dict=schema_with_system_field_in_column_and_invalid_field_in_unique_constraints
        )
        schema_validation.validate_schema_dict()
    except SchemaError as e:
        exception_raised = True
        assert e.detail == {
            "business_logic_errors": {
                "columns": {
                    "invalid_fields": ["parent_laui"],
                    "info": "custom validations cannot be provided for system fields",
                },
                "unique_constraints": {
                    "invalid_fields": ["last_name"],
                    "info": "only item_fields can be part of unique_constraints",
                },
                "item_fields": schema_validation.get_item_fields(),
                "system_fields": system_fields,
            }
        }
    finally:
        assert exception_raised == True


def test_invalid_field_in_unique_constraints_and_invalid_field_in_projection_fields_and_system_field_in_columns_fail():
    exception_raised = False
    try:
        schema_validation = SchemaValidation(
            schema_dict=schema_with_invalid_field_in_unique_constraints_and_invalid_field_in_projection_fields_and_system_field_in_columns
        )
        schema_validation.validate_schema_dict()
    except SchemaError as e:
        exception_raised = True
        assert e.detail == {
            "business_logic_errors": {
                "columns": {
                    "invalid_fields": ["parent_laui"],
                    "info": "custom validations cannot be provided for system fields",
                },
                "unique_constraints": {
                    "invalid_fields": ["last_name"],
                    "info": "only item_fields can be part of unique_constraints",
                },
                "projection_fields": {
                    "invalid_fields": ["last_name"],
                    "info": "only item_fields can be part of projection_fields",
                },
                "item_fields": schema_validation.get_item_fields(),
                "system_fields": system_fields,
            }
        }
    finally:
        assert exception_raised == True


def test_empty_unique_constraints_fail():
    exception_raised = False
    try:
        schema_validation = SchemaValidation(schema_dict=schema_with_empty_unique_constraints)
        schema_validation.validate_schema_dict()
    except SchemaError as e:
        exception_raised = True
        assert e.detail == {
            "business_logic_errors": {
                "unique_constraints": "unique_constraints cannot be empty",
                "item_fields": schema_validation.get_item_fields(),
                "system_fields": system_fields,
            }
        }
    finally:
        assert exception_raised == True


def test_missing_unique_constraints_fail():
    exception_raised = False
    try:
        schema_validation = SchemaValidation(schema_dict=schema_with_missing_unique_constraints)
        schema_validation.validate_schema_dict()
    except SchemaError as e:
        exception_raised = True
        assert e.detail == {
            "validation_errors": [
                {
                    "type": "missing",
                    "loc": ("unique_constraints",),
                    "msg": "Field required",
                    "input": schema_with_missing_unique_constraints,
                    "url": PYDANTIC_MISSING_URL,
                    "expected": {"datatype": "list", "list_item_datatype": "string"},
                }
            ]
        }
    finally:
        assert exception_raised == True


def test_missing_columns_invalid_field_in_projection_fields_fail():
    exception_raised = False
    try:
        schema_validation = SchemaValidation(
            schema_dict=schema_with_missing_columns_invalid_field_in_projection_fields
        )
        schema_validation.validate_schema_dict()
    except SchemaError as e:
        exception_raised = True
        assert e.detail == {
            "validation_errors": [
                {
                    "type": "missing",
                    "loc": ("columns",),
                    "msg": "Field required",
                    "input": schema_with_missing_columns_invalid_field_in_projection_fields,
                    "url": PYDANTIC_MISSING_URL,
                    "expected": {
                        "datatype": "list",
                        "list_item_datatype": {
                            "name": "string",
                            "datatype": "string",
                            "required": "boolean",
                        },
                    },
                }
            ],
            "business_logic_errors": {
                "projection_fields": {
                    "invalid_fields": ["name"],
                    "info": "only item_fields can be part of projection_fields",
                },
                "item_fields": schema_validation.get_item_fields(),
                "system_fields": system_fields,
            },
        }
    finally:
        assert exception_raised == True


schema_with_system_field_in_column = {
    "columns": [
        {
            "name": "name",
            "datatype": "string",
            "required": True,
            "min_length": 1,
            "max_length": 255,
            "regex": "^[a-zA-Z0-9_\\-\\s]+$",
            "description": "Folder name with alphanumeric characters, spaces, hyphens, and underscores",
        },
        {
            "name": "description",
            "datatype": "string",
            "required": False,
            "max_length": 1000,
            "default": [],
            "description": "Optional folder description",
        },
        {
            "name": "parent_laui",
            "datatype": "string",
            "required": False,
            "description": "Reference to parent folder for hierarchical structure",
            "foreign_key": {"collection": "folder", "field": "_id"},
        },
        {
            "name": "config_type",
            "datatype": "string",
            "required": True,
            "default": ["system", "task", "UIaction", "taskAction"],
            "description": "",
        },
        {"name": "content", "datatype": "object", "required": True, "description": ""},
    ],
    "projection_fields": ["name"],
    "unique_constraints": ["parent_laui", "name"],
    "indexes": [
        {"fields": ["tags"], "type": "multikey"},
        {"fields": ["name", "description"], "type": "text"},
    ],
}


schema_with_system_field_in_column_and_invalid_field_in_unique_constraints = {
    "columns": [
        {
            "name": "name",
            "datatype": "string",
            "required": True,
            "min_length": 1,
            "max_length": 255,
            "regex": "^[a-zA-Z0-9_\\-\\s]+$",
            "description": "Folder name with alphanumeric characters, spaces, hyphens, and underscores",
        },
        {
            "name": "description",
            "datatype": "string",
            "required": False,
            "max_length": 1000,
            "default": [],
            "description": "Optional folder description",
        },
        {
            "name": "parent_laui",
            "datatype": "string",
            "required": False,
            "description": "Reference to parent folder for hierarchical structure",
            "foreign_key": {"collection": "folder", "field": "_id"},
        },
        {
            "name": "config_type",
            "datatype": "string",
            "required": True,
            "default": ["system", "task", "UIaction", "taskAction"],
            "description": "",
        },
        {"name": "content", "datatype": "object", "required": True, "description": ""},
    ],
    "unique_constraints": ["name", "last_name"],
    "projection_fields": ["parent_laui", "name"],
    "indexes": [
        {"fields": ["tags"], "type": "multikey"},
        {"fields": ["name", "description"], "type": "text"},
    ],
}

schema_with_invalid_field_in_unique_constraints_and_invalid_field_in_projection_fields_and_system_field_in_columns = {
    "columns": [
        {
            "name": "name",
            "datatype": "string",
            "required": True,
            "min_length": 1,
            "max_length": 255,
            "regex": "^[a-zA-Z0-9_\\-\\s]+$",
            "description": "Folder name with alphanumeric characters, spaces, hyphens, and underscores",
        },
        {
            "name": "description",
            "datatype": "string",
            "required": False,
            "max_length": 1000,
            "default": [],
            "description": "Optional folder description",
        },
        {
            "name": "parent_laui",
            "datatype": "string",
            "required": False,
            "description": "Reference to parent folder for hierarchical structure",
            "foreign_key": {"collection": "folder", "field": "_id"},
        },
        {
            "name": "config_type",
            "datatype": "string",
            "required": True,
            "default": ["system", "task", "UIaction", "taskAction"],
            "description": "",
        },
        {"name": "content", "datatype": "object", "required": True, "description": ""},
    ],
    "unique_constraints": ["name", "last_name"],
    "projection_fields": ["parent_laui", "name", "last_name"],
    "indexes": [
        {"fields": ["tags"], "type": "multikey"},
        {"fields": ["name", "description"], "type": "text"},
    ],
}

schema_with_empty_unique_constraints = {
    "columns": [
        {
            "name": "name",
            "datatype": "string",
            "required": True,
            "min_length": 1,
            "max_length": 255,
            "regex": "^[a-zA-Z0-9_\\-\\s]+$",
            "description": "Folder name with alphanumeric characters, spaces, hyphens, and underscores",
        },
        {
            "name": "description",
            "datatype": "string",
            "required": False,
            "max_length": 1000,
            "default": [],
            "description": "Optional folder description",
        },
        {
            "name": "config_type",
            "datatype": "string",
            "required": True,
            "default": ["system", "task", "UIaction", "taskAction"],
            "description": "",
        },
        {"name": "content", "datatype": "object", "required": True, "description": ""},
    ],
    "unique_constraints": [],
    "projection_fields": ["parent_laui", "name"],
    "indexes": [
        {"fields": ["tags"], "type": "multikey"},
        {"fields": ["name", "description"], "type": "text"},
    ],
}

schema_with_missing_unique_constraints = {
    "columns": [
        {
            "name": "name",
            "datatype": "string",
            "required": True,
            "min_length": 1,
            "max_length": 255,
            "regex": "^[a-zA-Z0-9_\\-\\s]+$",
            "description": "Folder name with alphanumeric characters, spaces, hyphens, and underscores",
        },
        {
            "name": "description",
            "datatype": "string",
            "required": False,
            "max_length": 1000,
            "default": [],
            "description": "Optional folder description",
        },
        {
            "name": "config_type",
            "datatype": "string",
            "required": True,
            "default": ["system", "task", "UIaction", "taskAction"],
            "description": "",
        },
        {"name": "content", "datatype": "object", "required": True, "description": ""},
    ],
    "projection_fields": ["parent_laui", "name"],
    "indexes": [
        {"fields": ["tags"], "type": "multikey"},
        {"fields": ["name", "description"], "type": "text"},
    ],
}

schema_with_missing_columns_invalid_field_in_projection_fields = {
    "projection_fields": ["name"],
    "unique_constraints": ["item_type"],
}
