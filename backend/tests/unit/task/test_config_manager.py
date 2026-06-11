# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
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
    initialize_logger(real_config)
    yield
    manager = get_logger_manager()
    manager.clear_loggers()


def test_config_merge():
    workflow_configs = [
        {
            "laui": str(ObjectId()),
            "name": "workflow_config_1",
            "content": {
                "key_1": "workflow_value_1",
                "key_2": "workflow_value_2",
                "parameters": {"DB_HOST": "localhost", "DB_PORT": "5432", "LOG_LEVEL": "INFO"},
                "overridable": ["LOG_LEVEL"],
                "nested_dir_1": {
                    "key_1": {"abc": "xyz", "def": "pqr"},
                    "key_2": "workflow_value_1",
                },
            },
        },
        {
            "name": "workflow_config_2",
            "laui": str(ObjectId()),
            "content": {
                "key_1": "workflow_value_3",  # ignored
                "key_2": "workflow_value_4",  # ignored
                "key_3": "workflow_value_5",
                "parameters": {
                    "timeout": 300,
                    "retry_count": 3,
                    "retry_delay": 60,
                },
                "overridable": ["DB_PORT"],  # ignored
                "not_overridable": ["DB_HOST"],
                "nested_dir_1": {
                    "key_2": {},  # ignored
                    "key_1": {
                        "abc": "abc",  # ignored
                        "ghi": "stu",
                    },
                },
            },
        },
    ]

    workflow_config_1_laui = workflow_configs[0]["laui"]
    workflow_config_2_laui = workflow_configs[1]["laui"]

    task_configs = [
        {
            "name": "task_config_1",
            "laui": str(ObjectId()),
            "content": {
                "key_1": "task_value_1",
                "key_4": "task_value_4",
                "parameters": {
                    "DB_HOST": "localhost2",  # ignored
                    "DB_PORT": "5433",
                    "LOG_LEVEL": "WARNING",
                },
                "nested_dir_1": {"key_1": {"jkl": "pqr"}},
            },
        },
        {
            "name": "task_config_2",
            "laui": str(ObjectId()),
            "content": {
                "parameters": {
                    "timeout": 600,
                },
                "nested_dir_1": {
                    "key_1": {
                        "abc": "abc",
                        "jkl": "jkl",  # ignored
                    }
                },
            },
        },
    ]

    task_config_1_laui = task_configs[0]["laui"]
    task_config_2_laui = task_configs[1]["laui"]

    task_config = {
        "name": "task_config",
        "content": {
            "parameters": {
                "DB_HOST": "localhost3",  # ignored
                "retry_count": 5,
            }
        },
    }

    task_config_laui = "attached_task_config"

    config_manager = ConfigManager()
    merged_result = config_manager.merge_configs(
        task_config=task_config,
        configs_data={"workflow_configs": workflow_configs, "task_configs": task_configs},
    )

    merged_config = merged_result["merged_config"]
    print(merged_config)

    assert merged_config == {
        "key_1": "task_value_1",
        "key_2": "workflow_value_2",
        "key_3": "workflow_value_5",
        "key_4": "task_value_4",
        "parameters": {
            "DB_HOST": "localhost",
            "DB_PORT": "5433",
            "LOG_LEVEL": "WARNING",
            "timeout": 600,
            "retry_count": 5,
            "retry_delay": 60,
        },
        "overridable": ["LOG_LEVEL"],
        "not_overridable": ["DB_HOST"],
        "nested_dir_1": {
            "key_1": {"abc": "abc", "def": "pqr", "jkl": "pqr", "ghi": "stu"},
            "key_2": "workflow_value_1",
        },
    }

    merged_value_sources = merged_result["merged_value_sources"]

    print(merged_value_sources)

    assert merged_value_sources == {
        "key_1": task_config_1_laui,
        "key_2": workflow_config_1_laui,
        "key_3": workflow_config_2_laui,
        "key_4": task_config_1_laui,
        "parameters": {
            "DB_HOST": workflow_config_1_laui,
            "DB_PORT": task_config_1_laui,
            "LOG_LEVEL": task_config_1_laui,
            "timeout": task_config_2_laui,
            "retry_count": task_config_laui,
            "retry_delay": workflow_config_2_laui,
        },
        "overridable": workflow_config_1_laui,
        "not_overridable": workflow_config_2_laui,
        "nested_dir_1": {
            "key_1": {
                "abc": task_config_2_laui,
                "def": workflow_config_1_laui,
                "jkl": task_config_1_laui,
                "ghi": workflow_config_2_laui,
            },
            "key_2": workflow_config_1_laui,
        },
    }


def test_replace_placeholders_with_task_system_params():
    """
    Verifies that task system fields (name, project_laui, account_laui, operator_laui, etc.)
    are available for placeholder replacement even when not present in config parameters.
    Also verifies that excluded fields (description, actions, payload, config) are NOT available.
    """
    config_manager = ConfigManager()

    task_laui = str(ObjectId())
    project_laui = str(ObjectId())
    account_laui = str(ObjectId())
    operator_laui = str(ObjectId())
    connection_laui = str(ObjectId())

    task = TaskValidationModel(
        name="my_test_task",
        laui=task_laui,
        parent_laui=str(ObjectId()),
        project_laui=project_laui,
        account_laui=account_laui,
        operator_laui=operator_laui,
        connection_laui=connection_laui,
        description="this should be excluded",
        partition="PROD",
        frequency="0 * * * *",
        actions={
            "pre_actions": [],
            "post_actions": [],
            "create_actions": [],
            "running_actions": [],
        },
        payload={"some_key": "some_value"},
        config={"parameters": {"DB_HOST": "localhost"}},
    )

    # parameters only has DB_HOST — task system fields are NOT in parameters
    parameters = {"DB_HOST": "localhost"}

    payload_content = {
        "url": "https://api.example.com/{{ project_laui }}/tasks",
        "task_name": "{{ name }}",
        "account": "{{ account_laui }}",
        "operator": "{{ operator_laui }}",
        "connection": "{{ connection_laui }}",
        "partition": "{{ partition }}",
        "frequency": "{{ frequency }}",
        "host": "{{ DB_HOST }}",
        "nested": {"task_ref": "task:{{ laui }}", "items": ["{{ name }}", "{{ project_laui }}"]},
        # excluded fields should NOT be replaced
        "desc": "{{ description }}",
        "acts": "{{ actions }}",
        "pay": "{{ payload }}",
        "cfg": "{{ config }}",
    }

    result = config_manager.replace_placeholders(payload_content, parameters, task=task)

    # task system fields should be replaced
    assert result["url"] == f"https://api.example.com/{project_laui}/tasks"
    assert result["task_name"] == "my_test_task"
    assert result["account"] == account_laui
    assert result["operator"] == operator_laui
    assert result["connection"] == connection_laui
    assert result["partition"] == "PROD"
    assert result["frequency"] == "0 * * * *"
    assert result["host"] == "localhost"

    # nested dict and list replacement
    assert result["nested"]["task_ref"] == f"task:{task_laui}"
    assert result["nested"]["items"] == ["my_test_task", project_laui]

    # excluded fields should remain as unreplaced placeholders
    assert "{{ description }}" in result["desc"]
    assert "{{ actions }}" in result["acts"]
    assert "{{ payload }}" in result["pay"]
    assert "{{ config }}" in result["cfg"]


def test_replace_placeholders_config_params_take_precedence_over_task_system_params():
    """
    Verifies that explicit config parameters take precedence over task system params.
    e.g. if parameters has name="override_name", it should win over task.name.
    """
    config_manager = ConfigManager()

    task = TaskValidationModel(
        name="original_name",
        laui=str(ObjectId()),
        parent_laui=str(ObjectId()),
        project_laui=str(ObjectId()),
        account_laui=str(ObjectId()),
        operator_laui=str(ObjectId()),
        connection_laui=str(ObjectId()),
    )

    # parameters explicitly overrides "name"
    parameters = {"name": "override_name"}

    result = config_manager.replace_placeholders("{{ name }}", parameters, task=task)
    assert result == "override_name"
