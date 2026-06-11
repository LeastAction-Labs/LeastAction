# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
"""Sleep Operator

This operator pauses execution for a specified number of seconds.
Useful for adding delays in workflows, rate limiting, or scheduling.
"""

import json
import time

from src.common.logger.logger import log_error, log_info


def initialize(least_action_task_object):
    """
    Initialize the sleep operator.

    Args:
        least_action_task_object: Task object containing configuration

    Returns:
        dict: Client object (minimal for this operator)
    """
    try:
        log_info(
            "task",
            "initialize",
            "initializing_sleep_operator",
            f"Initializing sleep operator for task: {least_action_task_object.get('laui')}",
        )

        # Create a minimal client object for this operator
        client = {"type": "sleep_operator", "initialized": True}

        log_info(
            "task",
            "initialize",
            "initialization_complete",
            "Sleep operator initialized successfully",
        )

        return client

    except Exception as e:
        log_error(
            "task", "initialize", "initialization_failed", f"Error during initialization: {str(e)}"
        )
        raise


def run(least_action_task_object, client):
    """
    Execute the sleep operation for specified seconds.

    Args:
        least_action_task_object: Task object containing payload with sleep duration
        client: Client object from initialize()

    Returns:
        dict: Contains execution_type, result, and sleep details
    """
    try:
        payload_str = least_action_task_object.get("payload", "")

        log_info(
            "task",
            "run",
            "extracting_payload",
            f"Extracting payload for task: {least_action_task_object.get('laui')}",
        )

        # Parse payload - expecting JSON string
        try:
            payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
        except json.JSONDecodeError as e:
            log_error(
                "task", "run", "payload_parse_error", f"Failed to parse payload as JSON: {str(e)}"
            )
            raise ValueError(f"Invalid JSON payload: {str(e)}")

        # Extract sleep duration
        sleep_seconds = payload.get("seconds")

        if sleep_seconds is None:
            error_msg = "No 'seconds' parameter provided in payload"
            log_error("task", "run", "missing_seconds_parameter", error_msg)
            raise ValueError(error_msg)

        # Validate sleep duration
        try:
            sleep_seconds = float(sleep_seconds)
        except (ValueError, TypeError):
            error_msg = f"Invalid 'seconds' value: {sleep_seconds}. Must be a number."
            log_error("task", "run", "invalid_seconds_value", error_msg)
            raise ValueError(error_msg)

        # Validate that sleep duration is non-negative
        if sleep_seconds < 0:
            error_msg = f"Sleep duration cannot be negative: {sleep_seconds}"
            log_error("task", "run", "negative_sleep_duration", error_msg)
            raise ValueError(error_msg)

        log_info("task", "run", "sleep_starting", f"Starting sleep for {sleep_seconds} seconds")

        # Record start time
        start_time = time.time()

        # Execute sleep
        time.sleep(sleep_seconds)

        # Record end time
        end_time = time.time()
        actual_sleep_duration = end_time - start_time

        log_info(
            "task",
            "run",
            "sleep_completed",
            f"Sleep completed. Requested: {sleep_seconds}s, Actual: {actual_sleep_duration:.4f}s",
        )

        result = {
            "execution_type": "sync",  # Sleep is a synchronous operation
            "result": {
                "requested_seconds": sleep_seconds,
                "actual_seconds": round(actual_sleep_duration, 4),
                "message": f"Successfully slept for {sleep_seconds} seconds",
            },
            "status": "success",
            "timestamp": end_time,
        }

        log_info("task", "run", "run_completed", "Run method completed successfully")

        return result

    except ValueError as e:
        log_error("task", "run", "validation_error", f"Validation error: {str(e)}")
        raise

    except Exception as e:
        log_error("task", "run", "run_failed", f"Unexpected error during run: {str(e)}")
        raise


def check_completion(least_action_task_object, client, run_details):
    """
    Check completion status for the sleep operation.

    Args:
        least_action_task_object: Task object
        client: Client object from initialize()
        run_details: Results from run() method

    Returns:
        dict: Status dictionary with completion state
    """
    try:
        execution_type = run_details.get("execution_type")

        log_info(
            "task",
            "check_completion",
            "checking_completion_status",
            f"Checking completion status for task: {least_action_task_object.get('laui')}",
        )

        # Sleep is a synchronous operation, so it's always complete
        if execution_type == "sync":
            log_info(
                "task",
                "check_completion",
                "sync_operation_complete",
                "Synchronous sleep operation completed",
            )

            result = run_details.get("result", {})

            return {
                "status": "success",
                "message": "Sleep operation completed successfully",
                "output": result,
            }

        # Fallback (should not reach here for sleep operator)
        log_error(
            "task",
            "check_completion",
            "unexpected_execution_type",
            f"Unexpected execution type: {execution_type}",
        )

        return {
            "status": "failed",
            "message": f"Unexpected execution type: {execution_type}",
            "output": {},
        }

    except Exception as e:
        log_error(
            "task",
            "check_completion",
            "check_completion_failed",
            f"Unexpected error during completion check: {str(e)}",
        )
        return {"status": "failed", "message": f"Unexpected error: {str(e)}", "output": {}}


def finish(least_action_task_object, client, completion_details, run_details):
    """
    Cleanup resources and finalize the operation.

    Args:
        least_action_task_object: Task object
        client: Client object to cleanup
        completion_details: Final completion status
        run_details: Original run results
    """
    try:
        log_info(
            "task",
            "finish",
            "starting_cleanup",
            f"Starting cleanup for task: {least_action_task_object.get('laui')}",
        )

        # Log final status
        status = completion_details.get("status", "unknown")
        message = completion_details.get("message", "No message provided")

        log_info("task", "finish", "final_status", f"Final status: {status} - {message}")

        # Log operation summary
        output = completion_details.get("output", {})
        requested_seconds = output.get("requested_seconds")
        actual_seconds = output.get("actual_seconds")

        if requested_seconds is not None and actual_seconds is not None:
            log_info(
                "task",
                "finish",
                "operation_summary",
                f"Sleep operation summary - Requested: {requested_seconds}s, Actual: {actual_seconds}s",
            )

        # Release client reference
        if client:
            log_info("task", "finish", "releasing_client", "Releasing client reference")
            client = None

        log_info("task", "finish", "cleanup_completed", "Cleanup completed successfully")

    except Exception as e:
        log_error(
            "task", "finish", "cleanup_error", f"Error during cleanup (non-critical): {str(e)}"
        )
        # Don't raise exception in finish() to avoid masking the main operation result


"""

bashblock = {}
payload = {
  "seconds": 5
}


connection = {}
"""
