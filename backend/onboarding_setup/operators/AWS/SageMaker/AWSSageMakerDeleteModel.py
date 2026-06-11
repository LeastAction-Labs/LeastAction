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
AWS SageMaker Delete Model Operator

Deletes a SageMaker model definition. Does not delete S3 artifacts or ECR images. Sync.
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
                 f"Initializing AWSSageMakerDeleteModel for task: {task_laui}")
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
    Deletes a SageMaker model definition.

    Payload fields:
        model_name  (str, required)  -- name of the SageMaker model to delete

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

        model_name = payload.get("model_name")
        if not model_name:
            log_error("task", "run", "validation_error", "Required field missing: model_name")
            return {"status": "failed", "execution_type": "sync", "result": None,
                    "error": "Required field missing: model_name"}

        log_info("task", "run", "deleting_model", f"Deleting SageMaker model: {model_name}")
        client.delete_model(ModelName=model_name)
        log_info("task", "run", "model_deleted", f"Model deleted successfully: {model_name}")

        return {"status": "success", "execution_type": "sync",
                "result": {"model_name": model_name,
                           "message": f"Model {model_name} deleted successfully"}}
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        # Treat "model not found" as success for idempotency
        if error_code == "ValidationException" and "Could not find model" in error_msg:
            model_name = (payload or {}).get("model_name", "unknown")
            log_info("task", "run", "model_not_found",
                     f"Model {model_name} not found — already deleted (idempotent success)")
            return {"status": "success", "execution_type": "sync",
                    "result": {"model_name": model_name,
                               "message": "Model not found — already deleted"}}
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
             "DeleteModel is synchronous — passing through result")
    return {"status": "success",
            "message": "SageMaker model deleted successfully",
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
                     f"Model {output.get('model_name')} deletion complete: {output.get('message')}")
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
    "model_name": "my-inference-model",
}

prompt = (
    "Deletes a SageMaker model definition. Provide model_name. "
    "Does not delete the underlying S3 model artifacts or ECR container image. "
    "Idempotent — returns success if the model is already deleted. "
    "Synchronous — completes immediately."
)

install_docs = """## Dependencies
- boto3>=1.28.0
- botocore>=1.31.0

## IAM Permissions Required
- sagemaker:DeleteModel

## Prerequisites
- Models referenced by active endpoints cannot be deleted — delete the endpoint first
- Models referenced by in-use endpoint configs may fail — delete the endpoint config first
"""

guide_docs = """## What it does

Deletes a SageMaker model definition by name. The model object is a lightweight pointer to a container image and optional S3 artifacts — deleting it removes only the SageMaker metadata record, not the underlying ECR image or S3 model files. The operator is idempotent: if the model does not exist it returns success rather than raising an error. This operator is synchronous.

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

| Field      | Required | Description                                   |
|------------|----------|-----------------------------------------------|
| model_name | Yes      | Name of the SageMaker model to delete         |

---

## Output (on success)

    {
      "model_name": "my-inference-model",
      "message": "Model my-inference-model deleted successfully"
    }

| Field      | Description                                              |
|------------|----------------------------------------------------------|
| model_name | Name of the deleted model                                |
| message    | Confirmation message or note if already deleted          |

---

## Scenarios and Edge Cases

Model not found (returns success — idempotent):
  If the model does not exist, the operator treats it as a success and returns a "Model not found — already deleted" message. This makes it safe to use in cleanup pipelines without pre-checking existence.

Model referenced by active endpoint config (cannot delete):
  If the model is referenced by an endpoint configuration that is actively used by an InService endpoint, AWS may raise an error. Delete the endpoint and endpoint configuration first before deleting the model.

---

## What this operator does NOT do

- Does not delete model artifacts from S3 — the model.tar.gz and any training outputs remain in S3.
- Does not delete the container image from ECR.
- Does not delete associated endpoint configurations or endpoints — those must be deleted separately before or after deleting the model.
"""

description = (
    "Deletes a SageMaker model definition. Does not delete underlying S3 artifacts or ECR images. "
    "Idempotent and synchronous."
)

publisher = "LeastActionLabs"

metadata = {
    "service": "SageMaker",
    "category": "ML",
    "tags": ["sagemaker", "model", "delete", "aws"],
    "airflow_equivalent": "SageMakerDeleteModelOperator",
}

version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False
status = "draft"

publisher_notes = """## Publisher Notes

Deleting a model only removes the SageMaker model object — it does not delete the container image in ECR or model artifacts in S3.
Models referenced by active endpoints cannot be deleted — delete the endpoint first (there is no DeleteEndpoint operator yet; use the AWS console or add one).
The operator is idempotent: if the model does not exist, it returns success rather than raising an error, making it safe to use in cleanup pipelines.
Model deletion is immediate and irreversible — the model name can be reused after deletion.
"""
