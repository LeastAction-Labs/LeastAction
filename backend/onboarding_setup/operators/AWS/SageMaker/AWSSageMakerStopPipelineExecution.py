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

codeblock = {"main.py": '''"""
AWS SageMaker Stop Pipeline Execution Operator

Sends a stop signal to a running SageMaker Pipeline execution. Sync (fire-and-forget).
Auth priority: explicit keys → assume IAM role → default credential chain.
"""

import json
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from src.common.logger.logger import log_error, log_info


def _build_sagemaker_client(connection: dict):
    region = connection.get("region", "us-east-1")
    access_key = connection.get("aws_access_key_id")
    secret_key = connection.get("aws_secret_access_key")
    session_token = connection.get("aws_session_token")
    assume_role_arn = connection.get("assume_iam_role")

    # Case 1: Explicit credentials
    if access_key and secret_key:
        log_info("task", "initialize", "auth_keys", f"Using explicit access key ending ...{access_key[-4:]}")
        session = boto3.Session(aws_access_key_id=access_key, aws_secret_access_key=secret_key,
                                aws_session_token=session_token, region_name=region)
        return session.client("sagemaker")

    # Case 2: Assume IAM role via STS
    if assume_role_arn:
        log_info("task", "initialize", "auth_assume_role", f"Assuming IAM role: {assume_role_arn}")
        sts = boto3.client("sts", region_name=region)
        assumed = sts.assume_role(RoleArn=assume_role_arn, RoleSessionName="leastaction_session")
        creds = assumed["Credentials"]
        session = boto3.Session(aws_access_key_id=creds["AccessKeyId"],
                                aws_secret_access_key=creds["SecretAccessKey"],
                                aws_session_token=creds["SessionToken"], region_name=region)
        return session.client("sagemaker")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info("task", "initialize", "auth_default",
             "Using default AWS credential chain (instance profile / ECS task role / env / config)")
    return boto3.Session(region_name=region).client("sagemaker")


def initialize(least_action_task_object):
    """Build and verify the SageMaker boto3 client. Returns: boto3 sagemaker client"""
    try:
        connection = least_action_task_object.get("connection", {})
        if isinstance(connection, str):
            connection = json.loads(connection)
        task_laui = least_action_task_object.get("laui")
        log_info("task", "initialize", "start",
                 f"Initializing AWSSageMakerStopPipelineExecution for task: {task_laui}")
        client = _build_sagemaker_client(connection)
        region = connection.get("region", "us-east-1")
        log_info("task", "initialize", "verify_connection", f"Verifying SageMaker connectivity in region: {region}")
        try:
            client.list_domains(MaxResults=1)
        except ClientError:
            pass
        log_info("task", "initialize", "connection_established", f"SageMaker client ready for region: {region}")
        return client
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "initialize", "client_error", f"AWS ClientError ({error_code}): {error_msg}")
        raise
    except BotoCoreError as e:
        log_error("task", "initialize", "botocore_error", f"BotoCoreError during initialization: {str(e)}")
        raise
    except Exception as e:
        log_error("task", "initialize", "unexpected_error", f"Unexpected error during initialization: {str(e)}")
        raise


def run(least_action_task_object, client):
    """
    Sends a stop signal to a running SageMaker Pipeline execution.

    Payload fields:
        pipeline_execution_arn  (str, required)  -- ARN of the pipeline execution to stop
        client_request_token    (str, optional)  -- idempotency token

    Returns: dict with status, execution_type, result
    """
    try:
        task_laui = least_action_task_object.get("laui")
        payload = least_action_task_object.get("payload", {})
        log_info("task", "run", "extracting_payload", f"Extracting configuration for task: {task_laui}")
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                log_error("task", "run", "payload_parse_error", "Failed to parse payload as JSON")
                return {"status": "failed", "execution_type": "sync", "result": None,
                        "error": "Invalid payload format — expected flat JSON object"}
        if isinstance(payload, dict) and "data" in payload and isinstance(payload["data"], dict):
            payload = payload["data"]
            log_info("task", "run", "payload_unwrapped", "Unwrapped payload data envelope")

        pipeline_execution_arn = payload.get("pipeline_execution_arn")
        if not pipeline_execution_arn:
            log_error("task", "run", "validation_error", "Required field missing: pipeline_execution_arn")
            return {"status": "failed", "execution_type": "sync", "result": None,
                    "error": "Required field missing: pipeline_execution_arn"}

        kwargs = {"PipelineExecutionArn": pipeline_execution_arn}
        if payload.get("client_request_token"):
            kwargs["ClientRequestToken"] = payload["client_request_token"]

        log_info("task", "run", "stopping_pipeline_execution",
                 f"Sending stop signal to pipeline execution: {pipeline_execution_arn}")
        response = client.stop_pipeline_execution(**kwargs)
        returned_arn = response.get("PipelineExecutionArn", pipeline_execution_arn)
        log_info("task", "run", "stop_signal_sent",
                 f"Stop signal sent to pipeline execution: {returned_arn}")

        return {"status": "success", "execution_type": "sync",
                "result": {"pipeline_execution_arn": returned_arn,
                           "status": "Stopping",
                           "message": "Stop signal sent — execution will halt after completing in-flight steps"}}
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "client_error", f"AWS ClientError ({error_code}): {error_msg}")
        return {"status": "failed", "execution_type": "sync", "result": None,
                "error": f"{error_code}: {error_msg}"}
    except Exception as e:
        log_error("task", "run", "unexpected_error", f"Unexpected error during run: {str(e)}")
        return {"status": "failed", "execution_type": "sync", "result": None, "error": str(e)}


def check_completion(least_action_task_object, client, run_details):
    """Sync operation — pass through run result as output."""
    if run_details.get("status") == "failed":
        log_error("task", "check_completion", "run_phase_failed",
                  f"Run phase reported failure: {run_details.get('error')}")
        return {"status": "failed",
                "message": f"Run phase failed: {run_details.get('error')}",
                "output": None}
    log_info("task", "check_completion", "sync_passthrough",
             "StopPipelineExecution is synchronous (fire-and-forget) — passing through result")
    return {"status": "success",
            "message": "Stop signal sent to pipeline execution",
            "output": run_details.get("result")}


def finish(least_action_task_object, client, completion_details, run_details):
    """Log final outcome and release held resources. Returns: None"""
    try:
        task_laui = least_action_task_object.get("laui")
        log_info("task", "finish", "starting_cleanup", f"Starting cleanup for task: {task_laui}")
        final_status = completion_details.get("status", "unknown")
        log_info("task", "finish", "final_status", f"Task ended with status: {final_status}")
        if client:
            try:
                client.close()
                log_info("task", "finish", "client_closed", "SageMaker boto3 client closed successfully")
            except Exception as close_error:
                log_error("task", "finish", "client_close_error", f"Error closing client: {str(close_error)}")
        if final_status == "success":
            output = completion_details.get("output") or {}
            log_info("task", "finish", "operation_summary",
                     f"Stop signal sent to pipeline execution: {output.get('pipeline_execution_arn')}. "
                     f"In-flight steps will complete before halting.")
        elif final_status == "failed":
            log_error("task", "finish", "operation_failed",
                      f"Operation failed: {completion_details.get('message')}")
        else:
            log_info("task", "finish", "operation_status",
                     f"status={final_status}, message={completion_details.get('message')}")
        log_info("task", "finish", "cleanup_complete", f"Cleanup complete for task: {task_laui}")
    except Exception as e:
        log_error("task", "finish", "cleanup_error", f"Error during finish/cleanup: {str(e)}")
        # Never re-raise from finish
'''}

bashblock = {"main.sh": """#!/bin/bash\nset -e\npip install boto3>=1.28.0\npip install botocore>=1.31.0\necho \"Dependencies installed successfully\"\n"""}

connection = {"region": "us-east-1"}

payload = {
    "pipeline_execution_arn": "arn:aws:sagemaker:us-east-1:123456789012:pipeline/my-pipeline/execution/abc123xyz456",
    # "client_request_token": "unique-stop-token"  # optional, for idempotent retries
}

prompt = (
    "Sends a stop signal to a running SageMaker Pipeline execution. "
    "Provide pipeline_execution_arn. Optional: client_request_token. "
    "Synchronous — fire-and-forget stop signal. Currently running steps complete before the execution halts. "
    "Does not wait for the execution to reach Stopped state."
)

install_docs = """## Dependencies
- boto3>=1.28.0
- botocore>=1.31.0

## IAM Permissions Required
- sagemaker:StopPipelineExecution

## Prerequisites
- The pipeline execution must be in Executing state — cannot stop a Succeeded/Failed/Stopped execution
"""

guide_docs = """## What it does

Sends a stop signal to a running SageMaker Pipeline execution. The stop is a fire-and-forget request — the operator returns immediately after the API call succeeds without waiting for the execution to fully halt. Currently executing pipeline steps are allowed to complete before the execution transitions to Stopped state. This operator is synchronous.

---

## Auth

Three methods are supported, evaluated in this priority order:

1. **Access keys** — if `aws_access_key_id` + `aws_secret_access_key` are present in the connection, they are used immediately. Suitable for IAM users, CI/CD pipelines, or any environment outside AWS.
2. **Assume IAM role** — if `assume_iam_role` (role ARN) is present and access keys are absent, the operator assumes the specified role via STS. Use this for cross-account access or when you need to scope down to a least-privilege role.
3. **Default credential chain** — boto3 falls back to the standard AWS credential chain: EC2 instance profile, ECS task role, Lambda execution role, environment variables, or `~/.aws/credentials`.

---

## Connection

**Scenario 1 — Access keys** (IAM user, CI/CD, running outside AWS):

    {
      "region": "us-east-1",
      "aws_access_key_id": "AKIA...",          // IAM user access key
      "aws_secret_access_key": "...",           // IAM user secret key
      "aws_session_token": "..."                // only needed for temporary/STS-issued credentials
    }

**Scenario 2 — Assume IAM role** (cross-account or least-privilege scoping):

    {
      "region": "us-east-1",
      "assume_iam_role": "arn:aws:iam::123456789012:role/MyRole"
    }

**Scenario 3 — Default credential chain** (EC2 instance profile, ECS task role, Lambda role):

    {"region": "us-east-1"}

| Field                 | Required   | Description                                                                          |
|-----------------------|------------|--------------------------------------------------------------------------------------|
| region                | Yes        | AWS region where the SageMaker resources exist                                       |
| aws_access_key_id     | Scenario 1 | IAM user access key                                                                  |
| aws_secret_access_key | Scenario 1 | IAM user secret key — required alongside aws_access_key_id                          |
| aws_session_token     | No         | Temporary session token — only needed with short-lived STS credentials               |
| assume_iam_role       | Scenario 2 | Role ARN to assume via STS                                                           |

---

## Payload

| Field                  | Required | Description                                                            |
|------------------------|----------|------------------------------------------------------------------------|
| pipeline_execution_arn | Yes      | Full ARN of the pipeline execution to stop                             |
| client_request_token   | No       | Idempotency token for safe retries — same token is a no-op             |

---

## Output (on success)

    {
      "pipeline_execution_arn": "arn:aws:sagemaker:us-east-1:123456789012:pipeline/my-pipeline/execution/abc123",
      "status": "Stopping",
      "message": "Stop signal sent — execution will halt after completing in-flight steps"
    }

| Field                  | Description                                                       |
|------------------------|-------------------------------------------------------------------|
| pipeline_execution_arn | ARN of the pipeline execution the stop signal was sent to         |
| status                 | Status immediately after the stop request — always "Stopping"     |
| message                | Human-readable confirmation of the stop signal                    |

---

## Scenarios and Edge Cases

Execution already stopped (idempotent):
  If the execution is already in Stopped, Failed, or Succeeded state, AWS raises ValidationException. This operator does not handle idempotency for already-terminal executions — check status before calling stop if needed.

Currently running steps complete before pipeline halts:
  The stop signal causes the pipeline to stop queueing new steps. Steps that are already executing (e.g. a training job mid-run) are allowed to finish before the pipeline transitions to Stopped. This can take minutes to hours depending on the step type.

---

## What this operator does NOT do

- Does not immediately terminate mid-flight training or processing jobs spawned by pipeline steps — those jobs run to completion or their own stopping condition.
- Does not resume the stopped execution — stopped executions cannot be resumed. Use AWSSageMakerStartPipelineExecution to start a new execution.
- Does not poll for the Stopped state — this is a fire-and-forget operator. Use describe_pipeline_execution to check the final state if needed.
"""

description = (
    "Sends a stop signal to a running SageMaker Pipeline execution. "
    "Synchronous fire-and-forget — returns immediately after sending the stop request."
)

publisher = "LeastActionLabs"

metadata = {
    "service": "SageMaker",
    "category": "ML",
    "tags": ["sagemaker", "pipeline", "stop", "orchestration", "aws"],
    "airflow_equivalent": "SageMakerStopPipelineExecutionOperator",
}

version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False
status = "draft"

publisher_notes = """## Publisher Notes

stop_pipeline_execution sends a stop signal — it does NOT immediately terminate the execution.
Currently executing pipeline steps are allowed to complete before the execution transitions to Stopped.
This operator does NOT terminate mid-flight training or processing jobs spawned by the pipeline steps — those jobs continue until their own stopping condition is met.
The pipeline execution must be in Executing state — calling stop on an already-Stopped, Failed, or Succeeded execution raises a ValidationException.
Stopped executions cannot be resumed — use AWSSageMakerStartPipelineExecution to start a new execution if needed.
Use AWSSageMakerStartPipelineExecution's check_completion (calling describe_pipeline_execution) to poll for the Stopped state if confirmation is needed.
client_request_token enables idempotent stop requests — safe to retry without double-stopping.
"""
