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
AWS SageMaker Start Pipeline Execution Operator

Starts a SageMaker ML Pipeline execution and polls until Succeeded or Failed. Async.
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
                 f"Initializing AWSSageMakerStartPipelineExecution for task: {task_laui}")
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
    Starts a SageMaker Pipeline execution.

    Payload fields:
        pipeline_name                    (str, required)   -- name of an existing registered SageMaker pipeline
        pipeline_execution_display_name  (str, optional)   -- human-readable display name for this execution
        pipeline_parameters              (list, optional)  -- list of {"Name": str, "Value": str} parameter overrides
        pipeline_execution_description   (str, optional)   -- description for this execution
        client_request_token             (str, optional)   -- idempotency token for safe retries
        parallelism_configuration        (dict, optional)  -- {"MaxParallelExecutionSteps": int}

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
                return {"status": "failed", "execution_type": "async", "result": None,
                        "error": "Invalid payload format — expected flat JSON object"}
        if isinstance(payload, dict) and "data" in payload and isinstance(payload["data"], dict):
            payload = payload["data"]
            log_info("task", "run", "payload_unwrapped", "Unwrapped payload data envelope")

        pipeline_name = payload.get("pipeline_name")
        if not pipeline_name:
            log_error("task", "run", "validation_error", "Required field missing: pipeline_name")
            return {"status": "failed", "execution_type": "async", "result": None,
                    "error": "Required field missing: pipeline_name"}

        kwargs = {"PipelineName": pipeline_name}
        if payload.get("pipeline_execution_display_name"):
            kwargs["PipelineExecutionDisplayName"] = payload["pipeline_execution_display_name"]
        if payload.get("pipeline_parameters"):
            # Accept either list of {"Name":..,"Value":..} or dict — normalize to list
            params = payload["pipeline_parameters"]
            if isinstance(params, dict):
                params = [{"Name": k, "Value": str(v)} for k, v in params.items()]
            kwargs["PipelineParameters"] = params
        if payload.get("pipeline_execution_description"):
            kwargs["PipelineExecutionDescription"] = payload["pipeline_execution_description"]
        if payload.get("client_request_token"):
            kwargs["ClientRequestToken"] = payload["client_request_token"]
        if payload.get("parallelism_configuration"):
            kwargs["ParallelismConfiguration"] = payload["parallelism_configuration"]

        log_info("task", "run", "starting_pipeline_execution",
                 f"Starting pipeline execution: {pipeline_name}")
        response = client.start_pipeline_execution(**kwargs)
        pipeline_execution_arn = response.get("PipelineExecutionArn", "")
        log_info("task", "run", "pipeline_execution_started",
                 f"Pipeline execution started. ARN: {pipeline_execution_arn}")

        return {"status": "pending", "execution_type": "async",
                "result": {"pipeline_name": pipeline_name,
                           "pipeline_execution_arn": pipeline_execution_arn}}
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "client_error", f"AWS ClientError ({error_code}): {error_msg}")
        return {"status": "failed", "execution_type": "async", "result": None,
                "error": f"{error_code}: {error_msg}"}
    except Exception as e:
        log_error("task", "run", "unexpected_error", f"Unexpected error during run: {str(e)}")
        return {"status": "failed", "execution_type": "async", "result": None, "error": str(e)}


def check_completion(least_action_task_object, client, run_details):
    """Poll describe_pipeline_execution until Succeeded, Failed, or Stopped."""
    if run_details.get("status") == "failed":
        log_error("task", "check_completion", "run_phase_failed",
                  f"Run phase reported failure: {run_details.get('error')}")
        return {"status": "failed",
                "message": f"Run phase failed: {run_details.get('error')}",
                "output": None}
    try:
        pipeline_execution_arn = (run_details.get("result") or {}).get("pipeline_execution_arn")
        if not pipeline_execution_arn:
            return {"status": "failed", "message": "No pipeline_execution_arn in run_details", "output": None}

        response = client.describe_pipeline_execution(PipelineExecutionArn=pipeline_execution_arn)
        exec_status = response.get("PipelineExecutionStatus", "Unknown")
        failure_reason = response.get("FailureReason", "")
        log_info("task", "check_completion", "pipeline_status",
                 f"Pipeline execution {pipeline_execution_arn} status: {exec_status}")

        if exec_status == "Succeeded":
            return {"status": "success",
                    "message": "Pipeline execution succeeded",
                    "output": {"pipeline_execution_arn": pipeline_execution_arn,
                               "pipeline_name": (run_details.get("result") or {}).get("pipeline_name", ""),
                               "execution_status": exec_status}}
        elif exec_status in ("Failed", "Stopped"):
            return {"status": "failed",
                    "message": f"Pipeline execution {exec_status}: {failure_reason or 'No reason provided'}",
                    "output": {"pipeline_execution_arn": pipeline_execution_arn,
                               "failure_reason": failure_reason}}
        return {"status": "pending",
                "message": f"Pipeline execution is {exec_status}",
                "output": None}
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "check_completion", "client_error", f"AWS ClientError ({error_code}): {error_msg}")
        return {"status": "failed", "message": f"{error_code}: {error_msg}", "output": None}
    except Exception as e:
        log_error("task", "check_completion", "unexpected_error", f"Unexpected error: {str(e)}")
        return {"status": "failed", "message": str(e), "output": None}


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
                     f"Pipeline {output.get('pipeline_name')} execution succeeded. "
                     f"ARN: {output.get('pipeline_execution_arn')}")
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
    "pipeline_name": "my-ml-pipeline",
    # "pipeline_execution_display_name": "training-run-v2",    # optional
    # "pipeline_parameters": [{"Name": "LearningRate", "Value": "0.01"}],  # optional
    # "pipeline_execution_description": "Nightly training run",  # optional
    # "client_request_token": "unique-idempotency-token",       # optional
    # "parallelism_configuration": {"MaxParallelExecutionSteps": 3}  # optional
}

prompt = (
    "Starts a SageMaker ML Pipeline execution and polls until Succeeded, Failed, or Stopped. "
    "Provide pipeline_name. "
    "Optional: pipeline_execution_display_name, pipeline_parameters (list of {Name, Value} or dict), "
    "pipeline_execution_description, client_request_token, parallelism_configuration. "
    "Async — polls describe_pipeline_execution until terminal state."
)

install_docs = """## Dependencies
- boto3>=1.28.0
- botocore>=1.31.0

## IAM Permissions Required
- sagemaker:StartPipelineExecution
- sagemaker:DescribePipelineExecution

## Prerequisites
- The pipeline must exist and be registered in SageMaker before execution
  (create via SDK, SageMaker Studio, or IaC)
"""

guide_docs = """## What it does

Starts a SageMaker ML Pipeline execution by name, optionally overriding pipeline parameters for this run. The pipeline must already be registered in SageMaker. The operator polls describe_pipeline_execution until the execution reaches Succeeded, Failed, or Stopped. It supports idempotent retries via client_request_token and accepts pipeline parameters as either a list or a dict. This operator is async.

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

| Field                           | Required | Description                                                                     |
|---------------------------------|----------|---------------------------------------------------------------------------------|
| pipeline_name                   | Yes      | Name of an existing registered SageMaker pipeline                               |
| pipeline_execution_display_name | No       | Human-readable display name for this specific execution                         |
| pipeline_parameters             | No       | List of {"Name": str, "Value": str} or a dict — parameter overrides for this run |
| pipeline_execution_description  | No       | Description for this execution                                                  |
| client_request_token            | No       | Idempotency token — same token returns the same execution ARN on retry          |
| parallelism_configuration       | No       | {"MaxParallelExecutionSteps": int} to limit concurrent step execution           |

---

## Output (on success)

    {
      "pipeline_execution_arn": "arn:aws:sagemaker:us-east-1:123456789012:pipeline/my-pipeline/execution/abc123",
      "pipeline_name": "my-ml-pipeline",
      "execution_status": "Succeeded"
    }

| Field                  | Description                                                       |
|------------------------|-------------------------------------------------------------------|
| pipeline_execution_arn | Full ARN of the pipeline execution                                |
| pipeline_name          | Name of the pipeline that was executed                            |
| execution_status       | Final execution status — Succeeded on success                     |

---

## Scenarios and Edge Cases

Pipeline not found:
  If pipeline_name does not refer to a registered pipeline, AWS raises ResourceNotFoundException. The pipeline must be created and registered via the SDK or SageMaker Studio before it can be executed.

Parameter names must match exactly:
  pipeline_parameters override the default values defined in the pipeline definition. Parameter names are case-sensitive and must match exactly — unrecognized parameter names raise ValidationException.

Stopped or Failed states:
  If the pipeline execution enters Stopped or Failed state, the operator returns failure with the FailureReason. Stopped executions cannot be resumed — start a new execution if needed.

---

## What this operator does NOT do

- Does not create or register the pipeline — the pipeline must exist before this operator can execute it.
- Does not resume a stopped execution — start a new execution with AWSSageMakerStartPipelineExecution.
- Does not terminate mid-flight training or processing jobs if the execution is stopped mid-run — use AWSSageMakerStopPipelineExecution for that.
"""

description = (
    "Starts a SageMaker ML Pipeline execution and polls asynchronously until Succeeded, Failed, or Stopped. "
    "Supports parameter overrides and idempotency tokens."
)

publisher = "LeastActionLabs"

metadata = {
    "service": "SageMaker",
    "category": "ML",
    "tags": ["sagemaker", "pipeline", "orchestration", "mlops", "aws"],
    "airflow_equivalent": "SageMakerStartPipelineExecutionOperator",
}

version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False
status = "draft"

publisher_notes = """## Publisher Notes

The pipeline must be registered in SageMaker before this operator can execute it — registration is done via the SDK (pipeline.upsert()) or SageMaker Studio.
pipeline_parameters override default parameter values defined in the pipeline — parameter names must match exactly (case-sensitive).
This operator accepts pipeline_parameters as either a list [{"Name": "k", "Value": "v"}] or a dict {"k": "v"} — both are normalized to the list format required by the API.
client_request_token enables idempotent retries — if the same token is used in two calls, the second returns the ARN of the first execution without creating a new one.
Pipelines can contain training, processing, condition, and lambda steps — each step that spawns compute incurs cost independently.
Use parallelism_configuration to limit concurrent step execution and control cost vs speed tradeoffs.
Stopped executions cannot be resumed — start a new execution if needed.
"""
