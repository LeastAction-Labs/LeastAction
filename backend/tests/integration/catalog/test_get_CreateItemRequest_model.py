# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from pydantic import __version__ as _pv

from src.common.config import Config
from src.common.logger.logger import initialize_logger
from src.core.catalog.config.schema.schema_manager import SchemaManager

PYDANTIC_MISSING_URL = f"https://errors.pydantic.dev/{'.'.join(_pv.split('.')[:2])}/v/missing"

# The pytestmark is needed for running anyio tests
# Documentation: https://anyio.readthedocs.io/en/stable/testing.html#creating-asynchronous-tests
pytestmark = pytest.mark.anyio


# testcases to check if the dynamic model is getting created as expected and it is validating stuff as expected.
# here we pass a valid item_type.json


@pytest.fixture(autouse=True)
def setup_test_item_type_model():
    config = Config()
    initialize_logger(config)
    file_path = Path.cwd().parent / "config/schema/test_item_type.json"
    sample_dict = _get_test_item_type_dict()
    sample_json = json.dumps(sample_dict)
    Path.write_text(file_path, sample_json)
    schema_manager = SchemaManager(item_type="test_item_type")
    CreateItemRequest = schema_manager.CreateItemRequest_model
    yield CreateItemRequest
    Path.unlink(file_path)


def test_valid_model(setup_test_item_type_model: Any):
    CreateItemRequest = setup_test_item_type_model
    valid_dict = {
        "name": "my_item",
        "is_root": True,
        "item_type": "test_item_type",
        "config_type": "system",
        "content": {"abc": "def"},
    }
    CreateItemRequest.model_validate(valid_dict)


def test_name_field_missing_model_fail(setup_test_item_type_model: Any):
    exception_raised = False
    try:
        CreateItemRequest = setup_test_item_type_model
        invalid_dict = {
            "is_root": True,
            "item_type": "test_item_type",
            "config_type": "system",
            "content": {"abc": "def"},
        }
        CreateItemRequest.model_validate(invalid_dict)
    except ValidationError as e:
        exception_raised = True
        print(e.errors())
        assert e.errors() == [
            {
                "type": "missing",
                "loc": ("name",),
                "msg": "Field required",
                "input": invalid_dict,
                "url": PYDANTIC_MISSING_URL,
            }
        ]
    finally:
        assert exception_raised == True


def test_type_specific_field_missing_model_fail(setup_test_item_type_model: Any):
    exception_raised = False
    try:
        CreateItemRequest = setup_test_item_type_model
        invalid_dict = {
            "name": "my_item",
            "is_root": True,
            "item_type": "test_item_type",
            "content": {"abc": "def"},
        }
        CreateItemRequest.model_validate(invalid_dict)
    except ValidationError as e:
        exception_raised = True
        assert e.errors() == [
            {
                "type": "missing",
                "loc": ("config_type",),
                "msg": "Field required",
                "input": invalid_dict,
                "url": PYDANTIC_MISSING_URL,
            }
        ]
    finally:
        assert exception_raised == True


def _get_test_item_type_dict():
    return {
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
        "projection_fields": ["name"],
        "unique_constraints": ["parent_laui", "name"],
        "indexes": [
            {"fields": ["tags"], "type": "multikey"},
            {"fields": ["name", "description"], "type": "text"},
        ],
    }
