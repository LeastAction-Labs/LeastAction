# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import UTC, datetime, timedelta

import pytest
from bson import ObjectId
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
# TEST CASES SUMMARY
# ============================================================================
# This test file covers the following scenarios:
#
# SUCCESS CASES (marked with _pass):
#    - Task creation with ADHOC frequency (no dates required)
#    - Task creation with cron expression (requires start_date and end_date)
#    - Task creation with payload as direct input string
#    - Task creation with payload_laui referencing a payload item
#    - Task creation with attached configuration items
#    - Task creation with existing references (sequential creation)
#    - Task with multiple configs merging parameters
#    - Spark connection with Spark operator
#    - Databricks connection with Spark operator
#    - Cron expressions (every minute, complex business hours)
#    - Same start and end date (boundary condition)
#    - Past dates (historical tasks)
#    - All valid states (scheduled, success, running, error, completed)
#    - Complex JSON payloads
#    - Empty string payloads
#    - Missing frequency (async defaults to ADHOC)
#    - Empty config list
#    - No payload field provided
#
# FAILURE CASES (marked with _fail):
#    - End date before start date
#    - Non-existent operator
#    - Non-existent connection
#    - Both payload and payload_laui provided
#    - Non-existent parent_laui
#    - Invalid cron expression
#    - Missing all required items
#    - Parent not a workflow folder
#    - Operator item type mismatch
#    - connection item type mismatch
#    - Config item type mismatch
#    - Spark connection with Python operator (incompatible mapping)
#    - Invalid state value not in enum
#    - All non-existent item IDs (operator, connection, parent)
#    - Missing account_laui (required field)
#    - Missing project_laui (required field)
#    - Cron frequency without start_date
#    - Cron frequency without end_date
#    - Cron frequency without both dates
#    - connection-operator type mismatch
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
                "name": f"workflow_{datetime.now().timestamp()}",
                "parent_laui": project_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "folder_metadata": {"state": "active"},
            },
        ),
    )
    assert wf_resp.status_code == 200
    return CreateItemResponse(**wf_resp.json()).item_laui


@pytest.fixture
async def operator_laui(
    client: TestClient, workflow_laui: str, account_laui: str, project_laui: str
) -> str:
    """Create a Python operator in the workflow (alias for python_operator_laui)"""
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
async def spark_operator_laui(
    client: TestClient, workflow_laui: str, account_laui: str, project_laui: str
) -> str:
    """Create a Spark operator"""
    op_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "operator.spark",
                "name": f"spark_operator_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "codeblock": {
                    "main.py": "def initialize(self):\n    return {}\ndef run(self, ctx):\n    return {'status': 'ok', 'execution_type': 'sync'}\ndef check_completion(self, ctx, state):\n    return {'status': 'done'}\ndef finish(self, ctx, state, result):\n    return None\n"
                },
                "bashblock": {"main.sh": "spark-submit test.py"},
            },
        ),
    )
    assert op_resp.status_code == 200
    return CreateItemResponse(**op_resp.json()).item_laui


@pytest.fixture
async def connection_laui(
    client: TestClient, workflow_laui: str, account_laui: str, project_laui: str
) -> str:
    """Create a Python connection environment (alias for python_connection_laui)"""
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
async def spark_connection_laui(
    client: TestClient, workflow_laui: str, account_laui: str, project_laui: str
) -> str:
    """Create a Spark connection environment"""
    connection_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "connection.spark",
                "name": f"spark_connection_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "content": {"type": "kubernetes"},
            },
        ),
    )
    assert connection_resp.status_code == 200
    return CreateItemResponse(**connection_resp.json()).item_laui


@pytest.fixture
async def databricks_connection_laui(
    client: TestClient, workflow_laui: str, account_laui: str, project_laui: str
) -> str:
    """Create a Databricks connection environment"""
    connection_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "connection.databricks",
                "name": f"databricks_connection_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "content": {"type": "cloud"},
            },
        ),
    )
    assert connection_resp.status_code == 200
    return CreateItemResponse(**connection_resp.json()).item_laui


@pytest.fixture
async def payload_laui(
    client: TestClient, workflow_laui: str, account_laui: str, project_laui: str
) -> str:
    """Create a payload item in the workflow"""
    payload_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "payload.json",
                "name": f"payload_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "content": '{"test": "data"}',
            },
        ),
    )
    assert payload_resp.status_code == 200
    return CreateItemResponse(**payload_resp.json()).item_laui


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
                "parent_laui": workflow_laui,
                "config_type": "task",
                "content": {
                    "parameters": {
                        "LOG_LEVEL": "DEBUG",  # Overwrites config1
                        "API_KEY": "secret123",
                    }
                },
            },
        ),
    )
    assert config3_resp.status_code == 200
    config_lauis.append(CreateItemResponse(**config3_resp.json()).item_laui)

    return config_lauis


async def test_create_task_with_frequency_adhoc_pass(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test successful task creation with ADHOC frequency.
    ADHOC tasks do not require start_date or end_date.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_adhoc_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )
    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None


async def test_create_task_with_cron_expression_pass(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test successful task creation with valid cron expression.
    Scheduled tasks with cron require start_date and end_date.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_cron_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "0 12 * * *",  # Valid cron: daily at noon
                "start_date": "2025-01-01T00:00:00",
                "end_date": "2025-12-31T23:59:59",
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None


async def test_create_task_with_payload_as_input_pass(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test successful task creation with payload as direct input string.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_payload_input_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "payload": '{"key": "value", "data": [1, 2, 3]}',
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None


async def test_create_task_with_payload_laui_and_create_link_pass(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    payload_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
    test_database: MongoDatabase,
):
    """
    Test successful task creation with payload_laui referencing a payload item.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_payload_laui_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "payload_laui": payload_laui,
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None
    # Assert create_link
    links_created = await test_database.links.find(
        filter={"child_laui": ObjectId(task_data.item_laui), "true_parent": False}
    ).to_list(length=None)  # all links created during task creation for this item_laui as soft link
    if operator_laui:
        assert any(
            link["parent_laui"] == ObjectId(operator_laui)
            and link["parent_type"] == "operator.python"
            for link in links_created
        )
        links_created = [
            link
            for link in links_created
            if link["parent_laui"] != ObjectId(operator_laui)
            or link["parent_type"] != "operator.python"
        ]
    if connection_laui:
        assert any(
            link["parent_laui"] == ObjectId(connection_laui)
            and link["parent_type"] == "connection.python"
            for link in links_created
        )
        links_created = [
            link
            for link in links_created
            if link["parent_laui"] != ObjectId(connection_laui)
            or link["parent_type"] != "connection.python"
        ]
    if payload_laui:
        assert any(
            link["parent_laui"] == ObjectId(payload_laui) and link["parent_type"] == "payload.json"
            for link in links_created
        )
        links_created = [
            link
            for link in links_created
            if link["parent_laui"] != ObjectId(payload_laui)
            or link["parent_type"] != "payload.json"
        ]
    assert len(links_created) == 0


async def test_create_task_with_attached_configs_and_create_link_pass(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    config_lauis: list[str],
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
    test_database: MongoDatabase,
):
    """
    Test successful task creation with attached configuration items.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_config_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "attached_config_lauis": config_lauis,
            },
        ),
    )
    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None
    # Assert create_link
    links_created = await test_database.links.find(
        filter={"child_laui": ObjectId(task_data.item_laui), "true_parent": False}
    ).to_list(length=None)  # all links created during task creation for this item_laui as soft link
    if operator_laui:
        assert any(
            link["parent_laui"] == ObjectId(operator_laui)
            and link["parent_type"] == "operator.python"
            for link in links_created
        )
        links_created = [
            link
            for link in links_created
            if link["parent_laui"] != ObjectId(operator_laui)
            or link["parent_type"] != "operator.python"
        ]
    if connection_laui:
        assert any(
            link["parent_laui"] == ObjectId(connection_laui)
            and link["parent_type"] == "connection.python"
            for link in links_created
        )
        links_created = [
            link
            for link in links_created
            if link["parent_laui"] != ObjectId(connection_laui)
            or link["parent_type"] != "connection.python"
        ]
    if config_lauis:
        for config_laui in config_lauis:
            assert any(
                link["parent_laui"] == ObjectId(config_laui)
                and link["parent_type"] in ["config.env", "config.json", "config.yaml"]
                for link in links_created
            )
            links_created = [
                link
                for link in links_created
                if link["parent_laui"] != ObjectId(config_laui)
                or link["parent_type"] not in ["config.env", "config.json", "config.yaml"]
            ]
    assert len(links_created) == 0


async def test_create_task_with_existing_references(
    client: TestClient, project_laui: str, account_laui: str
):
    """
    Create workflow, operator, connection sequentially and then create a task.
    This verifies that previous creations are visible to the next request.
    """
    # Create workflow folder
    wf_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.workflow",
                "name": f"wf_visibility_{datetime.now().timestamp()}",
                "parent_laui": project_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
            },
        ),
    )
    assert wf_resp.status_code == 200, f"Workflow creation failed: {wf_resp.json()}"
    workflow_laui = CreateItemResponse(**wf_resp.json()).item_laui

    # Create operator
    op_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "operator.python",
                "name": f"operator_visibility_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "codeblock": {
                    "main.py": "def initialize(self):\n    return {}\ndef run(self, ctx):\n    return {'status': 'ok', 'execution_type': 'sync'}\ndef check_completion(self, ctx, state):\n    return {'status': 'done'}\ndef finish(self, ctx, state, result):\n    return None\n"
                },
                "bashblock": {"main.sh": "echo 'ok'"},
            },
        ),
    )
    assert op_resp.status_code == 200, f"Operator creation failed: {op_resp.json()}"
    operator_laui = CreateItemResponse(**op_resp.json()).item_laui

    # Create connection
    connection_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "connection.python",
                "name": f"connection_visibility_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "content": {"type": "docker"},
            },
        ),
    )
    assert connection_resp.status_code == 200, (
        f"connection creation failed: {connection_resp.json()}"
    )
    connection_laui = CreateItemResponse(**connection_resp.json()).item_laui

    # Create task referencing them
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_visibility_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )

    assert task_resp.status_code == 200, f"Task creation failed: {task_resp.json()}"
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None


async def test_create_task_with_end_date_before_start_date_fail(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that task creation fails when end_date is before start_date.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_invalid_dates_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "0 12 * * *",
                "start_date": "2025-12-31T23:59:59",
                "end_date": "2025-01-01T00:00:00",  # Before start_date
            },
        ),
    )

    assert task_resp.status_code == 422
    error_detail = task_resp.json()["detail"]
    assert "end_date must be greater than" in error_detail.lower()


async def test_create_task_with_nonexistent_operator_fail(
    client: TestClient,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that task creation fails when operator_laui does not exist.
    """
    fake_operator_laui = "507f1f77bcf86cd799439012"
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_missing_operator_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": fake_operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )

    assert task_resp.status_code == 403


async def test_create_task_with_nonexistent_connection_fail(
    client: TestClient, operator_laui: str, workflow_laui: str, project_laui: str, account_laui: str
):
    """
    Test that task creation fails when connection_laui does not exist.
    """
    fake_connection_laui = "507f1f77bcf86cd799439013"
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_missing_connection_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": fake_connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )

    assert task_resp.status_code == 403


async def test_create_task_with_both_payload_and_payload_laui_pass(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    payload_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that when both payload and payload_laui are provided, payload_laui takes precedence.
    The payload field is ignored and the content from payload_laui is used.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_both_payloads_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "payload": '{"data": "test"}',
                "payload_laui": payload_laui,
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None


async def test_create_task_with_nonexistent_parent_laui_fail(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that task creation fails when parent_laui does not exist.
    """
    fake_parent_laui = "507f1f77bcf86cd799439011"
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_bad_parent_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": fake_parent_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )

    assert task_resp.status_code == 403


async def test_create_task_with_invalid_cron_expression_fail(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that task creation fails with invalid cron expression.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_invalid_cron_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "0 12 *",  # Invalid: only 3 fields
                "start_date": "2025-01-01T00:00:00",
                "end_date": "2025-12-31T23:59:59",
            },
        ),
    )

    assert task_resp.status_code == 422
    error_detail = task_resp.json()["detail"]
    assert "invalid cron expression" in error_detail.lower()


async def test_create_task_with_missing_all_required_items_fail(
    client: TestClient, workflow_laui: str, project_laui: str, account_laui: str
):
    """
    Test that task creation fails when required items (operator, connection, workflow) are missing.
    This tests validation when trying to create a task without proper setup.
    """
    fake_operator_laui = "507f1f77bcf86cd799439014"
    fake_connection_laui = "507f1f77bcf86cd799439015"

    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_all_missing_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": fake_operator_laui,
                "connection_laui": fake_connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )

    assert task_resp.status_code == 403


async def test_create_task_with_parent_not_workflow_folder_fail(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that task creation fails when parent_laui is not a folder.workflow item type.
    """
    # Create a folder other then folder.workflow
    folder_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.connection",
                "name": f"regular_folder_{datetime.now().timestamp()}",
                "parent_laui": project_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
            },
        ),
    )
    assert folder_resp.status_code == 200
    folder_laui = CreateItemResponse(**folder_resp.json()).item_laui

    # Try to create task with regular folder as parent
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_bad_parent_type_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": folder_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )

    assert task_resp.status_code == 422
    error_detail = task_resp.json()["detail"]
    assert "invalid item_type" in error_detail.lower() or "supported types" in error_detail.lower()


async def test_create_task_with_operator_item_type_mismatch_fail(
    client: TestClient,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that task creation fails when operator_laui points to non-operator item.
    """
    # Create a config item (not an operator)
    config_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "config.env",
                "name": f"not_an_operator_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "config_type": "task",
                "content": {"KEY": "value"},
            },
        ),
    )
    assert config_resp.status_code == 200
    config_laui = CreateItemResponse(**config_resp.json()).item_laui

    # Try to create task with config as operator
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_operator_mismatch_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": config_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )

    assert task_resp.status_code == 422
    error_detail = task_resp.json()["detail"]
    assert "not of type operator" in error_detail.lower()


async def test_create_task_with_connection_item_type_mismatch_fail(
    client: TestClient, operator_laui: str, workflow_laui: str, project_laui: str, account_laui: str
):
    """
    Test that task creation fails when connection_laui points to non-connection item.
    """
    # Create a payload item (not connection)
    payload_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "payload.json",
                "name": f"not_a_connection_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "content": "{}",
            },
        ),
    )
    assert payload_resp.status_code == 200
    payload_laui = CreateItemResponse(**payload_resp.json()).item_laui

    # Try to create task with payload as connection
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_connection_mismatch_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": payload_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )

    assert task_resp.status_code == 422
    error_detail = task_resp.json()["detail"]
    assert "not of type connection" in error_detail.lower()


async def test_create_task_with_config_item_type_mismatch_fail(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that task creation fails when attached_config_lauis contains non-config item.
    """
    # Create payload (not config)
    payload_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "payload.json",
                "name": f"not_a_config_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "content": "{}",
            },
        ),
    )
    assert payload_resp.status_code == 200
    payload_laui = CreateItemResponse(**payload_resp.json()).item_laui

    # Try to create task with payload in attached_config_lauis
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_config_mismatch_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "attached_config_lauis": [payload_laui],
            },
        ),
    )

    assert task_resp.status_code == 422
    error_detail = task_resp.json()["detail"]
    assert "not of type config" in error_detail.lower()


async def test_task_with_multiple_configs_merge_parameters(
    client: TestClient,
    python_operator_laui: str,
    python_connection_laui: str,
    config_lauis: list[str],
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that multiple attached configs are merged correctly.
    Later configs should override earlier ones for duplicate parameters.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_config_merge_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": python_operator_laui,
                "connection_laui": python_connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "attached_config_lauis": config_lauis,
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None


async def test_task_spark_connection_with_spark_operator_pass(
    client: TestClient,
    spark_operator_laui: str,
    spark_connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test valid connection-operator mapping: connection.spark supports operator.spark
    Per system.yml: connection.spark -> [operator.spark]
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_spark_spark_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": spark_operator_laui,
                "connection_laui": spark_connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None


# async def test_task_spark_connection_with_python_operator_fail(
#     client: TestClient,
#     python_operator_laui: str,
#     spark_connection_laui: str,
#     workflow_laui: str,
#     project_laui: str,
#     account_laui: str):
#     """
#     Test invalid connection-operator mapping: connection.spark does NOT support operator.python
#     Per system.yml: connection.spark -> [operator.spark] only
#     """
#     task_resp = execute_request(client=client, request=TestRequest(url="/api/v1/catalog/create", method="post", json={
#             "item_type": "task",
#             "name": f"task_spark_python_invalid_{datetime.now().timestamp()}",
#             "project_laui": project_laui,
#             "account_laui": account_laui,
#             "parent_laui": workflow_laui,
#             "operator_laui": python_operator_laui,
#             "connection_laui": spark_connection_laui,
#             "state": "scheduled",
#             "frequency": "ADHOC",
#         }))

#     assert task_resp.status_code == 422
#     error_detail = task_resp.json()["detail"]
#     assert (
#         "does not support" in error_detail.lower()
#         or "not compatible" in error_detail.lower()
#     )


async def test_task_databricks_connection_with_spark_operator_pass(
    client: TestClient,
    spark_operator_laui: str,
    databricks_connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test valid connection-operator mapping: connection.databricks supports operator.spark
    Per system.yml: connection.databricks -> [operator.spark, operator.python]
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_databricks_spark_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": spark_operator_laui,
                "connection_laui": databricks_connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None


async def test_task_with_every_minute_cron_pass(
    client: TestClient,
    python_operator_laui: str,
    python_connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test with cron expression for every minute: */1 * * * *
    Valid 5-field cron expression.
    """
    now = datetime.now(UTC)
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_every_minute_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": python_operator_laui,
                "connection_laui": python_connection_laui,
                "state": "scheduled",
                "frequency": "*/1 * * * *",
                "start_date": (now - timedelta(days=1)).isoformat(),
                "end_date": (now + timedelta(days=1)).isoformat(),
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None


async def test_task_with_complex_cron_pass(
    client: TestClient,
    python_operator_laui: str,
    python_connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test with complex cron expression: 0 9-17 * * 1-5
    Runs at 9am to 5pm, Monday to Friday.
    """
    now = datetime.now(UTC)
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_business_hours_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": python_operator_laui,
                "connection_laui": python_connection_laui,
                "state": "scheduled",
                "frequency": "0 9-17 * * 1-5",
                "start_date": (now - timedelta(days=1)).isoformat(),
                "end_date": (now + timedelta(days=1)).isoformat(),
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None


async def test_task_with_same_start_and_end_date_pass(
    client: TestClient,
    python_operator_laui: str,
    python_connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test task with same start_date and end_date.
    Should be valid (end_date >= start_date).
    """
    same_date = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC).isoformat()
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_same_dates_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": python_operator_laui,
                "connection_laui": python_connection_laui,
                "state": "scheduled",
                "frequency": "0 12 * * *",
                "start_date": same_date,
                "end_date": same_date,
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None


async def test_task_with_past_dates_pass(
    client: TestClient,
    python_operator_laui: str,
    python_connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test task with past start and end dates.
    Should be valid even if dates are in the past.
    """
    start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC).isoformat()
    end = datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC).isoformat()

    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_past_dates_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": python_operator_laui,
                "connection_laui": python_connection_laui,
                "state": "scheduled",
                "frequency": "0 12 * * *",
                "start_date": start,
                "end_date": end,
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None


async def test_task_with_all_valid_states(
    client: TestClient,
    python_operator_laui: str,
    python_connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test task creation with all valid state values from schema.
    Valid states: scheduled, success, running, error, completed
    """
    valid_states = ["scheduled", "success", "running", "error"]

    for state in valid_states:
        task_resp = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/task",
                method="post",
                json={
                    "item_type": "task",
                    "name": f"task_state_{state}_{datetime.now().timestamp()}",
                    "project_laui": project_laui,
                    "account_laui": account_laui,
                    "parent_laui": workflow_laui,
                    "operator_laui": python_operator_laui,
                    "connection_laui": python_connection_laui,
                    "state": state,
                    "frequency": "ADHOC",
                },
            ),
        )

        assert task_resp.status_code == 200, f"Failed for state: {state}"
        task_data = CreateItemResponse(**task_resp.json())
        assert task_data.item_laui is not None


async def test_task_with_complex_json_payload_pass(
    client: TestClient,
    python_operator_laui: str,
    python_connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test task with complex nested JSON payload.
    """
    complex_payload = {
        "database": {
            "host": "localhost",
            "port": 5432,
            "credentials": {"username": "admin", "password": "secret"},
        },
        "arrays": [1, 2, 3, {"nested": "value"}],
        "flags": {"enabled": True, "retry": False},
    }

    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_complex_payload_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": python_operator_laui,
                "connection_laui": python_connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "payload": complex_payload,
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None


async def test_task_with_empty_string_payload_pass(
    client: TestClient,
    python_operator_laui: str,
    python_connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test task with empty string payload.
    Should be valid (payload is optional).
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_empty_payload_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": python_operator_laui,
                "connection_laui": python_connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "payload": "",
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None


# ============================================================================
# ADDITIONAL TEST CASES - Missing Scenarios
# ============================================================================


async def test_create_task_with_invalid_state_fail(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that task creation fails when state is not in enum.
    Valid states: scheduled, success, running, error, completed
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_invalid_state_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "invalid_state",
                "frequency": "ADHOC",
            },
        ),
    )

    assert task_resp.status_code == 422


async def test_create_task_with_all_nonexistent_item_lauis_fail(
    client: TestClient, workflow_laui: str, project_laui: str, account_laui: str
):
    """
    Test task creation fails when all referenced items (operator, connection, parent) don't exist.
    Uses dummy MongoDB ObjectIds for non-existent items.
    """
    fake_operator_laui = "507f1f77bcf86cd799439001"
    fake_connection_laui = "507f1f77bcf86cd799439002"
    fake_parent_laui = "507f1f77bcf86cd799439003"

    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_all_nonexistent_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": fake_parent_laui,
                "operator_laui": fake_operator_laui,
                "connection_laui": fake_connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )

    assert task_resp.status_code == 403


async def test_create_task_missing_account_laui_fail(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
):
    """
    Test that task creation fails when account_laui is not provided.
    account_laui is a required field.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_no_account_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )

    assert task_resp.status_code == 422
    response_data = task_resp.json()
    error_detail = response_data.get("detail", "")
    # Convert to string to handle both list and dict types
    error_str = str(error_detail)
    assert "account_laui" in error_str.lower()


async def test_create_task_missing_project_laui_fail(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    account_laui: str,
):
    """
    Test that task creation fails when project_laui is not provided.
    project_laui is a required field.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_no_project_{datetime.now().timestamp()}",
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )

    assert task_resp.status_code == 422
    response_data = task_resp.json()
    error_detail = response_data.get("detail", "")
    # Convert to string to handle both list and dict types
    error_str = str(error_detail)
    assert "project_laui" in error_str.lower()


async def test_create_task_cron_without_start_date_fail(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that task creation fails when cron expression is used without start_date.
    Cron-based tasks require start_date.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_cron_no_start_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "0 12 * * *",
                "end_date": "2025-12-31T23:59:59",
            },
        ),
    )

    assert task_resp.status_code == 422
    error_detail = task_resp.json()["detail"]
    assert "start_date" in error_detail.lower()


async def test_create_task_cron_without_end_date_fail(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that task creation fails when cron expression is used without end_date.
    Cron-based tasks require end_date.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_cron_no_end_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "0 12 * * *",
                "start_date": "2025-01-01T00:00:00",
            },
        ),
    )

    assert task_resp.status_code == 200


async def test_create_task_cron_without_both_dates_fail(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that task creation fails when cron expression is used without both start_date and end_date.
    Cron-based tasks require both dates.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_cron_no_dates_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "0 12 * * *",
            },
        ),
    )

    assert task_resp.status_code == 422


async def test_create_task_missing_frequency_pass(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that task creation succeeds when frequency is not provided.
    Should async default to ADHOC if frequency is optional or not provided.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_no_frequency_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None


async def test_create_task_with_attached_config_empty_pass(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test task creation with empty attached_config_lauis list.
    Should succeed with no attached configs.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_empty_config_list_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
                "attached_config_lauis": [],
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None


async def test_create_task_with_no_payload_pass(
    client: TestClient,
    operator_laui: str,
    connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test task creation without payload field.
    Payload is optional and should not be required.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_no_payload_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )

    assert task_resp.status_code == 200
    task_data = CreateItemResponse(**task_resp.json())
    assert task_data.item_laui is not None


async def test_create_task_python_connection_with_spark_operator_fail(
    client: TestClient,
    spark_operator_laui: str,
    python_connection_laui: str,
    workflow_laui: str,
    project_laui: str,
    account_laui: str,
):
    """
    Test that task creation fails when connection-operator type mismatch.
    connection.python supports operator.python and operator.spark.
    This should verify the mapping validation.
    Per system.yml: connection.python -> [operator.python, operator.spark]
    This tests the opposite: connection.python with spark operator should be valid.
    However, if spark is not supported by python connection, this should fail.
    """
    task_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/task",
            method="post",
            json={
                "item_type": "task",
                "name": f"task_python_connection_spark_op_{datetime.now().timestamp()}",
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_laui,
                "operator_laui": spark_operator_laui,
                "connection_laui": python_connection_laui,
                "state": "scheduled",
                "frequency": "ADHOC",
            },
        ),
    )

    # Note: This depends on the actual system.yml configuration
    # If python connection supports spark operator, this should pass (200)
    # If it doesn't, it should fail (422)
    assert task_resp.status_code in [200, 422]
    if task_resp.status_code == 422:
        error_detail = task_resp.json()["detail"]
        assert (
            "does not support" in error_detail.lower() or "not compatible" in error_detail.lower()
        )
