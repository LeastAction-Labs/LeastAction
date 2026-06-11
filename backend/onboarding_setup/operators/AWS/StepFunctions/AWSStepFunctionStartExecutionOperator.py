# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
operator_type = "AWS"

codeblock = {"main.py": """import json
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from src.common.logger.logger import log_info, log_error


def _build_stepfunctions_client(connection: dict):
    region = connection.get("region", "us-east-1")
    access_key = connection.get("aws_access_key_id")
    secret_key = connection.get("aws_secret_access_key")
    session_token = connection.get("aws_session_token")
    assume_role_arn = connection.get("assume_iam_role")

    # Case 1: Explicit credentials
    if access_key and secret_key:
        log_info("task", "initialize", "auth_keys",
                 f"Using explicit access key ending ...{access_key[-4:]}")
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token,
            region_name=region,
        )
        return session.client("stepfunctions")

    # Case 2: Assume IAM role via STS
    if assume_role_arn:
        log_info("task", "initialize", "auth_assume_role",
                 f"Assuming IAM role: {assume_role_arn}")
        sts = boto3.client("sts", region_name=region)
        assumed = sts.assume_role(RoleArn=assume_role_arn, RoleSessionName="leastaction_session")
        creds = assumed["Credentials"]
        session = boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region,
        )
        return session.client("stepfunctions")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info("task", "initialize", "auth_default",
             "Using default AWS credential chain (instance profile / ECS task role / env / config)")
    return boto3.Session(region_name=region).client("stepfunctions")


def initialize(least_action_task_object):
    try:
        connection = least_action_task_object.get("connection", {})
        if isinstance(connection, str):
            connection = json.loads(connection)

        log_info("task", "initialize", "building_client",
                 f"region={connection.get('region', 'us-east-1')}")

        client = _build_stepfunctions_client(connection)
        log_info("task", "initialize", "client_ready",
                 "Step Functions client initialized")
        return client

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "initialize", "client_error", f"({error_code}) {error_msg}")
        raise
    except Exception as e:
        log_error("task", "initialize", "init_failed", f"Error: {str(e)}")
        raise


def run(least_action_task_object, client):
    try:
        payload = least_action_task_object.get("payload", {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                log_error("task", "run", "payload_parse_error", "Failed to parse payload as JSON")
                return {"status": "failed", "execution_type": "sync", "result": None,
                        "error": "Invalid payload format — expected flat JSON object"}

        state_machine_arn = payload.get("state_machine_arn")
        if not state_machine_arn:
            msg = "Missing required payload field: state_machine_arn"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        execution_name = payload.get("execution_name")
        execution_input = payload.get("input", {})

        kwargs = {
            "stateMachineArn": state_machine_arn,
            "input": json.dumps(execution_input),
        }
        if execution_name:
            kwargs["name"] = execution_name

        log_info("task", "run", "start_execution",
                 f"Starting Step Functions execution for: {state_machine_arn}")

        response = client.start_execution(**kwargs)
        execution_arn = response.get("executionArn")
        start_date = str(response.get("startDate", ""))

        log_info("task", "run", "execution_started",
                 f"Execution started - ARN: {execution_arn}")

        return {
            "execution_type": "sync",
            "status": "success",
            "result": {
                "execution_arn": execution_arn,
                "state_machine_arn": state_machine_arn,
                "execution_name": execution_name,
                "start_date": start_date,
            }
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "client_error", f"({error_code}) {error_msg}")
        return {"execution_type": "sync", "status": "failed",
                "result": {"error": f"({error_code}) {error_msg}"}}
    except Exception as e:
        log_error("task", "run", "run_failed", f"Unexpected error: {str(e)}")
        return {"execution_type": "sync", "status": "failed", "result": {"error": str(e)}}


def check_completion(least_action_task_object, client, run_details):
    log_info("task", "check_completion", "sync_complete",
             "StepFunctionStartExecution is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "StepFunctionStartExecution completed",
        "output": run_details.get("result", {})
    }


def finish(least_action_task_object, client, completion_details, run_details):
    try:
        result = run_details.get("result", {})
        status = completion_details.get("status", "unknown")
        log_info("task", "finish", "final_status", f"Completed with status: {status}")
        if status == "success":
            log_info("task", "finish", "summary",
                     f"ExecutionArn: {result.get('execution_arn')} | "
                     f"StartDate: {result.get('start_date')}")
        else:
            log_error("task", "finish", "operation_failed",
                      completion_details.get("message", "No message"))
        if client:
            try:
                client.close()
                log_info("task", "finish", "client_closed", "Step Functions boto3 client closed successfully")
            except Exception as close_error:
                log_error("task", "finish", "client_close_error", f"Error closing client: {str(close_error)}")
        log_info("task", "finish", "cleanup_complete", "Cleanup complete")
    except Exception as e:
        log_error("task", "finish", "cleanup_error", f"Error in finish: {str(e)}")
"""}

bashblock = {"main.sh": """#!/bin/bash
set -e
pip install boto3>=1.28.0
pip install botocore>=1.31.0
echo "Dependencies installed successfully"
"""}

connection = {
    "region": "us-east-1"
}

payload = {
    "state_machine_arn": "arn:aws:states:us-east-1:123456789012:stateMachine:MyStateMachine",
    "execution_name": "my-execution-run-1",
    "input": {"key": "value"}
}

prompt = (
    "Start an AWS Step Functions state machine execution. "
    "Payload must include state_machine_arn. execution_name and input are optional. "
    "The input dict is serialized to JSON before being passed to start_execution. "
    "No connectivity check in initialize() — Step Functions has no lightweight list call available. "
    "Auth: IAM role via STS first, fall back to access keys from connection. "
    "Return execution_arn, state_machine_arn, execution_name, and start_date on success. "
    "Pair with AWSStepFunctionGetExecutionOutput to retrieve results after execution completes."
)

install_docs = """# AWSStepFunctionStartExecution — Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": ["states:StartExecution"],
      "Resource": "*"
    }

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance — no connection keys needed       |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
| Session token | Optionally add aws_session_token in connection                |
"""

guide_docs = """# AWSStepFunctionStartExecution — Operator Guide

## What it does

Starts an AWS Step Functions state machine execution and returns the execution ARN
immediately. The execution runs asynchronously — this operator does not wait for it
to complete. Use AWSStepFunctionGetExecutionOutput to poll the result once the
execution is expected to be done.

The input payload is serialized to JSON and passed directly to the state machine.
execution_name is optional — if omitted, AWS generates a unique name automatically.

Note: initialize() does not perform a connectivity check because Step Functions has
no lightweight read-only call available without additional permissions. Auth is
validated implicitly when start_execution is called.

---

## Auth

1. IAM role — tried first via STS. Used automatically if available. No keys needed in connection.
2. Access keys — fallback to aws_access_key_id + aws_secret_access_key from connection.

---

## Connection

    {
      "region": "us-east-1",
      "aws_access_key_id": "",       // optional — omit to use IAM role
      "aws_secret_access_key": "",   // optional — omit to use IAM role
      "aws_session_token": ""        // optional — for temporary credentials
    }

---

## Payload

    {
      "state_machine_arn": "arn:aws:states:us-east-1:123456789012:stateMachine:MyStateMachine",
      "execution_name": "my-execution-run-1",
      "input": {"key": "value"}
    }

| Field             | Required | Description                                              |
|-------------------|----------|----------------------------------------------------------|
| state_machine_arn | Yes      | Full ARN of the state machine to execute                 |
| execution_name    | No       | Unique name for this execution (auto-generated if omitted) |
| input             | No       | JSON-serializable dict passed as input to the execution  |

---

## Output (on success)

    {
      "execution_arn": "arn:aws:states:us-east-1:...:execution:MyStateMachine:my-run",
      "state_machine_arn": "arn:aws:states:...",
      "execution_name": "my-execution-run-1",
      "start_date": "2026-04-09 12:45:13.902000+00:00"
    }

Use execution_arn with AWSStepFunctionGetExecutionOutput to retrieve the final output.

---

## Scenarios and Edge Cases

Duplicate execution_name:
  AWS returns ExecutionAlreadyExists. Caught as ClientError, returned as status:failed.
  Use unique names (e.g. include a timestamp) to avoid conflicts.

State machine does not exist:
  AWS returns StateMachineDoesNotExist. Caught as ClientError, returned as status:failed.

IAM permission missing:
  states:StartExecution not granted → AccessDeniedException. Caught as ClientError.
"""

description = (
    "Starts an AWS Step Functions state machine execution and returns the execution ARN "
    "immediately without waiting for completion. The payload input dict is automatically "
    "serialized to JSON before being passed to the state machine. execution_name is optional — "
    "AWS generates one if omitted. No connectivity check in initialize() since Step Functions "
    "has no lightweight read-only endpoint. "
    "Auth: IAM role via STS first, fallback to flat access keys in connection. "
    "Returns execution_arn, state_machine_arn, execution_name, and start_date on success. "
    "Pair with AWSStepFunctionGetExecutionOutput to retrieve results after the execution completes."
)

publisher = "LeastActionLabs"

metadata = {
    "service": "StepFunctions",
    "category": "Orchestration",
    "tags": ["stepfunctions", "state-machine", "execution", "aws"],
    "airflow_equivalent": "StepFunctionStartExecutionOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

start_execution returns immediately — the state machine runs asynchronously. This operator does not wait for completion. execution_name must be unique per state machine — duplicate names return ExecutionAlreadyExists. If omitted, AWS generates a UUID-based name. The input dict is auto-serialized to JSON. Use AWSStepFunctionGetExecutionOutput with the returned execution_arn to retrieve results. For Express workflows, describe_execution is not available — use CloudWatch Logs instead.
"""
