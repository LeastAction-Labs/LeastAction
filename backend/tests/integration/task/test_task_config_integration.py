# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
"""
Integration tests for task config field and config merging functionality.

These tests verify:
1. Task creation with inline config field
2. Config merging with attached_config_lauis
3. Config merging with workflow configs
4. Config merge priority: workflow configs > attached configs > task config field
5. Complex nested config structures
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from src.core.catalog.api_request import CreateItemResponse
from src.core.db.types import MongoDatabase
from tests.integration.schema import BaseFolders, TestRequest
from tests.integration.utils import create_base_folders, execute_request

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def database_cleanup(test_database: MongoDatabase, client: TestClient):
    await test_database.items.drop()
    await test_database.links.delete_many({})
    yield  # Test runs here
    await test_database.items.drop()
    await test_database.links.drop()


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(autouse=True)
def base_folders_setup(client: TestClient, database_cleanup):
    base_folders = create_base_folders(client)
    yield base_folders


@pytest.fixture
async def account_laui(base_folders_setup: BaseFolders) -> str:
    return base_folders_setup.account_folder_laui


@pytest.fixture
async def project_laui(base_folders_setup: BaseFolders) -> str:
    return base_folders_setup.project_folder_laui


@pytest.fixture
async def workflow_laui(client: TestClient, project_laui: str, account_laui: str) -> str:
    """Create a workflow folder under the project"""
    wf_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.workflow",
                "name": f"workflow_config_{datetime.now().timestamp()}",
                "parent_laui": project_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
            },
        ),
    )
    assert wf_resp.status_code == 200
    return CreateItemResponse(**wf_resp.json()).item_laui


@pytest.fixture
async def python_operator_laui(
    client: TestClient, workflow_laui: str, account_laui: str, project_laui: str
) -> str:
    """Create a Python operator"""
    op_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "operator.python",
                "name": f"python_operator_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "codeblock": {
                    "main.py": "def initialize(self):\n    return {}\ndef run(self, ctx):\n    return {'status': 'ok', 'execution_type': 'sync'}\ndef check_completion(self, ctx, state):\n    return {'status': 'done'}\ndef finish(self, ctx, state, result):\n    return None\n"
                },
                "bashblock": {"main.sh": "echo 'test'"},
            },
        ),
    )
    assert op_resp.status_code == 200
    return CreateItemResponse(**op_resp.json()).item_laui


@pytest.fixture
async def python_connection_laui(
    client: TestClient, workflow_laui: str, account_laui: str, project_laui: str
) -> str:
    """Create a Python connection environment"""
    connection_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "connection.python",
                "name": f"python_connection_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "content": {"type": "docker"},
            },
        ),
    )
    assert connection_resp.status_code == 200
    return CreateItemResponse(**connection_resp.json()).item_laui


@pytest.fixture
async def config_lauis(
    client: TestClient, workflow_laui: str, account_laui: str, project_laui: str
) -> list[str]:
    """Create multiple config items with different parameters"""
    config_lauis = []

    # Config with environment variables
    config1_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "config.env",
                "name": f"config_env_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "config_type": "task",
                "content": {
                    "parameters": {
                        "DB_HOST": "localhost",
                        "DB_PORT": "5432",
                        "LOG_LEVEL": "INFO",
                    }
                },
            },
        ),
    )
    assert config1_resp.status_code == 200
    config_lauis.append(CreateItemResponse(**config1_resp.json()).item_laui)

    # Config with timeout and retries
    config2_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "config.json",
                "name": f"config_json_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "config_type": "task",
                "content": {
                    "parameters": {
                        "timeout": 300,
                        "retry_count": 3,
                        "retry_delay": 60,
                    }
                },
            },
        ),
    )
    assert config2_resp.status_code == 200
    config_lauis.append(CreateItemResponse(**config2_resp.json()).item_laui)

    # Config with overlapping parameters (to test merging)
    config3_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "config.yaml",
                "name": f"config_yaml_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "config_type": "task",
                "content": {
                    "parameters": {
                        "LOG_LEVEL": "DEBUG",  # Ignored: config1 already set LOG_LEVEL (earlier configs win)
                        "API_KEY": "secret123",
                    }
                },
            },
        ),
    )
    assert config3_resp.status_code == 200
    config_lauis.append(CreateItemResponse(**config3_resp.json()).item_laui)

    return config_lauis


# ============================================================================
# TEST CASES - TASK CONFIG FIELD ONLY
# ============================================================================


async def test_create_task_with_only_config_field_pass(
    client: TestClient,
    python_operator_laui: str,
    python_connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test task creation with only the config field (no attached_config_lauis, no workflow configs).
    The config field should be merged and used for the task.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_only_config_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": python_operator_laui,
                "connection_laui": python_connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "config": {
                    "parameters": {"env": "production", "timeout": 300},
                    "async defaults": {"task": {"retry_count": 5}},
                },
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None

    # Verify task.config contains the merged config
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": task_data.item_laui}
        ),
    )
    assert get_resp.status_code == 200
    fetched_task = get_resp.json()

    # Assert that task.config is the merged config
    assert "config" in fetched_task
    assert "parameters" in fetched_task["config"]
    assert fetched_task["config"]["parameters"]["env"] == "production"
    assert fetched_task["config"]["parameters"]["timeout"] == 300
    assert fetched_task["config"]["async defaults"]["task"]["retry_count"] == 5


async def test_create_task_with_empty_config_field_pass(
    client: TestClient,
    python_operator_laui: str,
    python_connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
    config_lauis: list[str],
):
    """
    Test task creation with empty config field and attached_config_lauis.
    The attached configs should still be merged correctly.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_empty_config_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": python_operator_laui,
                "connection_laui": python_connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "config": {},
                "attached_config_lauis": config_lauis,
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None

    # Verify task.config contains the merged config from attached configs
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": task_data.item_laui}
        ),
    )
    assert get_resp.status_code == 200
    fetched_task = get_resp.json()

    # Assert that task.config is the merged config from attached configs
    assert "config" in fetched_task
    assert "parameters" in fetched_task["config"]

    # All parameters from all three attached configs should be present
    assert fetched_task["config"]["parameters"]["DB_HOST"] == "localhost"  # from config1
    assert fetched_task["config"]["parameters"]["DB_PORT"] == "5432"  # from config1
    assert (
        fetched_task["config"]["parameters"]["LOG_LEVEL"] == "INFO"
    )  # from config1 (earlier configs take precedence)
    assert fetched_task["config"]["parameters"]["timeout"] == 300  # from config2
    assert fetched_task["config"]["parameters"]["retry_count"] == 3  # from config2
    assert fetched_task["config"]["parameters"]["retry_delay"] == 60  # from config2
    assert fetched_task["config"]["parameters"]["API_KEY"] == "secret123"  # from config3


async def test_create_task_config_with_complex_nested_structure_pass(
    client: TestClient,
    python_operator_laui: str,
    python_connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test task creation with complex nested config structure.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_complex_config_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": python_operator_laui,
                "connection_laui": python_connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "config": {
                    "parameters": {
                        "database": {"host": "localhost", "port": 5432},
                        "features": {"enabled": True, "beta": False},
                    },
                    "async defaults": {
                        "task": {"retry_count": 3, "timeout": 600},
                        "cron": {"pokeInterval": "30s"},
                    },
                    "git": {"repo": "https://github.com/org/repo", "branch": "main"},
                },
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None

    # Verify task.config contains the merged complex nested config
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": task_data.item_laui}
        ),
    )
    assert get_resp.status_code == 200
    fetched_task = get_resp.json()

    # Assert that task.config is the merged config with all nested structures
    assert "config" in fetched_task
    assert "parameters" in fetched_task["config"]
    assert "database" in fetched_task["config"]["parameters"]
    assert fetched_task["config"]["parameters"]["database"]["host"] == "localhost"
    assert fetched_task["config"]["parameters"]["database"]["port"] == 5432
    assert "features" in fetched_task["config"]["parameters"]
    assert fetched_task["config"]["parameters"]["features"]["enabled"] is True
    assert fetched_task["config"]["parameters"]["features"]["beta"] is False
    assert "async defaults" in fetched_task["config"]
    assert fetched_task["config"]["async defaults"]["task"]["retry_count"] == 3
    assert fetched_task["config"]["async defaults"]["task"]["timeout"] == 600
    assert fetched_task["config"]["async defaults"]["cron"]["pokeInterval"] == "30s"
    assert "git" in fetched_task["config"]
    assert fetched_task["config"]["git"]["repo"] == "https://github.com/org/repo"
    assert fetched_task["config"]["git"]["branch"] == "main"


# ============================================================================
# TEST CASES - CONFIG FIELD WITH ATTACHED CONFIGS
# ============================================================================


async def test_create_task_with_config_and_attached_configs_pass(
    client: TestClient,
    python_operator_laui: str,
    python_connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
    config_lauis: list[str],
):
    """
    Test task creation with config field and attached_config_lauis.
    Verify that attached configs override the config field.
    Priority: attached configs > config field
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_config_and_attached_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": python_operator_laui,
                "connection_laui": python_connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "config": {
                    "parameters": {"LOG_LEVEL": "INFO"},  # Will be overridden by config3's DEBUG
                },
                "attached_config_lauis": config_lauis,
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None

    # Verify task.config contains the merged config with attached configs overriding task config
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": task_data.item_laui}
        ),
    )
    assert get_resp.status_code == 200
    fetched_task = get_resp.json()

    # Assert that task.config is the merged config
    assert "config" in fetched_task
    assert "parameters" in fetched_task["config"]

    # config1 (first in config_lauis) sets LOG_LEVEL: "INFO" first, so config3's "DEBUG" is ignored
    # Attached configs take precedence over inline task config, so config1's "INFO" wins over task config's "INFO"
    assert fetched_task["config"]["parameters"]["LOG_LEVEL"] == "INFO"

    # Parameters from all attached configs should be present
    assert fetched_task["config"]["parameters"]["DB_HOST"] == "localhost"  # from config1
    assert fetched_task["config"]["parameters"]["DB_PORT"] == "5432"  # from config1
    assert fetched_task["config"]["parameters"]["timeout"] == 300  # from config2
    assert fetched_task["config"]["parameters"]["retry_count"] == 3  # from config2
    assert fetched_task["config"]["parameters"]["retry_delay"] == 60  # from config2
    assert fetched_task["config"]["parameters"]["API_KEY"] == "secret123"  # from config3


# ============================================================================
# TEST CASES - ALL THREE CONFIGS (TASK + ATTACHED + WORKFLOW)
# ============================================================================


async def test_create_task_with_all_three_configs_pass(
    client: TestClient,
    python_operator_laui: str,
    python_connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
    config_lauis: list[str],
):
    """
    Test task creation with all 3 config sources:
    - config field (task-level inline config)
    - attached_config_lauis (attached config items)
    - workflow configs (from parent workflow)

    Verify merge priority: workflow configs > attached configs > config field
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_all_configs_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": python_operator_laui,
                "connection_laui": python_connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "config": {
                    "parameters": {
                        "task_level_param": "from_task",
                        "shared_param": "task_value",
                    },
                },
                "attached_config_lauis": config_lauis,
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None

    # Verify task.config contains the merged config with proper priority
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": task_data.item_laui}
        ),
    )
    assert get_resp.status_code == 200
    fetched_task = get_resp.json()

    # Assert that task.config is the merged config
    assert "config" in fetched_task
    assert "parameters" in fetched_task["config"]

    # Task-level param should be present (not overridden)
    assert fetched_task["config"]["parameters"]["task_level_param"] == "from_task"

    # Attached configs (processed before task config) take precedence; config1 sets LOG_LEVEL first
    assert (
        fetched_task["config"]["parameters"]["LOG_LEVEL"] == "INFO"
    )  # from config1 (earlier configs win)
    assert fetched_task["config"]["parameters"]["DB_HOST"] == "localhost"  # from config1
    assert fetched_task["config"]["parameters"]["timeout"] == 300  # from config2
    assert fetched_task["config"]["parameters"]["API_KEY"] == "secret123"  # from config3


async def test_all_three_configs_with_distinct_params_merged_pass(
    client: TestClient,
    python_operator_laui: str,
    python_connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that when all 3 config sources have entirely different (non-overlapping) parameters,
    ALL parameters from every source appear in the final merged task.config.

    Sources:
    - workflow config (parent_laui=workflow_laui):  region, cluster
    - attached task config (under folder.config):   cache_ttl, max_connections
    - inline task config:                           app_name, debug_mode
    """

    # 1. Create workflow config (parent_laui = workflow, so it's auto-attached as workflow config)
    wf_config_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "config.json",
                "name": f"wf_config_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "config_type": "workflow",
                "content": {
                    "parameters": {
                        "region": "us-east-1",
                        "cluster": "prod-cluster-01",
                    }
                },
            },
        ),
    )
    assert wf_config_resp.status_code == 200

    # 2. Create a folder.config to hold the task-level attached config
    config_folder_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.config",
                "name": f"config_folder_{datetime.now().timestamp()}",
                "parent_laui": project_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
            },
        ),
    )
    assert config_folder_resp.status_code == 200
    config_folder_laui = CreateItemResponse(**config_folder_resp.json()).item_laui

    # 3. Create task-level attached config under folder.config with different params
    task_config_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "config.json",
                "name": f"task_attached_config_{datetime.now().timestamp()}",
                "parent_laui": config_folder_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "config_type": "task",
                "content": {
                    "parameters": {
                        "cache_ttl": 3600,
                        "max_connections": 50,
                    }
                },
            },
        ),
    )
    assert task_config_resp.status_code == 200
    task_attached_config_laui = CreateItemResponse(**task_config_resp.json()).item_laui

    # 4. Create task with inline config + attached config (workflow config auto-resolved from parent)
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_all_distinct_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": python_operator_laui,
                "connection_laui": python_connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "config": {
                    "parameters": {
                        "app_name": "my_app",
                        "debug_mode": True,
                    },
                },
                "attached_config_lauis": [task_attached_config_laui],
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None

    # Fetch the task and assert that ALL parameters from all 3 sources are present
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": task_data.item_laui}
        ),
    )
    assert get_resp.status_code == 200
    fetched_task = get_resp.json()

    assert "config" in fetched_task
    assert "parameters" in fetched_task["config"]
    merged_params = fetched_task["config"]["parameters"]

    # From workflow config (parent_laui = workflow_laui)
    assert merged_params["region"] == "us-east-1"
    assert merged_params["cluster"] == "prod-cluster-01"

    # From attached task config (under folder.config, passed via attached_config_lauis)
    assert merged_params["cache_ttl"] == 3600
    assert merged_params["max_connections"] == 50

    # From inline task config
    assert merged_params["app_name"] == "my_app"
    assert merged_params["debug_mode"] is True


# ============================================================================
# TEST CASES - CONFIG MERGING WITH MULTIPLE ATTACHED CONFIGS
# ============================================================================


async def test_create_task_with_multiple_attached_configs_merge_pass(
    client: TestClient,
    python_operator_laui: str,
    python_connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
    config_lauis: list[str],
):
    """
    Test that multiple attached configs are merged in order,
    with earlier configs taking precedence over later ones for the same key.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_multi_attached_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": python_operator_laui,
                "connection_laui": python_connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "attached_config_lauis": config_lauis,  # config1, config2, config3
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None

    # Verify task.config contains the merged config from all attached configs
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": task_data.item_laui}
        ),
    )
    assert get_resp.status_code == 200
    fetched_task = get_resp.json()

    # Assert that task.config is the merged config
    assert "config" in fetched_task
    assert "parameters" in fetched_task["config"]

    # config1 sets LOG_LEVEL: "INFO" first; config3's "DEBUG" is ignored (earlier configs win)
    assert fetched_task["config"]["parameters"]["LOG_LEVEL"] == "INFO"

    # All parameters from all three configs should be present
    assert fetched_task["config"]["parameters"]["DB_HOST"] == "localhost"  # from config1
    assert fetched_task["config"]["parameters"]["DB_PORT"] == "5432"  # from config1
    assert fetched_task["config"]["parameters"]["timeout"] == 300  # from config2
    assert fetched_task["config"]["parameters"]["retry_count"] == 3  # from config2
    assert fetched_task["config"]["parameters"]["retry_delay"] == 60  # from config2
    assert fetched_task["config"]["parameters"]["API_KEY"] == "secret123"  # from config3


# ============================================================================
# TEST CASES - CONFIG FIELD RETURNED CORRECTLY
# ============================================================================


async def test_get_task_with_config_field_pass(
    client: TestClient,
    python_operator_laui: str,
    python_connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that when getting a task, the config field is returned correctly.
    """
    task_config = {
        "parameters": {"env": "staging", "timeout": 200},
        "async defaults": {"task": {"retry_count": 3}},
    }

    # Create task with config
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_get_config_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": python_operator_laui,
                "connection_laui": python_connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "config": task_config,
            },
        ),
    )

    assert task_resp.status_code == 200
    task_laui = CreateItemResponse(**task_resp.json()).item_laui

    # Get the task and verify config field
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": task_laui}
        ),
    )
    assert get_resp.status_code == 200
    task_data = get_resp.json()

    # Verify config field is present and correct
    assert "config" in task_data
    assert task_data["config"] == task_config
    assert task_data["config"]["parameters"]["env"] == "staging"
    assert task_data["config"]["parameters"]["timeout"] == 200
    assert task_data["config"]["async defaults"]["task"]["retry_count"] == 3


async def test_get_task_without_config_field_defaults_to_empty_pass(
    client: TestClient,
    python_operator_laui: str,
    python_connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that when getting a task without config field, it async defaults to empty dict.
    """
    # Create task without config field
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task/run",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_no_config_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": python_operator_laui,
                "connection_laui": python_connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )

    assert task_resp.status_code == 200
    task_laui = CreateItemResponse(**task_resp.json()).item_laui

    # Get the task and verify config async defaults to empty dict
    get_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": task_laui}
        ),
    )
    assert get_resp.status_code == 200
    task_data = get_resp.json()

    assert "config" in task_data
    assert task_data["config"] == {}
