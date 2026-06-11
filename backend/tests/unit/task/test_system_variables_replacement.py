# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import json
import logging
from datetime import datetime

import pytest
from bson import ObjectId

from src.common.config import Config
from src.common.logger.logger import get_logger_manager, initialize_logger
from src.core.task.config.config_manager import ConfigManager
from src.core.task.schema import TaskValidationModel

pytestmark = pytest.mark.anyio


@pytest.fixture
def real_config():
    """Load actual config and ensure logs directory exists"""
    config = Config()
    config.logs_dir.mkdir(parents=True, exist_ok=True)
    return config


@pytest.fixture(autouse=True)
def setup_logger(real_config):
    """Initialize logger before each test"""
    logging.disable(logging.CRITICAL)
    initialize_logger(real_config)
    yield
    manager = get_logger_manager()
    manager.clear_loggers()


@pytest.fixture
def config_manager():
    return ConfigManager()


def test_process_task_execution():
    """
    This test case checks the main functionality of process_task_execution for placeholder replacement.

    The task already has a final merged config with all parameters.
    process_task_execution should replace placeholders in payload with:
    1. Parameters from task.config["parameters"]
    2. Builtin system variables (ds, ts)
    """
    config_manager = ConfigManager()

    # Payload with placeholders to be replaced
    payload_content = {
        "database": {
            "host": "{{DB_HOST}}",
            "port": "{{DB_PORT}}",
            "connection": "{{DB_HOST}}:{{DB_PORT}}",
        },
        "logging": {"level": "{{LOG_LEVEL}}"},
        "retry": {"count": "{{retry_count}}", "delay": "{{retry_delay}}"},
        "timing": {"timeout": "{{timeout}}"},
        "builtin": {"date": "{{current_date}}", "timestamp": "{{current_timestamp}}"},
        "missing": {
            "unknown_param": "{{this_does_not_exist}}",
            "another_unknown": "{{missing_var}}",
        },
    }

    # Task with final merged config (already merged from workflow_configs, task_configs, and task.config)
    sample_task = TaskValidationModel(
        name="test_task",
        laui=ObjectId(),
        item_type="task",
        parent_laui=ObjectId(),
        operator_laui=ObjectId(),
        connection_laui=ObjectId(),
        project_laui=ObjectId(),
        account_laui=ObjectId(),
        state="queued_in_redis",
        config={
            "parameters": {
                "DB_HOST": "localhost",  # Final merged value
                "DB_PORT": "5433",  # Final merged value
                "LOG_LEVEL": "WARNING",  # Final merged value
                "timeout": 600,  # Final merged value
                "retry_count": 5,  # Final merged value
                "retry_delay": 60,  # Final merged value
            }
        },
        payload=json.dumps(payload_content),  # Convert dict to JSON string
        connection={},
    )

    task = config_manager.process_task_execution(task=sample_task)

    # Parse the JSON string payload back to dict for assertion
    result_payload = json.loads(task.payload) if isinstance(task.payload, str) else task.payload

    # print("Processed payload:")
    # print(json.dumps(result_payload, indent=2))

    current_date = datetime.now().strftime("%Y-%m-%d")

    # Check the structure and most values
    assert result_payload["database"] == {
        "host": "localhost",
        "port": "5433",
        "connection": "localhost:5433",
    }
    assert result_payload["logging"] == {"level": "WARNING"}
    assert result_payload["retry"] == {"count": "5", "delay": "60"}
    assert result_payload["timing"] == {"timeout": "600"}
    assert result_payload["missing"] == {
        "unknown_param": "{{ this_does_not_exist }}",
        "another_unknown": "{{ missing_var }}",
    }

    # Check builtin values (current_date/current_timestamp are always set regardless of logical_date)
    assert result_payload["builtin"]["date"] == current_date
    assert "timestamp" in result_payload["builtin"]
    # Verify timestamp is in ISO format by parsing it
    datetime.fromisoformat(result_payload["builtin"]["timestamp"])

    # To run only above test case:
    # uv run pytest tests/unit/task/test_system_variables_replacement.py::test_process_task_execution -vv -s -p no:warnings


# ----------------------------------------replace_placeholders---------------------------------------------------------------
def test_replace_placeholders_complex_nested_structure(config_manager):
    """Test complex nested structure with list, dict, and strings"""

    content = {
        "users": [
            {"name": "bankai -> {{user1_name}}", "permissions": ["{{perm1}}", "{{perm2}}"]},
            {"name": "{{user2_name}}", "permissions": ["{{perm3}}"]},
        ],
        "settings": {
            "environment": "{{env}}",
            "debug": "{{debug}}",
            "missing test": "missing parameter : {{missing}}",
        },
    }
    parameters = {
        "user1_name": "Admin",
        "perm1": "read",
        "perm2": "write",
        "user2_name": "Guest",
        "perm3": "read",
        "env": "production",
        "debug": "false",
    }

    result = config_manager.replace_placeholders(content, parameters)

    assert result == {
        "users": [
            {"name": "bankai -> Admin", "permissions": ["read", "write"]},
            {"name": "Guest", "permissions": ["read"]},
        ],
        "settings": {
            "environment": "production",
            "debug": "false",
            "missing test": "missing parameter : {{ missing }}",
        },
    }


# ----------------------------------------TEST: replace_placeholders (edge cases)--------------------------------------------


def test_replace_placeholders_missing_parameter(config_manager):
    """Test behavior when parameter is missing - KeepUndefined preserves placeholders with spaces"""

    content = "Hello {{name}}, your order-{{missing}}-is ready"
    parameters = {"name": "Alice"}

    result = config_manager.replace_placeholders(content, parameters)

    assert result == "Hello Alice, your order-{{ missing }}-is ready"


def test_replace_placeholders_special_characters(config_manager):
    """Test with special characters in values"""

    content = "Name: {{name}}, Quote: {{quote}}"
    parameters = {"name": "O'Brien", "quote": 'He said "Hello"'}
    result = config_manager.replace_placeholders(content, parameters)
    assert result == 'Name: O\'Brien, Quote: He said "Hello"'


def test_replace_placeholders_non_string_non_dict_non_list(config_manager):
    """Test with integer/boolean/None content"""

    parameters = {"key": "value"}

    assert config_manager.replace_placeholders(42, parameters) == 42
    assert config_manager.replace_placeholders(True, parameters) is True
    assert config_manager.replace_placeholders(None, parameters) is None


def test_replace_placeholders_empty_string(config_manager):
    content = ""
    parameters = {"key": "value"}

    result = config_manager.replace_placeholders(content, parameters)

    assert result == ""


# -------------------------------------------------------------------------------------------------------------------------

"""
1. Run all tests:
   pytest tests/unit/task/test_templating.py -v

2. Run tests for specific function:
   pytest tests/unit/task/test_templating.py -k "builtin_variables" -v
   pytest tests/unit/task/test_templating.py -k "replace_placeholders" -v
   pytest tests/unit/task/test_templating.py -k "process_execution" -v

3. Run with output:
   pytest tests/unit/task/test_templating.py -v -s

4. Run specific test:
   pytest tests/unit/task/test_templating.py::test_replace_placeholders_simple_string -v
"""
