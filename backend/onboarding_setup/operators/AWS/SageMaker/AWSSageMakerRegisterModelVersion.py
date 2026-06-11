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
AWS SageMaker Register Model Version Operator

Registers a model version in the SageMaker Model Registry for versioning and approval workflows. Sync.
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
                 f"Initializing AWSSageMakerRegisterModelVersion for task: {task_laui}")
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
    Registers a model version in the SageMaker Model Registry.

    Payload fields:
        model_package_group_name       (str, required)   -- name of the model package group
        image_uri                      (str, required)   -- Docker image URI for inference
        model_data_url                 (str, optional)   -- S3 URI of model.tar.gz artifact
        approval_status                (str, optional)   -- "PendingManualApproval" or "Approved" (default: PendingManualApproval)
        description                    (str, optional)   -- description for this model version
        supported_content_types        (list, optional)  -- list of content types (default: ["text/csv"])
        supported_response_mime_types  (list, optional)  -- list of response MIME types (default: ["text/csv"])
        tags                           (list, optional)  -- list of {"Key": ..., "Value": ...} dicts

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

        model_package_group_name = payload.get("model_package_group_name")
        image_uri = payload.get("image_uri")

        if not model_package_group_name:
            log_error("task", "run", "validation_error", "Required field missing: model_package_group_name")
            return {"status": "failed", "execution_type": "sync", "result": None,
                    "error": "Required field missing: model_package_group_name"}
        if not image_uri:
            log_error("task", "run", "validation_error", "Required field missing: image_uri")
            return {"status": "failed", "execution_type": "sync", "result": None,
                    "error": "Required field missing: image_uri"}

        container_spec = {"Image": image_uri}
        if payload.get("model_data_url"):
            container_spec["ModelDataUrl"] = payload["model_data_url"]

        inference_specification = {
            "Containers": [container_spec],
            "SupportedContentTypes": payload.get("supported_content_types", ["text/csv"]),
            "SupportedResponseMIMETypes": payload.get("supported_response_mime_types", ["text/csv"]),
        }

        kwargs = {
            "ModelPackageGroupName": model_package_group_name,
            "InferenceSpecification": inference_specification,
            "ModelApprovalStatus": payload.get("approval_status", "PendingManualApproval"),
        }
        if payload.get("description"):
            kwargs["ModelPackageDescription"] = payload["description"]
        if payload.get("tags"):
            kwargs["Tags"] = payload["tags"]

        log_info("task", "run", "registering_model_version",
                 f"Registering model version in group: {model_package_group_name} "
                 f"approval_status={kwargs['ModelApprovalStatus']}")
        response = client.create_model_package(**kwargs)
        model_package_arn = response.get("ModelPackageArn", "")
        log_info("task", "run", "model_version_registered",
                 f"Model version registered. ARN: {model_package_arn}")

        return {"status": "success", "execution_type": "sync",
                "result": {"model_package_group_name": model_package_group_name,
                           "model_package_arn": model_package_arn,
                           "approval_status": kwargs["ModelApprovalStatus"]}}
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
             "RegisterModelVersion is synchronous — passing through result")
    return {"status": "success",
            "message": "Model version registered successfully in the Model Registry",
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
                     f"Model version registered in group {output.get('model_package_group_name')}. "
                     f"ARN: {output.get('model_package_arn')} "
                     f"Status: {output.get('approval_status')}")
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
    "model_package_group_name": "my-model-group",
    "image_uri": "763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.0.0-cpu-py310",
    # "model_data_url": "s3://my-bucket/model/model.tar.gz",      # optional
    # "approval_status": "PendingManualApproval",                  # optional, default PendingManualApproval
    # "description": "Model v2.1 trained on 2024 data",           # optional
    # "supported_content_types": ["text/csv"],                     # optional
    # "supported_response_mime_types": ["text/csv"],               # optional
    # "tags": [{"Key": "stage", "Value": "staging"}]              # optional
}

prompt = (
    "Registers a model version in the SageMaker Model Registry. "
    "Provide model_package_group_name and image_uri. "
    "Optional: model_data_url, approval_status (default PendingManualApproval), description, "
    "supported_content_types (default ['text/csv']), supported_response_mime_types (default ['text/csv']), tags. "
    "Synchronous — returns model_package_arn immediately."
)

install_docs = """## Dependencies
- boto3>=1.28.0
- botocore>=1.31.0

## IAM Permissions Required
- sagemaker:CreateModelPackage

## Prerequisites
- The model package group must exist before registering versions
  (create it via AWS console, SDK, or a separate operator)
"""

guide_docs = """## What it does

Registers a new versioned model entry in the SageMaker Model Registry within an existing model package group. Each registration creates an immutable version record containing the container image, optional S3 model artifacts, supported content types, and an approval status. The approval workflow enables human-in-the-loop gating before a model version is deployed to production. This operator is synchronous and returns the model_package_arn immediately.

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

| Field                         | Required | Description                                                                     |
|-------------------------------|----------|---------------------------------------------------------------------------------|
| model_package_group_name      | Yes      | Name of the existing model package group to register the version into           |
| image_uri                     | Yes      | Docker image URI for inference (ECR or public)                                  |
| model_data_url                | No       | S3 URI of the model.tar.gz artifact containing model weights                    |
| approval_status               | No       | "PendingManualApproval" or "Approved" (default: PendingManualApproval)          |
| description                   | No       | Human-readable description for this specific model version                      |
| supported_content_types       | No       | List of accepted input content types (default: ["text/csv"])                    |
| supported_response_mime_types | No       | List of response MIME types (default: ["text/csv"])                             |
| tags                          | No       | List of {"Key": ..., "Value": ...} dicts                                        |

---

## Output (on success)

    {
      "model_package_group_name": "my-model-group",
      "model_package_arn": "arn:aws:sagemaker:us-east-1:123456789012:model-package/my-model-group/1",
      "approval_status": "PendingManualApproval"
    }

| Field                    | Description                                                      |
|--------------------------|------------------------------------------------------------------|
| model_package_group_name | Name of the model package group                                  |
| model_package_arn        | Full ARN of the registered model version (includes version number)|
| approval_status          | Approval status of the registered version                        |

---

## Scenarios and Edge Cases

Group not found (ValidationException):
  If model_package_group_name does not exist, AWS raises ValidationException. Create the model package group first via the AWS console, SDK (create_model_package_group), or a separate operator.

approval_status=Approved for automated pipelines:
  For fully automated CI/CD pipelines where human review is not required, set approval_status to "Approved" — this allows the model version to be deployed without a manual approval step.

---

## What this operator does NOT do

- Does not create the model package group — the group must exist before registering versions.
- Does not deploy the model version to an endpoint — use AWSSageMakerCreateEndpointConfig and AWSSageMakerCreateEndpoint after approval.
- Does not validate the container image or model artifacts at registration time.
- Does not update the approval status after registration — use update_model_package separately to approve or reject.
"""

description = (
    "Registers a new model version in the SageMaker Model Registry for versioning, "
    "approval workflows, and CI/CD integration. Synchronous — returns model_package_arn immediately."
)

publisher = "LeastActionLabs"

metadata = {
    "service": "SageMaker",
    "category": "ML",
    "tags": ["sagemaker", "model-registry", "versioning", "mlops", "aws"],
    "airflow_equivalent": "SageMakerRegisterModelVersionOperator",
}

version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False
status = "draft"

publisher_notes = """## Publisher Notes

The Model Registry enables versioning, approval workflows, and CI/CD integration for ML models.
The model_package_group must exist before registering versions — create it via the AWS console or SDK (create_model_package_group).
approval_status defaults to PendingManualApproval — suitable for human-in-the-loop review pipelines.
Use "Approved" for fully automated pipelines where human approval is not required.
supported_content_types and supported_response_mime_types are metadata only and do not enforce runtime behavior.
The model_package_arn includes the version number as the last path component (e.g. .../my-model-group/1, /2, etc.).
Use update_model_package with ModelApprovalStatus to approve/reject a version after registration.
"""
