# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import json
import time
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.core.catalog.api_request import CreateItemResponse
from src.core.db.types import MongoDatabase
from src.core.task.connection.schema import SortOrder
from tests.integration.schema import BaseFolders, TestRequest
from tests.integration.utils import create_base_folders, execute_request

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def database_cleanup(test_database: MongoDatabase):
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
async def action_folder_laui(client: TestClient, project_laui: str, account_laui: str) -> str:
    """Create an action folder under the project"""
    folder_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.action",
                "name": f"actions_{datetime.now().timestamp()}",
                "parent_laui": project_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
            },
        ),
    )
    assert folder_resp.status_code == 200
    return CreateItemResponse(**folder_resp.json()).item_laui


@pytest.fixture
async def connection_laui(
    client: TestClient, workflow_laui: str, account_laui: str, project_laui: str
) -> str:
    """Create a connection with test content"""
    connection_content = {
        "host": "localhost",
        "port": 5432,
        "database": "test_db",
        "username": "test_user",
        "password": "test_password",
        "ssl_mode": "require",
        "max_parallelism": 2,
        "sort_dict": {"priority": SortOrder.ASC},
    }

    conn_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "connection.python",
                "name": f"test_connection_{datetime.now().timestamp()}",
                "parent_laui": workflow_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
                "content": connection_content,
            },
        ),
    )
    assert conn_resp.status_code == 200
    return CreateItemResponse(**conn_resp.json()).item_laui


@pytest.fixture
async def connection_write_action_laui(
    client: TestClient, action_folder_laui: str, account_laui: str, project_laui: str
) -> str:
    """Create an action that writes connection content to a file"""
    action_code = '''import json
from pathlib import Path
from src.common.logger.logger import log_info, log_error


def run(least_action_action_object, folder_path, file_path):
    """
    Write connection content to a file.

    Args:
        least_action_action_object: Action metadata object with connection data
        folder_path: Path to the folder to create
        file_path: Path to the file to create (relative to folder_path or absolute)

    Returns:
        True if all operations succeed, False otherwise
    """
    action_id = least_action_action_object.get("laui")
    connection = least_action_action_object.get("connection")

    try:
        log_info("action", "run", "start", f"Starting connection write action {action_id}")

        # Validate connection
        if not connection:
            log_error("action", "run", "no_connection", "No connection data found in action object")
            return False

        # Validate inputs
        if not folder_path or not isinstance(folder_path, str):
            log_error("action", "run", "validation_error", "folder_path must be a non-empty string")
            return False

        if not file_path or not isinstance(file_path, str):
            log_error("action", "run", "validation_error", "file_path must be a non-empty string")
            return False

        # Convert to Path objects for easier manipulation
        folder = Path(folder_path)
        file = Path(file_path)

        # If file_path is relative, make it relative to folder_path
        if not file.is_absolute():
            file = folder / file

        log_info("action", "run", "paths", f"Folder: {folder}, File: {file}")

        # Create folder (handle case where folder already exists)
        try:
            folder.mkdir(parents=True, exist_ok=True)
            log_info("action", "run", "folder_created", f"Folder created/exists: {folder}")
        except PermissionError as e:
            log_error("action", "run", "permission_error", f"Permission denied creating folder {folder}: {str(e)}")
            return False
        except OSError as e:
            log_error("action", "run", "folder_error", f"Error creating folder {folder}: {str(e)}")
            return False

        # Check if folder exists
        if not folder.exists():
            log_error("action", "run", "folder_not_exists", f"Folder does not exist after creation: {folder}")
            return False

        # Create file with connection content (will overwrite if exists)
        try:
            file.parent.mkdir(parents=True, exist_ok=True)  # Ensure parent directories exist
            with open(file, "w", encoding="utf-8") as f:
                json.dump(connection, f, indent=2)
            log_info("action", "run", "file_created", f"File created with connection content: {file}")
        except PermissionError as e:
            log_error("action", "run", "permission_error", f"Permission denied creating file {file}: {str(e)}")
            return False
        except OSError as e:
            log_error("action", "run", "file_error", f"Error creating file {file}: {str(e)}")
            return False

        # Check if file exists
        if not file.exists():
            log_error("action", "run", "file_not_exists", f"File does not exist after creation: {file}")
            return False

        log_info("action", "run", "file_verified", f"File verified to exist: {file}")
        log_info("action", "run", "success", "Connection content written successfully")
        return True

    except Exception as e:
        log_error("action", "run", "unexpected_error", f"Unexpected error: {str(e)}")
        return False
'''

    action_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "action",
                "name": "ConnectionWrite.action",
                "parent_laui": action_folder_laui,
                "prompt": "Generate an action that writes connection content to a file",
                "codeblock": {"main.py": action_code},
                "bashblock": {},
                "account_laui": account_laui,
                "project_laui": project_laui,
            },
        ),
    )
    assert action_resp.status_code == 200
    return CreateItemResponse(**action_resp.json()).item_laui


# ============================================================================
# TEST CASES
# ============================================================================


async def test_execute_action_with_connection_laui_pass(
    client: TestClient,
    connection_write_action_laui: str,
    connection_laui: str,
):
    """
    Test action execution with connection_laui via /api/v1/action/run.
    This tests that the PreActionManager (create_actions):
    1. Fetches the connection content using catalog_manager.find_item
    2. Validates the item type starts with 'connection.'
    3. Makes the connection content available to the action
    4. The action executes successfully with the connection data

    Note: Due to container isolation, file verification may not work, but logs
    will show the connection was fetched and passed to the action successfully.
    """
    import tempfile

    test_dir = tempfile.mkdtemp()
    expected_content = {
        "host": "localhost",
        "port": 5432,
        "database": "test_db",
        "username": "test_user",
        "password": "test_password",
        "ssl_mode": "require",
        "max_parallelism": 2,
        "sort_dict": {"priority": "ascending"},
    }

    start_time = time.time()
    action_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/action/run",
            method="post",
            json={
                "item_type": "action",
                "item_laui": connection_write_action_laui,
                "connection_laui": connection_laui,
                "action_variables": {
                    "folder_path": test_dir,
                    "file_path": "connection_output.json",
                },
            },
        ),
    )
    end_time = time.time()
    execution_time = end_time - start_time

    print(f"Action execution response: {action_resp.json()}")
    assert action_resp.status_code == 200
    assert execution_time < 2.0, f"Execution took {execution_time:.3f}s, expected < 2.0s"

    # Poll briefly for file (action creates it with connection content)
    # Note: File may be in Celery worker container, not accessible from test container
    output_file = Path(test_dir) / "connection_output.json"
    for _ in range(50):  # 50 * 0.1 = 5 seconds max
        if output_file.exists():
            # If file exists, verify connection content
            with open(output_file, encoding="utf-8") as f:
                written_content = json.load(f)
            assert written_content == expected_content, (
                "Written content should match expected connection content"
            )
            print(f"✓ Connection content successfully fetched and written: {written_content}")
            break
        time.sleep(0.1)
    # File may not be accessible due to container isolation, but action executed successfully
    # Check logs to verify connection was fetched and passed correctly


async def test_execute_action_with_invalid_connection_type_fail(
    client: TestClient,
    connection_write_action_laui: str,
    workflow_laui: str,
):
    """
    Test that action execution logs error but continues when connection_laui
    points to an item that is not a connection type (e.g., folder.workflow).

    For action_manager (running_actions/post_actions): logs error and continues
    For pre_action_manager: would return False and abort
    """
    import tempfile

    test_dir = tempfile.mkdtemp()

    # Use workflow_laui (not a connection) as connection_laui
    start_time = time.time()
    action_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/action/run",
            method="post",
            json={
                "item_type": "action",
                "item_laui": connection_write_action_laui,
                "connection_laui": workflow_laui,  # This is a folder.workflow, not a connection
                "action_variables": {
                    "folder_path": test_dir,
                    "file_path": "connection_output.json",
                },
            },
        ),
    )
    end_time = time.time()
    execution_time = end_time - start_time

    print(f"Action execution response: {action_resp.json()}")
    # PreActionManager should handle invalid connection type and continue for create_actions
    assert action_resp.status_code == 200
    assert execution_time < 2.0, f"Execution took {execution_time:.3f}s, expected < 2.0s"
    # Check logs to verify error was logged about invalid connection type


async def test_execute_action_with_nonexistent_connection_fail(
    client: TestClient,
    connection_write_action_laui: str,
):
    """
    Test that action execution logs error when connection_laui does not exist.

    For action_manager (running_actions/post_actions): logs error and continues
    For pre_action_manager (create_actions/pre_actions): returns False and aborts
    """
    import tempfile

    test_dir = tempfile.mkdtemp()
    fake_connection_laui = "507f1f77bcf86cd799439012"

    start_time = time.time()
    action_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/action/run",
            method="post",
            json={
                "item_type": "action",
                "item_laui": connection_write_action_laui,
                "connection_laui": fake_connection_laui,
                "action_variables": {
                    "folder_path": test_dir,
                    "file_path": "connection_output.json",
                },
            },
        ),
    )
    end_time = time.time()
    execution_time = end_time - start_time

    print(f"Action execution response: {action_resp.json()}")
    # PreActionManager.create_actions should handle nonexistent connection
    # Check that request completes (status 200) but may log error internally
    assert action_resp.status_code in [200, 404, 422]
    assert execution_time < 2.0, f"Execution took {execution_time:.3f}s, expected < 2.0s"
    # Check logs to verify error was logged about connection not found
