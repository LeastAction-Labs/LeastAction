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
AWS SageMaker Create Experiment Operator

Creates a SageMaker Experiment for organizing and comparing ML training runs. Sync.
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
                 f"Initializing AWSSageMakerCreateExperiment for task: {task_laui}")
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
    Creates a SageMaker Experiment.

    Payload fields:
        experiment_name  (str, required)  -- unique name for the experiment (account + region scoped)
        description      (str, optional)  -- human-readable description
        tags             (list, optional) -- list of {"Key": ..., "Value": ...} dicts

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

        experiment_name = payload.get("experiment_name")
        if not experiment_name:
            log_error("task", "run", "validation_error", "Required field missing: experiment_name")
            return {"status": "failed", "execution_type": "sync", "result": None,
                    "error": "Required field missing: experiment_name"}

        kwargs = {"ExperimentName": experiment_name}
        if payload.get("description"):
            kwargs["Description"] = payload["description"]
        if payload.get("tags"):
            kwargs["Tags"] = payload["tags"]

        log_info("task", "run", "creating_experiment", f"Creating SageMaker experiment: {experiment_name}")
        response = client.create_experiment(**kwargs)
        experiment_arn = response.get("ExperimentArn", "")
        log_info("task", "run", "experiment_created", f"Experiment created. ARN: {experiment_arn}")

        return {"status": "success", "execution_type": "sync",
                "result": {"experiment_name": experiment_name, "experiment_arn": experiment_arn}}
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
             "CreateExperiment is synchronous — passing through result")
    return {"status": "success",
            "message": "SageMaker experiment created successfully",
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
                     f"Experiment {output.get('experiment_name')} created. ARN: {output.get('experiment_arn')}")
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
    "experiment_name": "my-ml-experiment",
    # "description": "Comparing model architectures for image classification",  # optional
    # "tags": [{"Key": "team", "Value": "ml-platform"}]                        # optional
}

prompt = (
    "Creates a SageMaker Experiment to organize and compare ML training runs and trials. "
    "Provide experiment_name. Optional: description, tags. "
    "Synchronous — returns experiment_arn immediately. "
    "experiment_name must be unique within the account and region."
)

install_docs = """## Dependencies
- boto3>=1.28.0
- botocore>=1.31.0

## IAM Permissions Required
- sagemaker:CreateExperiment
"""

guide_docs = """## What it does

Creates a SageMaker Experiment, which is a top-level container for organizing and comparing ML training runs (Trials). Experiments provide a structured way to track different model variants, hyperparameter configurations, and dataset versions across multiple training jobs. This operator is synchronous and returns the experiment_arn immediately.

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

| Field           | Required | Description                                                                        |
|-----------------|----------|------------------------------------------------------------------------------------|
| experiment_name | Yes      | Unique experiment name scoped to the account and region (max 120 characters)       |
| description     | No       | Human-readable description of the experiment's purpose                             |
| tags            | No       | List of {"Key": ..., "Value": ...} dicts                                           |

---

## Output (on success)

    {
      "experiment_name": "my-ml-experiment",
      "experiment_arn": "arn:aws:sagemaker:us-east-1:123456789012:experiment/my-ml-experiment"
    }

| Field           | Description                                              |
|-----------------|----------------------------------------------------------|
| experiment_name | Name of the created experiment                           |
| experiment_arn  | Full ARN of the experiment                               |

---

## Scenarios and Edge Cases

Experiment already exists (ResourceInUse):
  If an experiment with the same name already exists in the account and region, AWS raises ResourceInUse. Use the existing experiment's name to associate new trials rather than creating a duplicate.

Name length limit (max 120 characters):
  experiment_name must not exceed 120 characters. AWS raises a ValidationException for names that are too long.

---

## What this operator does NOT do

- Does not create Trials (individual training runs) — Trials are created separately and associated with the experiment via ExperimentConfig in training/processing job calls.
- Does not associate any compute jobs to the experiment automatically — jobs must specify ExperimentConfig in their own API calls.
- Does not delete the experiment or its associated Trials.
"""

description = (
    "Creates a SageMaker Experiment to organize, track, and compare ML training runs and trials. "
    "Synchronous — returns experiment ARN immediately. Free to create."
)

publisher = "LeastActionLabs"

metadata = {
    "service": "SageMaker",
    "category": "ML",
    "tags": ["sagemaker", "experiment", "tracking", "mlops", "aws"],
    "airflow_equivalent": "SageMakerCreateExperimentOperator",
}

version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False
status = "draft"

publisher_notes = """## Publisher Notes

Experiments are containers for Trials (individual training runs) in the SageMaker Experiments framework.
Once an experiment exists, associate training jobs, processing jobs, or tuning jobs with it by passing ExperimentConfig in those API calls.
Experiments are free — only the underlying compute jobs (training, processing) incur cost.
experiment_name must be unique within the account and region — the API raises ResourceInUse if the name already exists.
Deleting an experiment deletes all associated trials and trial components — use with care in production.
SageMaker Studio provides a visual interface for comparing trials across experiments.
"""
