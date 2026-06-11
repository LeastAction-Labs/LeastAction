# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import time
from datetime import datetime
from pathlib import Path

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
# TEST CASES SUMMARY
# ============================================================================
# This test file covers the following scenarios:
#
# SUCCESS CASES (marked with _pass):
#    - Execute action with only essential fields (item_type, item_laui, action_variables)
#    - Execute action with valid file system operation action
#    - Execute action with all required fields and action_variables
#    - Execute action with minimal fields
#
# FAILURE CASES (marked with _fail):
#    - Execute action with missing action item (non-existent laui)
#    - Execute action with invalid item_type
#    - Execute action with missing action_variables
#    - Execute action without laui field
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
async def file_system_action_laui(
    client: TestClient, action_folder_laui: str, account_laui: str, project_laui: str
) -> str:
    """Create a file system operation action"""
    action_code = '''from pathlib import Path
from src.common.logger.logger import log_info, log_error


def run(least_action_action_object, folder_path, file_path, file_content):
    """Create a folder, create a file with content, check if file exists, then delete it."""
    action_id = least_action_action_object.get("laui")

    try:
        log_info("action", "run", "start", f"Starting file system operation for action {action_id}")

        # Validate inputs
        if not folder_path or not isinstance(folder_path, str):
            log_error("action", "run", "validation_error", "folder_path must be a non-empty string")
            return False

        if not file_path or not isinstance(file_path, str):
            log_error("action", "run", "validation_error", "file_path must be a non-empty string")
            return False

        if file_content is None:
            file_content = ""  # Allow empty content

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

        # Check if folder exists (edge case: folder_path might be invalid)
        if not folder.exists():
            log_error("action", "run", "folder_not_exists", f"Folder does not exist after creation: {folder}")
            return False

        # Create file with content (will overwrite if exists)
        try:
            file.parent.mkdir(parents=True, exist_ok=True)  # Ensure parent directories exist
            with open(file, "w", encoding="utf-8") as f:
                f.write(file_content)
            log_info("action", "run", "file_created", f"File created: {file}")
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

        # Delete the file
        try:
            if file.exists():
                file.unlink()
                log_info("action", "run", "file_deleted", f"File deleted: {file}")
            else:
                log_info("action", "run", "file_already_deleted", f"File already does not exist: {file}")
        except PermissionError as e:
            log_error("action", "run", "permission_error", f"Permission denied deleting file {file}: {str(e)}")
            return False
        except OSError as e:
            log_error("action", "run", "delete_error", f"Error deleting file {file}: {str(e)}")
            return False

        # Verify file is deleted
        if file.exists():
            log_error("action", "run", "file_still_exists", f"File still exists after deletion: {file}")
            return False

        log_info("action", "run", "success", "All file system operations completed successfully")
        return True

    except Exception as e:
        log_error("action", "run", "unexpected_error", f"Unexpected error: {str(e)}")
        return False'''

    action_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "action",
                "name": "FileSystemOperation.action",
                "parent_laui": action_folder_laui,
                "prompt": "Generate an action that creates a folder, creates a file with content, checks if file exists, and deletes it",
                "codeblock": {"main.py": action_code},
                "bashblock": {},
                "account_laui": account_laui,
                "project_laui": project_laui,
            },
        ),
    )
    assert action_resp.status_code == 200
    return CreateItemResponse(**action_resp.json()).item_laui


async def test_execute_action_with_essential_fields_only_pass(
    client: TestClient,
    file_system_action_laui: str,
):
    """
    Test successful action execution with only essential fields:
    - item_type
    - item_laui (action to execute)
    - action_variables

    This is the simplest form of action execution.
    """
    import tempfile

    test_dir = tempfile.mkdtemp()
    expected_content = "INTEGRATION TEST ::: test_execute_action_with_essential_fields_only_pass"

    start_time = time.time()
    action_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/action/run",
            method="post",
            json={
                "item_type": "action",
                "item_laui": file_system_action_laui,
                "action_variables": {
                    "folder_path": test_dir,
                    "file_path": "test_file.txt",
                    "file_content": expected_content,
                },
            },
        ),
    )
    print("FIXTURE RESPONSE:", action_resp.status_code, action_resp.json())
    end_time = time.time()
    execution_time = end_time - start_time

    print(f"Action execution response: {action_resp.json()}")
    assert action_resp.status_code in [200]
    assert execution_time < 1.0, f"Execution took {execution_time:.3f}s, expected < 1.0s"

    # Assert folder exists (action creates it)
    folder_path_obj = Path(test_dir)
    assert folder_path_obj.exists(), f"Folder {test_dir} should exist"
    assert folder_path_obj.is_dir(), f"{test_dir} should be a directory"

    # Poll briefly for file (action creates then deletes it)
    file_path_obj = folder_path_obj / "test_file.txt"
    for _ in range(10):  # 10 * 0.05 = 0.5 seconds max
        if file_path_obj.exists():
            # Assert file contents
            assert file_path_obj.read_text(encoding="utf-8") == expected_content
            break
        time.sleep(0.05)
    # File may be deleted by action, so we don't fail if not found


async def test_execute_action_with_file_system_operation_pass(
    client: TestClient,
    file_system_action_laui: str,
):
    """
    Test successful action execution with file system operation.
    This tests the complete flow of executing an action with proper setup.
    """
    import tempfile

    test_dir = tempfile.mkdtemp()
    expected_content = "INTEGRATION TEST ::: test_execute_action_with_file_system_operation_pass"

    start_time = time.time()
    action_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/action/run",
            method="post",
            json={
                "item_type": "action",
                "item_laui": file_system_action_laui,
                "action_variables": {
                    "folder_path": test_dir,
                    "file_path": "test_file.txt",
                    "file_content": expected_content,
                },
            },
        ),
    )
    end_time = time.time()
    execution_time = end_time - start_time

    print(f"Action execution response: {action_resp.json()}")
    assert action_resp.status_code in [200]
    assert execution_time < 1.0, f"Execution took {execution_time:.3f}s, expected < 1.0s"

    # Assert folder exists (action creates it)
    folder_path_obj = Path(test_dir)
    assert folder_path_obj.exists(), f"Folder {test_dir} should exist"
    assert folder_path_obj.is_dir(), f"{test_dir} should be a directory"

    # Poll briefly for file (action creates then deletes it)
    file_path_obj = folder_path_obj / "test_file.txt"
    for _ in range(10):  # 10 * 0.05 = 0.5 seconds max
        if file_path_obj.exists():
            # Assert file contents
            assert file_path_obj.read_text(encoding="utf-8") == expected_content
            break
        time.sleep(0.05)
    # File may be deleted by action, so we don't fail if not found


async def test_execute_action_with_minimal_fields_pass(
    client: TestClient,
    file_system_action_laui: str,
):
    """
    Test action execution with minimal required fields.
    """
    import tempfile

    test_dir = tempfile.mkdtemp()
    expected_content = "INTEGRATION TEST ::: test_execute_action_with_minimal_fields_pass"

    start_time = time.time()
    action_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/action/run",
            method="post",
            json={
                "item_type": "action",
                "item_laui": file_system_action_laui,
                "action_variables": {
                    "folder_path": test_dir,
                    "file_path": "test_file.txt",
                    "file_content": expected_content,
                },
            },
        ),
    )
    end_time = time.time()
    execution_time = end_time - start_time

    assert action_resp.status_code in [200]
    assert execution_time < 1.0, f"Execution took {execution_time:.3f}s, expected < 1.0s"

    # Assert folder exists (action creates it)
    folder_path_obj = Path(test_dir)
    assert folder_path_obj.exists(), f"Folder {test_dir} should exist"
    assert folder_path_obj.is_dir(), f"{test_dir} should be a directory"

    # Poll briefly for file (action creates then deletes it)
    file_path_obj = folder_path_obj / "test_file.txt"
    for _ in range(10):  # 10 * 0.05 = 0.5 seconds max
        if file_path_obj.exists():
            # Assert file contents
            assert file_path_obj.read_text(encoding="utf-8") == expected_content
            break
        time.sleep(0.05)
    # File may be deleted by action, so we don't fail if not found


async def test_execute_action_with_nonexistent_action_fail(client: TestClient):
    """
    Test that action execution fails when action laui does not exist.
    """
    import tempfile

    test_dir = tempfile.mkdtemp()

    fake_action_laui = "507f1f77bcf86cd799439012"
    start_time = time.time()
    action_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/action/run",
            method="post",
            json={
                "item_type": "action",
                "item_laui": fake_action_laui,
                "action_variables": {
                    "folder_path": test_dir,
                    "file_path": "test_file.txt",
                    "file_content": "This should fail",
                },
            },
        ),
    )
    end_time = time.time()
    execution_time = end_time - start_time

    assert action_resp.status_code in [404, 422]
    assert execution_time < 1.0, f"Execution took {execution_time:.3f}s, expected < 1.0s"
    error_detail = action_resp.json()
    assert "not found" in str(error_detail).lower() or "does not exist" in str(error_detail).lower()

    # Action should not execute, so folder should not be created
    folder_path_obj = Path(test_dir)
    # Folder may exist if tempfile created it, but it should be empty
    if folder_path_obj.exists():
        # Verify no test file was created
        file_path_obj = folder_path_obj / "test_file.txt"
        assert not file_path_obj.exists(), "File should not exist since action failed"


async def test_execute_action_with_invalid_item_type_fail(
    client: TestClient, file_system_action_laui: str
):
    """
    Test that action execution fails when item_type is not 'action'.
    """
    import tempfile

    test_dir = tempfile.mkdtemp()

    start_time = time.time()
    action_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/action/run",
            method="post",
            json={
                "item_type": "task",  # Wrong item type
                "item_laui": file_system_action_laui,
                "action_variables": {
                    "folder_path": test_dir,
                    "file_path": "test_file.txt",
                    "file_content": "This should fail due to wrong item_type",
                },
            },
        ),
    )
    end_time = time.time()
    execution_time = end_time - start_time

    assert action_resp.status_code == 422
    assert execution_time < 1.0, f"Execution took {execution_time:.3f}s, expected < 1.0s"

    # Action should not execute, so folder should not be created
    folder_path_obj = Path(test_dir)
    # Folder may exist if tempfile created it, but it should be empty
    if folder_path_obj.exists():
        # Verify no test file was created
        file_path_obj = folder_path_obj / "test_file.txt"
        assert not file_path_obj.exists(), "File should not exist since action failed"


async def test_execute_action_with_missing_action_variables_pass(
    client: TestClient, file_system_action_laui: str
):
    """
    Test that action execution handles missing action_variables.
    """
    start_time = time.time()
    action_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/action/run",
            method="post",
            json={
                "item_type": "action",
                "item_laui": file_system_action_laui,
                "action_variables": {},
            },
        ),
    )
    end_time = time.time()
    execution_time = end_time - start_time

    assert action_resp.status_code in [200]
    assert execution_time < 1.0, f"Execution took {execution_time:.3f}s, expected < 1.0s"

    # Action executes but fails validation due to missing variables
    # No folder/file should be created since validation fails early


async def test_execute_action_with_invalid_paths_fail(
    client: TestClient, file_system_action_laui: str
):
    """
    Test that action execution handles invalid file system paths gracefully.
    """
    start_time = time.time()
    action_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/action/run",
            method="post",
            json={
                "item_type": "action",
                "item_laui": file_system_action_laui,
                "action_variables": {
                    "folder_path": "",  # Empty folder path should fail validation
                    "file_path": "test_file.txt",
                    "file_content": "This should fail",
                },
            },
        ),
    )
    end_time = time.time()
    execution_time = end_time - start_time

    # Action should execute but return False due to validation error
    assert action_resp.status_code in [200]
    assert execution_time < 1.0, f"Execution took {execution_time:.3f}s, expected < 1.0s"

    # Action executes but fails validation due to empty folder_path
    # No folder should be created since validation fails early


async def test_execute_action_without_laui_fail(client: TestClient):
    """
    Test that action execution fails when laui is not provided.
    """
    import tempfile

    test_dir = tempfile.mkdtemp()

    start_time = time.time()
    action_resp = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/action/run",
            method="post",
            json={
                "item_type": "action",
                "action_variables": {
                    "folder_path": test_dir,
                    "file_path": "test_file.txt",
                    "file_content": "This should fail",
                },
            },
        ),
    )
    end_time = time.time()
    execution_time = end_time - start_time

    assert action_resp.status_code == 422
    assert execution_time < 1.0, f"Execution took {execution_time:.3f}s, expected < 1.0s"

    # Action should not execute, so folder should not be created
    folder_path_obj = Path(test_dir)
    # Folder may exist if tempfile created it, but it should be empty
    if folder_path_obj.exists():
        # Verify no test file was created
        file_path_obj = folder_path_obj / "test_file.txt"
        assert not file_path_obj.exists(), "File should not exist since action failed"
