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
AWS SageMaker Create Model Operator

Creates a SageMaker model definition from a container image and optional S3 model artifacts. Sync.
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
                 f"Initializing AWSSageMakerCreateModel for task: {task_laui}")
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
    Creates a SageMaker model definition.

    Payload fields:
        model_name                (str, required)  -- unique name for the SageMaker model
        execution_role_arn        (str, required)  -- IAM role ARN that SageMaker assumes
        image_uri                 (str, required)  -- Docker image URI (ECR or public)
        model_data_url            (str, optional)  -- S3 URI of model.tar.gz artifact
        environment               (dict, optional) -- environment variables for the container
        vpc_config                (dict, optional) -- {"SecurityGroupIds": [...], "Subnets": [...]}
        enable_network_isolation  (bool, optional) -- isolate container from internet (default: False)
        tags                      (list, optional) -- list of {"Key": ..., "Value": ...} dicts

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
        execution_role_arn = payload.get("execution_role_arn")
        image_uri = payload.get("image_uri")

        if not model_name:
            log_error("task", "run", "validation_error", "Required field missing: model_name")
            return {"status": "failed", "execution_type": "sync", "result": None,
                    "error": "Required field missing: model_name"}
        if not execution_role_arn:
            log_error("task", "run", "validation_error", "Required field missing: execution_role_arn")
            return {"status": "failed", "execution_type": "sync", "result": None,
                    "error": "Required field missing: execution_role_arn"}
        if not image_uri:
            log_error("task", "run", "validation_error", "Required field missing: image_uri")
            return {"status": "failed", "execution_type": "sync", "result": None,
                    "error": "Required field missing: image_uri"}

        primary_container = {"Image": image_uri}
        if payload.get("model_data_url"):
            primary_container["ModelDataUrl"] = payload["model_data_url"]
        if payload.get("environment"):
            primary_container["Environment"] = payload["environment"]

        kwargs = {
            "ModelName": model_name,
            "ExecutionRoleArn": execution_role_arn,
            "PrimaryContainer": primary_container,
        }
        if payload.get("vpc_config"):
            kwargs["VpcConfig"] = payload["vpc_config"]
        if payload.get("enable_network_isolation") is not None:
            kwargs["EnableNetworkIsolation"] = bool(payload["enable_network_isolation"])
        if payload.get("tags"):
            kwargs["Tags"] = payload["tags"]

        log_info("task", "run", "creating_model",
                 f"Creating SageMaker model: {model_name} image={image_uri}")
        response = client.create_model(**kwargs)
        model_arn = response.get("ModelArn", "")
        log_info("task", "run", "model_created", f"Model created. ARN: {model_arn}")

        return {"status": "success", "execution_type": "sync",
                "result": {"model_name": model_name, "model_arn": model_arn}}
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
             "CreateModel is synchronous — passing through result")
    return {"status": "success",
            "message": "SageMaker model created successfully",
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
                     f"Model {output.get('model_name')} created. ARN: {output.get('model_arn')}")
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
    "execution_role_arn": "arn:aws:iam::123456789012:role/SageMakerExecutionRole",
    "image_uri": "763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.0.0-cpu-py310",
    # "model_data_url": "s3://my-bucket/model/model.tar.gz",  # optional
    # "environment": {"SAGEMAKER_PROGRAM": "inference.py"},   # optional
    # "enable_network_isolation": False,                      # optional
    # "vpc_config": {"SecurityGroupIds": [...], "Subnets": [...]}  # optional
}

prompt = (
    "Creates a SageMaker model definition from a container image and optional S3 model artifacts. "
    "Provide model_name, execution_role_arn, image_uri. "
    "Optional: model_data_url (S3 URI to model.tar.gz), environment (dict), vpc_config, "
    "enable_network_isolation (bool, default False), tags. "
    "Synchronous — returns model_arn immediately."
)

install_docs = """## Dependencies
- boto3>=1.28.0
- botocore>=1.31.0

## IAM Permissions Required
- sagemaker:CreateModel
- iam:PassRole (on execution_role_arn)
- ecr:GetAuthorizationToken + ecr:BatchGetImage (if using a private ECR image)

## Prerequisites
- execution_role_arn must trust sagemaker.amazonaws.com as a service principal
- model_data_url (if provided) must point to a valid .tar.gz in S3
"""

guide_docs = """## What it does

Creates a SageMaker model definition by associating a container image with optional S3 model artifacts. The model object is a lightweight pointer used by endpoint configurations (for real-time inference) and batch transform jobs (for offline inference). It does not load or execute any code itself. This operator is synchronous and returns the model_arn immediately.

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

| Field                    | Required | Description                                                                      |
|--------------------------|----------|----------------------------------------------------------------------------------|
| model_name               | Yes      | Unique name for the SageMaker model                                              |
| execution_role_arn       | Yes      | IAM role ARN that SageMaker assumes to pull the image and read S3 artifacts      |
| image_uri                | Yes      | Docker image URI (ECR private or public registry)                                |
| model_data_url           | No       | S3 URI of a model.tar.gz artifact containing model weights and serving code      |
| environment              | No       | Dict of environment variables injected into the container at inference time      |
| vpc_config               | No       | {"SecurityGroupIds": [...], "Subnets": [...]} for VPC-only endpoints             |
| enable_network_isolation | No       | Bool — isolate the container from internet access (default: False)               |
| tags                     | No       | List of {"Key": ..., "Value": ...} dicts                                         |

---

## Output (on success)

    {
      "model_name": "my-inference-model",
      "model_arn": "arn:aws:sagemaker:us-east-1:123456789012:model/my-inference-model"
    }

| Field      | Description                                              |
|------------|----------------------------------------------------------|
| model_name | Name of the created SageMaker model                      |
| model_arn  | Full ARN of the model                                    |

---

## Scenarios and Edge Cases

Model already exists (ValidationException):
  If a model with the same name already exists, AWS raises ValidationException. Use a unique model_name or delete the existing model before recreating.

Image not accessible (execution_role_arn needs ECR pull permissions):
  If the execution_role_arn lacks ecr:GetAuthorizationToken and ecr:BatchGetImage permissions for the image, the endpoint or batch transform job will fail at container startup — not at model creation time. The model object is created successfully regardless.

model_data_url not a .tar.gz:
  AWS accepts any S3 URI for model_data_url without validating the file format. However, most built-in containers expect a .tar.gz with model artifacts at /opt/ml/model/ — an incorrect format will cause the container to fail to load the model at inference time.

---

## What this operator does NOT do

- Does not train the model — model artifacts must be pre-uploaded to S3.
- Does not upload model artifacts — the execution_role_arn must have S3 read access to model_data_url.
- Does not validate that the container image exists or is accessible at creation time.
- Does not deploy the model — use AWSSageMakerCreateEndpointConfig and AWSSageMakerCreateEndpoint after this.
"""

description = (
    "Creates a SageMaker model definition from a container image and optional S3 model artifacts. "
    "The model is a pointer used by endpoint configs and batch transform jobs. Synchronous."
)

publisher = "LeastActionLabs"

metadata = {
    "service": "SageMaker",
    "category": "ML",
    "tags": ["sagemaker", "model", "inference", "aws"],
    "airflow_equivalent": "SageMakerModelOperator",
}

version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False
status = "draft"

publisher_notes = """## Publisher Notes

The SageMaker model object is a lightweight pointer to a container image and optional model artifacts — it has no cost itself.
The execution_role_arn must trust the SageMaker service principal (sagemaker.amazonaws.com) and have permissions to pull ECR images and read S3 artifacts.
model_data_url must point to a .tar.gz file containing the model artifacts in the format expected by the container's serving stack (e.g. /opt/ml/model/ for built-in containers).
For built-in SageMaker algorithms, omit model_data_url only if the container bundles its own weights (uncommon). For custom containers with self-contained models (e.g. ONNX runtime), model_data_url can be omitted.
The model is used downstream by AWSSageMakerCreateEndpointConfig (real-time) and AWSSageMakerStartBatchTransform (batch inference).
Deleting a model with AWSSageMakerDeleteModel does not delete the underlying S3 artifacts or ECR image.
"""
