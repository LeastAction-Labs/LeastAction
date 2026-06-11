# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import json
import os
import time

from src.common.logger.logger import log_error, log_info


def initialize(least_action_task_object):
    try:
        log_info(
            "task", "initialize", "creating_context", "Setting up file write operation context"
        )
        context = {"initialized": True, "task_id": least_action_task_object.get("laui")}
        log_info(
            "task", "initialize", "context_created", "File write context initialized successfully"
        )
        return context
    except Exception as e:
        log_error("task", "initialize", "error", f"Initialization failed: {str(e)}")
        raise


def run(least_action_task_object, client):
    payload = least_action_task_object.get("payload", "{}")
    try:
        log_info("task", "run", "parsing_payload", "Parsing payload for file write operation")
        if isinstance(payload, str):
            payload_data = json.loads(payload)
        else:
            payload_data = payload
        file_path = payload_data.get("path")
        message = payload_data.get("message")
        append = payload_data.get("append", False)
        delay = payload_data.get("delay", 0)

        if not file_path:
            raise ValueError("'path' is required in payload")
        if not message:
            raise ValueError("'message' is required in payload")
        log_info(
            "task", "run", "validate_input", f"Writing {len(message)} characters to {file_path}"
        )

        # Add delay if specified (for cancellation testing)
        if delay > 0:
            log_info("task", "run", "delaying", f"Sleeping for {delay} seconds")
            time.sleep(delay)

        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            log_info("task", "run", "create_directory", f"Creating directory: {directory}")
            os.makedirs(directory, exist_ok=True)
        mode = "a" if append else "w"
        log_info("task", "run", "write_file", f"Writing message to file: {file_path}")
        with open(file_path, mode, encoding="utf-8") as f:
            f.write(message)
            if append and not message.endswith("\n"):
                f.write("\n")
        if not os.path.exists(file_path):
            raise OSError("File was not created successfully")
        file_size = os.path.getsize(file_path)
        log_info("task", "run", "file_written", "Message written successfully")
        return {
            "execution_type": "sync",
            "file_path": file_path,
            "message": message,
            "append": append,
            "file_size": file_size,
            "success": True,
            "status": "success",
        }
    except Exception as e:
        log_error("task", "run", "execution_error", f"Error during file write: {str(e)}")
        raise


def check_completion(least_action_task_object, client, run_details):
    try:
        execution_type = run_details.get("execution_type")
        success = run_details.get("success", False)
        file_path = run_details.get("file_path")
        file_size = run_details.get("file_size", 0)
        log_info(
            "task",
            "check_completion",
            "checking_status",
            f"Checking status of file write to {file_path}",
        )
        if execution_type == "sync":
            if success and os.path.exists(file_path):
                log_info(
                    "task",
                    "check_completion",
                    "status_checked",
                    f"File write completed successfully: {file_path}",
                )
                return {
                    "status": "success",
                    "message": f"File written successfully to {file_path}",
                    "output": {
                        "file_path": file_path,
                        "file_size": file_size,
                        "append_mode": run_details.get("append", False),
                    },
                }
            else:
                return {
                    "status": "failed",
                    "message": "File write operation failed",
                    "output": {"file_path": file_path},
                }
    except Exception as e:
        log_error("task", "check_completion", "check_error", f"Error checking completion: {str(e)}")
        return {"status": "failed", "message": f"Error checking completion: {str(e)}", "output": {}}


def finish(least_action_task_object, client, completion_details, run_details):
    try:
        log_info("task", "finish", "cleaning_up", "Cleaning up file write operation resources")
        if completion_details and completion_details.get("status") == "success":
            log_info(
                "task", "finish", "task_completed", "File write operation completed successfully"
            )
        else:
            log_info("task", "finish", "task_failed", "File write operation failed")
        log_info("task", "finish", "cleanup_complete", "Resource cleanup completed")
    except Exception as e:
        log_error("task", "finish", "cleanup_error", f"Error during cleanup: {str(e)}")
        raise
