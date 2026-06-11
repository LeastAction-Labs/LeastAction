# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from pathlib import Path

from src.common.logger.logger import log_error, log_info


def run(least_action_action_object, folder_path, file_path, file_content):
    """
    Create a folder, create a file with content, check if file exists, then delete it.

    Args:
        least_action_action_object: Action metadata object
        folder_path: Path to the folder to create
        file_path: Path to the file to create (relative to folder_path or absolute)
        file_content: Content to write to the file

    Returns:
        True if all operations succeed, False otherwise
    """
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
            log_error(
                "action",
                "run",
                "permission_error",
                f"Permission denied creating folder {folder}: {str(e)}",
            )
            return False
        except OSError as e:
            log_error("action", "run", "folder_error", f"Error creating folder {folder}: {str(e)}")
            return False

        # Check if folder exists (edge case: folder_path might be invalid)
        if not folder.exists():
            log_error(
                "action",
                "run",
                "folder_not_exists",
                f"Folder does not exist after creation: {folder}",
            )
            return False

        # Create file with content (will overwrite if exists)
        try:
            file.parent.mkdir(parents=True, exist_ok=True)  # Ensure parent directories exist
            with open(file, "w", encoding="utf-8") as f:
                f.write(file_content)
            log_info("action", "run", "file_created", f"File created: {file}")
        except PermissionError as e:
            log_error(
                "action",
                "run",
                "permission_error",
                f"Permission denied creating file {file}: {str(e)}",
            )
            return False
        except OSError as e:
            log_error("action", "run", "file_error", f"Error creating file {file}: {str(e)}")
            return False

        # Check if file exists
        if not file.exists():
            log_error(
                "action", "run", "file_not_exists", f"File does not exist after creation: {file}"
            )
            return False

        log_info("action", "run", "file_verified", f"File verified to exist: {file}")

        # Delete the file
        try:
            if file.exists():
                file.unlink()
                log_info("action", "run", "file_deleted", f"File deleted: {file}")
            else:
                log_info(
                    "action", "run", "file_already_deleted", f"File already does not exist: {file}"
                )
        except PermissionError as e:
            log_error(
                "action",
                "run",
                "permission_error",
                f"Permission denied deleting file {file}: {str(e)}",
            )
            return False
        except OSError as e:
            log_error("action", "run", "delete_error", f"Error deleting file {file}: {str(e)}")
            return False

        # Verify file is deleted
        if file.exists():
            log_error(
                "action", "run", "file_still_exists", f"File still exists after deletion: {file}"
            )
            return False

        log_info("action", "run", "success", "All file system operations completed successfully")
        return True

    except Exception as e:
        log_error("action", "run", "unexpected_error", f"Unexpected error: {str(e)}")
        return False
