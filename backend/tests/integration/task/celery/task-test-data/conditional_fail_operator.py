# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import json
import time


def initialize(least_action_task_object):
    """
    Args:
        least_action_task_object: Task object containing configuration

    Returns:
        dict: Client object (minimal for this operator)
    """
    try:
        client = {"type": "fail_operator", "initialized": True}
        return client

    except Exception:
        raise


def run(least_action_task_object, client):
    """
    Args:
        least_action_task_object: Task object containing payload with sleep duration
        client: Client object from initialize()

    Returns:
        dict: Contains execution_type, result, and sleep details
    """
    try:
        payload_str = least_action_task_object.get("payload", "")

        # Parse payload - expecting JSON string
        try:
            payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON payload: {str(e)}")

        time.sleep(1)

        result = {
            "execution_type": "sync",
            "result": {"message": "task passed" if payload == "pass" else "task failed"},
            "status": "success" if payload == "pass" else "error",
        }

        return result

    except ValueError:
        raise

    except Exception:
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

        if execution_type == "sync":
            result = run_details.get("result", {})

            return {
                "status": run_details.get("status", "error"),
                "message": result.get("message", ""),
                "output": result,
            }

        return {
            "status": "failed",
            "message": f"Unexpected execution type: {execution_type}",
            "output": {},
        }

    except Exception as e:
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
        # Release client reference
        if client:
            client = None
    except Exception:
        pass
