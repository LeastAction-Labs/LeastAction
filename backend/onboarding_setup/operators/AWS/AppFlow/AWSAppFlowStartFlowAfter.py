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

codeblock = {"main.py": """
import json
import time
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from src.common.logger.logger import log_info, log_error


def _build_appflow_client(connection: dict):
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
        return session.client("appflow")

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
        return session.client("appflow")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info("task", "initialize", "auth_default",
             "Using default AWS credential chain (instance profile / ECS task role / env / config)")
    return boto3.Session(region_name=region).client("appflow")


def initialize(least_action_task_object):
    'Initialize and verify the AppFlow boto3 client using connection credentials.'
    try:
        connection = least_action_task_object.get("connection", {})
        if isinstance(connection, str):
            connection = json.loads(connection)

        log_info("task", "initialize", "building_client",
                 f"region={connection.get('region', 'us-east-1')}")

        client = _build_appflow_client(connection)
        client.list_flows(maxResults=1)
        log_info("task", "initialize", "connectivity_ok",
                 "AppFlow client initialized and verified")
        return client

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "initialize", "client_error", f"({error_code}) {error_msg}")
        raise
    except BotoCoreError as e:
        log_error("task", "initialize", "botocore_error", f"BotoCoreError: {str(e)}")
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
                        "error": "Invalid payload format - expected flat JSON object"}

        flow_name = payload.get("flow_name")
        checkpoint_time_str = payload.get("checkpoint_time")

        missing = []
        if not flow_name:
            missing.append("flow_name")
        if not checkpoint_time_str:
            missing.append("checkpoint_time")
        if missing:
            msg = f"Missing required payload fields: {missing}"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        checkpoint_time = datetime.fromisoformat(checkpoint_time_str.replace("Z", "+00:00"))
        poll_interval = int(payload.get("poll_interval_seconds", 15))

        log_info("task", "run", "starting_flow_after",
                 f"Starting AppFlow flow '{flow_name}', waiting for execution after {checkpoint_time_str}")

        resp = client.start_flow(flowName=flow_name)
        execution_id = resp.get("executionId")
        log_info("task", "run", "flow_started",
                 f"Flow '{flow_name}' started with executionId={execution_id}")

        terminal_statuses = {"Successful", "Error", "Canceled"}
        while True:
            records_resp = client.describe_flow_execution_records(
                flowName=flow_name, maxResults=1
            )
            executions = records_resp.get("flowExecutions", [])
            if executions:
                latest = executions[0]
                exec_status = latest.get("executionStatus")
                exec_result = latest.get("executionResult", {})
                records_processed = exec_result.get("recordsProcessed", 0)
                bytes_processed = exec_result.get("bytesProcessed", 0)
                started_at = latest.get("startedAt")

                log_info("task", "run", "polling_status",
                         f"Flow '{flow_name}' status: {exec_status}, started_at: {started_at}")

                if started_at:
                    if isinstance(started_at, datetime):
                        started_dt = started_at if started_at.tzinfo else started_at.replace(tzinfo=timezone.utc)
                    else:
                        started_dt = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))

                    if started_dt <= checkpoint_time:
                        log_info("task", "run", "waiting_after_checkpoint",
                                 f"Execution at {started_dt} is not after checkpoint {checkpoint_time_str}, waiting...")
                        time.sleep(poll_interval)
                        continue

                if exec_status in terminal_statuses:
                    final_status = "success" if exec_status == "Successful" else "failed"
                    return {
                        "execution_type": "sync",
                        "status": final_status,
                        "result": {
                            "flow_name": flow_name,
                            "execution_id": execution_id,
                            "execution_status": exec_status,
                            "records_processed": records_processed,
                            "bytes_processed": bytes_processed,
                        }
                    }
            time.sleep(poll_interval)

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "client_error", f"({error_code}) {error_msg}")
        return {"execution_type": "sync", "status": "failed",
                "result": {"error": f"({error_code}) {error_msg}"}}
    except BotoCoreError as e:
        log_error("task", "run", "transport_error", f"BotoCoreError: {str(e)}")
        return {"execution_type": "sync", "status": "failed",
                "result": {"error": f"Transport error: {str(e)}"}}
    except Exception as e:
        log_error("task", "run", "run_failed", f"Unexpected error: {str(e)}")
        return {"execution_type": "sync", "status": "failed", "result": {"error": str(e)}}


def check_completion(least_action_task_object, client, run_details):
    if run_details.get("status") == "failed":
        return {
            "status": "failed",
            "message": "AppFlow flow-after execution failed",
            "output": run_details.get("result", {})
        }
    log_info("task", "check_completion", "sync_complete",
             "AWSAppFlowStartFlowAfter is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "AppFlow flow-after execution completed",
        "output": run_details.get("result", {})
    }


def finish(least_action_task_object, client, completion_details, run_details):
    'Log final outcome and release any held resources. Returns: None'
    try:
        task_laui = least_action_task_object.get("laui")
        log_info("task", "finish", "starting_cleanup", f"Starting cleanup for task: {task_laui}")
        final_status = completion_details.get("status", "unknown")
        log_info("task", "finish", "final_status", f"Task ended with status: {final_status}")
        if client:
            try:
                client.close()
                log_info("task", "finish", "client_closed", "AppFlow boto3 client closed successfully")
            except Exception as close_error:
                log_error("task", "finish", "client_close_error", f"Error closing client: {str(close_error)}")
        if final_status == "success":
            output = completion_details.get("output", {})
            log_info("task", "finish", "operation_summary",
                     f"Flow {output.get('flow_name')} execution_id={output.get('execution_id')} "
                     f"status={output.get('execution_status')} records={output.get('records_processed')}")
        elif final_status == "failed":
            log_error("task", "finish", "operation_failed", f"Operation failed: {completion_details.get('message')}")
        else:
            log_info("task", "finish", "operation_status", f"status={final_status}, message={completion_details.get('message')}")
        log_info("task", "finish", "cleanup_complete", f"Cleanup complete for task: {task_laui}")
    except Exception as e:
        log_error("task", "finish", "cleanup_error", f"Error during finish/cleanup: {str(e)}")
        # Never re-raise from finish
"""}

bashblock = {"main.sh": """#!/bin/bash
set -e
pip install boto3>=1.28.0
pip install botocore>=1.31.0
echo "Dependencies installed successfully"
"""}

connection = {
    "region": "us-east-1",
}

payload = {
    "flow_name": "my-appflow-flow",           # required
    "checkpoint_time": "2024-01-15T00:00:00Z",  # required, ISO8601 UTC
    # "poll_interval_seconds": 15,             # optional
}

prompt = (
    "Create an operator that triggers an Amazon AppFlow flow and waits until an execution "
    "that started strictly after checkpoint_time (ISO 8601 UTC) completes. "
    "Skips any execution that started at or before the checkpoint. "
    "Required payload: flow_name, checkpoint_time. Optional: poll_interval_seconds (default 15). "
    "Auth: Case 1 explicit keys, Case 2 assume IAM role via STS, Case 3 default chain. "
    "Return flow_name, execution_id, execution_status, records_processed, bytes_processed. "
    "Catch all AWS errors and return them as status:failed - never raise."
)

install_docs = """# AWSAppFlowStartFlowAfter - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "appflow:StartFlow",
        "appflow:ListFlows",
        "appflow:DescribeFlowExecutionRecords"
      ],
      "Resource": "*"
    }

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| Explicit keys | Set aws_access_key_id and aws_secret_access_key in connection |
| Assume role   | Set assume_iam_role ARN in connection                         |
| Default chain | EC2 instance profile, ECS task role, env vars, ~/.aws         |
"""

guide_docs = """# AWSAppFlowStartFlowAfter - Operator Guide

## What it does

Triggers an Amazon AppFlow flow and polls every 15 seconds, skipping any execution that
started at or before the checkpoint_time. Only considers the run complete when an execution
that started strictly after the checkpoint reaches a terminal status (Successful, Error, or
Canceled). Equivalent to Airflow's AppflowRunAfterOperator.

Use this to ensure downstream tasks only process data from a new execution - not a stale
or pre-existing one.

---

## Auth

1. Explicit keys - aws_access_key_id + aws_secret_access_key (+ optional aws_session_token) in connection.
2. Assume IAM role - assume_iam_role ARN in connection, uses STS to assume role.
3. Default chain - EC2 instance profile, ECS task role, env vars, or ~/.aws config.

---

## Connection

    {
      "region": "us-east-1"
    }

Optional fields:

| Field                  | Description                          |
|------------------------|--------------------------------------|
| aws_access_key_id      | AWS access key ID                    |
| aws_secret_access_key  | AWS secret access key                |
| aws_session_token      | Session token for temporary creds    |
| assume_iam_role        | IAM role ARN to assume via STS       |

---

## Payload

    {
      "flow_name": "my-appflow-flow",
      "checkpoint_time": "2024-01-15T00:00:00Z"
    }

| Field                 | Required | Description                                                       |
|-----------------------|----------|-------------------------------------------------------------------|
| flow_name             | Yes      | Name of the AppFlow flow to trigger                               |
| checkpoint_time       | Yes      | ISO 8601 UTC - only accept executions that started after this     |
| poll_interval_seconds | No       | Polling interval in seconds (default: 15)                         |

---

## Output (on success)

    {
      "flow_name": "my-appflow-flow",
      "execution_id": "abc-123",
      "execution_status": "Successful",
      "records_processed": 1000,
      "bytes_processed": 204800
    }

---

## What this operator does NOT do

- Does not create or configure flows
- Does not filter records by time - only filters which execution to observe
"""

description = """
Triggers an Amazon AppFlow flow and waits for an execution that started strictly after the
specified checkpoint_time to complete. Skips any pre-existing execution at or before the
checkpoint. Equivalent to Airflow's AppflowRunAfterOperator. Required: flow_name,
checkpoint_time (ISO 8601 UTC). Optional: poll_interval_seconds (default 15). Auth: explicit
keys, assume IAM role, or default chain. Returns flow_name, execution_id, execution_status,
records_processed, and bytes_processed.
"""

publisher = "LeastActionLabs"

verified = False
status = "draft"

publisher_notes = (
    "Designed for Airflow-style DAG catchup - skips any execution at or before checkpoint_time and "
    "waits for one started strictly after. checkpoint_time format must be ISO8601 UTC string."
)

metadata = {
    "service": "AppFlow",
    "category": "Integration",
    "tags": ["appflow", "etl", "checkpoint", "aws"],
    "airflow_equivalent": "AppflowRunAfterOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
