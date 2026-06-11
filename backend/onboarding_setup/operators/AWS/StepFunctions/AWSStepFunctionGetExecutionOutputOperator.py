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

        execution_arn = payload.get("execution_arn")
        if not execution_arn:
            msg = "Missing required payload field: execution_arn"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        log_info("task", "run", "describe_execution",
                 f"Fetching execution details for: {execution_arn}")

        response = client.describe_execution(executionArn=execution_arn)

        exec_status = response.get("status")
        start_date = str(response.get("startDate", ""))
        stop_date = str(response.get("stopDate", ""))
        output_raw = response.get("output")

        output = None
        if output_raw:
            try:
                output = json.loads(output_raw)
            except Exception:
                output = output_raw

        op_status = "success" if exec_status == "SUCCEEDED" else "failed"

        log_info("task", "run", "execution_result",
                 f"ExecutionArn: {execution_arn} | Status: {exec_status}")

        return {
            "execution_type": "sync",
            "status": op_status,
            "result": {
                "execution_arn": execution_arn,
                "state_machine_arn": response.get("stateMachineArn"),
                "execution_name": response.get("name"),
                "execution_status": exec_status,
                "output": output,
                "start_date": start_date,
                "stop_date": stop_date,
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
             "StepFunctionGetExecutionOutput is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "StepFunctionGetExecutionOutput completed",
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
                     f"ExecutionStatus: {result.get('execution_status')}")
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
    "execution_arn": "arn:aws:states:us-east-1:123456789012:execution:MyStateMachine:my-execution-run-1"
}

prompt = (
    "Retrieve the output and final status of a completed Step Functions execution. "
    "Reads execution_arn from payload and calls describe_execution. "
    "Parses the output JSON string into a dict if possible. "
    "Returns status:success when execution_status == 'SUCCEEDED', otherwise status:failed. "
    "Auth: IAM role via STS first, fall back to access keys from connection."
)

install_docs = """# AWSStepFunctionGetExecutionOutput — Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": ["states:DescribeExecution"],
      "Resource": "*"
    }

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance — no connection keys needed       |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
| Session token | Optionally add aws_session_token in connection                |
"""

guide_docs = """# AWSStepFunctionGetExecutionOutput — Operator Guide

## What it does

Retrieves the final output and status of a Step Functions execution by calling
describe_execution. Returns the parsed output dict, execution status, start/stop
timestamps, and the execution ARN.

This is the companion to AWSStepFunctionStartExecution — run that operator first to
get an execution_arn, then use this operator to collect results once the execution
is expected to have completed.

The output field in the AWS response is a raw JSON string — this operator automatically
parses it into a Python dict for downstream use.

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
      "execution_arn": "arn:aws:states:us-east-1:123456789012:execution:MyStateMachine:my-run"
    }

| Field         | Required | Description                                              |
|---------------|----------|----------------------------------------------------------|
| execution_arn | Yes      | Full ARN of the execution (from AWSStepFunctionStartExecution) |

---

## Output (on success)

    {
      "execution_arn": "arn:aws:states:...",
      "state_machine_arn": "arn:aws:states:...",
      "execution_name": "my-execution-run-1",
      "execution_status": "SUCCEEDED",
      "output": {"result": "ok"},
      "start_date": "2026-04-09 12:45:13+00:00",
      "stop_date": "2026-04-09 12:45:14+00:00"
    }

op_status is "success" when execution_status == "SUCCEEDED", "failed" otherwise
(FAILED, TIMED_OUT, ABORTED).

---

## Scenarios and Edge Cases

Execution still RUNNING:
  describe_execution returns status RUNNING and no output. op_status will be "failed".
  Schedule this operator to run after sufficient time, or poll with a retry task.

Execution FAILED:
  output field may contain error details from the state machine's Catch block.

ExecutionDoesNotExist:
  Raised if execution_arn is invalid or the execution has been deleted.
  Caught as ClientError, returned as status:failed.
"""

description = (
    "Retrieves the final output and status of a completed AWS Step Functions execution. "
    "Calls describe_execution with the execution_arn from payload and automatically parses "
    "the output JSON string into a Python dict. "
    "Returns status:success when execution_status is 'SUCCEEDED', status:failed for "
    "FAILED, TIMED_OUT, ABORTED, or still-RUNNING executions. "
    "Auth: IAM role via STS first, fallback to flat access keys in connection. "
    "Designed to be paired with AWSStepFunctionStartExecution — use that operator first "
    "to start an execution and obtain the execution_arn."
)

publisher = "LeastActionLabs"

metadata = {
    "service": "StepFunctions",
    "category": "Orchestration",
    "tags": ["stepfunctions", "state-machine", "execution", "output", "aws"],
    "airflow_equivalent": "StepFunctionGetExecutionOutputOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

If the execution is still RUNNING, describe_execution returns status RUNNING with no output — this operator returns op_status:failed in that case. Schedule a retry after sufficient time or use a polling task. The output field in the AWS response is a raw JSON string — this operator auto-parses it to a dict. For FAILED executions, the output may contain error details from the state machine's Catch block. Express workflow executions are not queryable via describe_execution — only Standard workflows are supported.
"""
