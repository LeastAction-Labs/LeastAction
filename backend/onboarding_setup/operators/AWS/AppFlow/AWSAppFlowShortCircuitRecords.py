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
        if not flow_name:
            msg = "Missing required payload field: flow_name"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        execution_id_filter = payload.get("execution_id")
        min_records = int(payload.get("min_records", 1))

        log_info("task", "run", "checking_records",
                 f"Checking AppFlow flow '{flow_name}' for records (min_records={min_records})")

        records_resp = client.describe_flow_execution_records(
            flowName=flow_name, maxResults=10
        )
        executions = records_resp.get("flowExecutions", [])

        if not executions:
            log_info("task", "run", "no_executions_found",
                     f"No execution records found for flow '{flow_name}', short-circuiting")
            return {
                "execution_type": "sync",
                "status": "success",
                "result": {
                    "flow_name": flow_name,
                    "execution_id": None,
                    "execution_status": "NoExecutions",
                    "records_processed": 0,
                    "bytes_processed": 0,
                    "short_circuited": True,
                    "message": "No execution records found for this flow"
                }
            }

        target_exec = None
        if execution_id_filter:
            for exec_rec in executions:
                if exec_rec.get("executionId") == execution_id_filter:
                    target_exec = exec_rec
                    break
            if not target_exec:
                log_info("task", "run", "execution_id_not_found",
                         f"Execution '{execution_id_filter}' not found, using latest")

        if not target_exec:
            target_exec = executions[0]

        exec_status = target_exec.get("executionStatus")
        exec_result = target_exec.get("executionResult", {})
        records_processed = exec_result.get("recordsProcessed", 0)
        bytes_processed = exec_result.get("bytesProcessed", 0)
        found_execution_id = target_exec.get("executionId")

        log_info("task", "run", "execution_found",
                 f"Flow '{flow_name}' execution {found_execution_id}: "
                 f"status={exec_status}, records={records_processed}")

        short_circuited = records_processed < min_records
        if short_circuited:
            log_info("task", "run", "short_circuiting",
                     f"records_processed={records_processed} < min_records={min_records}, short-circuiting")
        else:
            log_info("task", "run", "records_sufficient",
                     f"records_processed={records_processed} >= min_records={min_records}, continuing")

        return {
            "execution_type": "sync",
            "status": "success",
            "result": {
                "flow_name": flow_name,
                "execution_id": found_execution_id,
                "execution_status": exec_status,
                "records_processed": records_processed,
                "bytes_processed": bytes_processed,
                "short_circuited": short_circuited,
                "message": "Short-circuited: no records to process" if short_circuited
                           else "Records found, downstream tasks should proceed"
            }
        }

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
            "message": "AppFlow short-circuit check failed",
            "output": run_details.get("result", {})
        }
    log_info("task", "check_completion", "sync_complete",
             "AWSAppFlowShortCircuitRecords is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "AppFlow short-circuit check completed",
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
                     f"Flow {output.get('flow_name')} short_circuited={output.get('short_circuited')} "
                     f"records={output.get('records_processed')}")
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
    "flow_name": "my-appflow-flow",  # required
    # "execution_id": "abc-123",     # optional, default: latest
    # "min_records": 1,              # optional, default: 1
}

prompt = (
    "Create an operator that checks the most recent Amazon AppFlow execution for a flow and "
    "returns short_circuited=True if records_processed < min_records (default 1). "
    "Required payload: flow_name. Optional: execution_id (check specific run, default: latest), "
    "min_records (threshold, default: 1). "
    "Auth: Case 1 explicit keys, Case 2 assume IAM role via STS, Case 3 default chain. "
    "Return flow_name, execution_id, execution_status, records_processed, bytes_processed, "
    "short_circuited (bool), message. "
    "Catch all AWS errors and return them as status:failed - never raise."
)

install_docs = """# AWSAppFlowShortCircuitRecords - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
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

guide_docs = """# AWSAppFlowShortCircuitRecords - Operator Guide

## What it does

Inspects the most recent (or a specified) Amazon AppFlow execution and sets short_circuited=True
if the number of records processed is below the min_records threshold (default: 1). Use this
as a gate before downstream tasks that require data - if no records were processed, there is
nothing to transform or load. Equivalent to Airflow's AppflowRecordsShortCircuitOperator.

This operator does NOT trigger a flow - it only inspects an existing execution record.

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
      "flow_name": "my-appflow-flow"
    }

| Field        | Required | Description                                                            |
|--------------|----------|------------------------------------------------------------------------|
| flow_name    | Yes      | Name of the AppFlow flow to inspect                                    |
| execution_id | No       | Specific execution ID to check (default: most recent)                  |
| min_records  | No       | Minimum records threshold to NOT short-circuit (default: 1)            |

---

## Output (on success)

    {
      "flow_name": "my-appflow-flow",
      "execution_id": "abc-123",
      "execution_status": "Successful",
      "records_processed": 0,
      "bytes_processed": 0,
      "short_circuited": true,
      "message": "Short-circuited: no records to process"
    }

`short_circuited: false` means records were found and downstream tasks should proceed.

---

## What this operator does NOT do

- Does not trigger a flow - pair it after AWSAppFlowStartFlow or similar
- Does not cancel downstream tasks automatically - use the short_circuited flag in your pipeline logic
"""

description = """
Inspects the most recent Amazon AppFlow flow execution and returns short_circuited=True if
records_processed is below min_records (default: 1). Use as a data gate before downstream
transform or load tasks. Equivalent to Airflow's AppflowRecordsShortCircuitOperator.
Required: flow_name. Optional: execution_id (default: latest), min_records (default: 1).
Auth: explicit keys, assume IAM role, or default chain. Returns flow_name, execution_id,
execution_status, records_processed, bytes_processed, short_circuited, and message.
"""

publisher = "LeastActionLabs"

verified = False
status = "draft"

publisher_notes = (
    "Returns short_circuited=True if records_processed < min_records - this is a SUCCESS status but "
    "the caller must inspect short_circuited to decide whether to skip downstream tasks. "
    "No execution_id found = short_circuited=True silently. This mirrors Airflow's "
    "ShortCircuitOperator pattern."
)

metadata = {
    "service": "AppFlow",
    "category": "Integration",
    "tags": ["appflow", "etl", "short-circuit", "aws"],
    "airflow_equivalent": "AppflowShortCircuitOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
