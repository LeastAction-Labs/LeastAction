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
AWS SageMaker Create Endpoint Config Operator

Creates a SageMaker endpoint configuration defining model, instance type, and traffic routing. Sync.
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
                 f"Initializing AWSSageMakerCreateEndpointConfig for task: {task_laui}")
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
    Creates a SageMaker endpoint configuration.

    Payload fields:
        endpoint_config_name       (str, required)   -- unique name for the endpoint configuration
        model_name                 (str, required)   -- name of an existing SageMaker model
        instance_type              (str, optional)   -- ML instance type (default: ml.m5.xlarge)
        initial_instance_count     (int, optional)   -- number of instances (default: 1)
        initial_variant_weight     (float, optional) -- traffic weight for this variant (default: 1.0)
        variant_name               (str, optional)   -- production variant name (default: AllTraffic)
        kms_key_id                 (str, optional)   -- KMS key ID for data encryption
        data_capture_config        (dict, optional)  -- data capture configuration dict
        tags                       (list, optional)  -- list of {"Key": ..., "Value": ...} dicts

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

        endpoint_config_name = payload.get("endpoint_config_name")
        model_name = payload.get("model_name")

        if not endpoint_config_name:
            log_error("task", "run", "validation_error", "Required field missing: endpoint_config_name")
            return {"status": "failed", "execution_type": "sync", "result": None,
                    "error": "Required field missing: endpoint_config_name"}
        if not model_name:
            log_error("task", "run", "validation_error", "Required field missing: model_name")
            return {"status": "failed", "execution_type": "sync", "result": None,
                    "error": "Required field missing: model_name"}

        instance_type = payload.get("instance_type", "ml.m5.xlarge")
        initial_instance_count = payload.get("initial_instance_count", 1)
        initial_variant_weight = payload.get("initial_variant_weight", 1.0)
        variant_name = payload.get("variant_name", "AllTraffic")

        production_variant = {
            "VariantName": variant_name,
            "ModelName": model_name,
            "InstanceType": instance_type,
            "InitialInstanceCount": initial_instance_count,
            "InitialVariantWeight": initial_variant_weight,
        }

        kwargs = {
            "EndpointConfigName": endpoint_config_name,
            "ProductionVariants": [production_variant],
        }
        if payload.get("kms_key_id"):
            kwargs["KmsKeyId"] = payload["kms_key_id"]
        if payload.get("data_capture_config"):
            kwargs["DataCaptureConfig"] = payload["data_capture_config"]
        if payload.get("tags"):
            kwargs["Tags"] = payload["tags"]

        log_info("task", "run", "creating_endpoint_config",
                 f"Creating endpoint config: {endpoint_config_name} model={model_name} "
                 f"instance={instance_type} count={initial_instance_count}")
        response = client.create_endpoint_config(**kwargs)
        endpoint_config_arn = response.get("EndpointConfigArn", "")
        log_info("task", "run", "endpoint_config_created",
                 f"Endpoint config created. ARN: {endpoint_config_arn}")

        return {"status": "success", "execution_type": "sync",
                "result": {"endpoint_config_name": endpoint_config_name,
                           "endpoint_config_arn": endpoint_config_arn}}
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
             "CreateEndpointConfig is synchronous — passing through result")
    return {"status": "success",
            "message": "Endpoint configuration created successfully",
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
                     f"Endpoint config {output.get('endpoint_config_name')} created. "
                     f"ARN: {output.get('endpoint_config_arn')}")
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
    "endpoint_config_name": "my-endpoint-config",
    "model_name": "my-model",
    # "instance_type": "ml.m5.xlarge",          # optional, default ml.m5.xlarge
    # "initial_instance_count": 1,              # optional, default 1
    # "initial_variant_weight": 1.0,            # optional, default 1.0
    # "variant_name": "AllTraffic",             # optional, default AllTraffic
    # "kms_key_id": "arn:aws:kms:...",          # optional
    # "data_capture_config": {},                # optional
    # "tags": [{"Key": "env", "Value": "prod"}] # optional
}

prompt = (
    "Creates a SageMaker endpoint configuration defining the model, instance type, and traffic "
    "routing for an inference endpoint. Provide endpoint_config_name and model_name. "
    "Optional: instance_type (default ml.m5.xlarge), initial_instance_count (default 1), "
    "initial_variant_weight (default 1.0), variant_name (default AllTraffic), kms_key_id, "
    "data_capture_config, tags. Synchronous — returns endpoint_config_arn immediately."
)

install_docs = """## Dependencies
- boto3>=1.28.0
- botocore>=1.31.0

## IAM Permissions Required
- sagemaker:CreateEndpointConfig

## Prerequisites
- A SageMaker model must exist (use AWSSageMakerCreateModel first)
- model_name must refer to an existing SageMaker model in the same region
"""

guide_docs = """## What it does

Creates a SageMaker endpoint configuration that defines the model, instance type, and traffic routing for a real-time inference endpoint. The configuration is a prerequisite for AWSSageMakerCreateEndpoint — it acts as a blueprint specifying which model to serve, on what instance type, and how to route traffic for multi-variant A/B testing. This operator is synchronous and returns the endpoint_config_arn immediately.

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

| Field                  | Required | Description                                                                      |
|------------------------|----------|----------------------------------------------------------------------------------|
| endpoint_config_name   | Yes      | Unique name for the endpoint configuration                                       |
| model_name             | Yes      | Name of an existing SageMaker model to serve                                     |
| instance_type          | No       | ML compute instance type (default: ml.m5.xlarge)                                 |
| initial_instance_count | No       | Number of instances to provision (default: 1)                                    |
| initial_variant_weight | No       | Traffic weight for this variant used in A/B testing (default: 1.0)               |
| variant_name           | No       | Production variant identifier (default: AllTraffic)                              |
| kms_key_id             | No       | KMS key ID or ARN for encrypting data at rest on the endpoint                    |
| data_capture_config    | No       | Dict enabling SageMaker Data Capture for model monitoring                        |
| tags                   | No       | List of {"Key": ..., "Value": ...} dicts                                         |

---

## Output (on success)

    {
      "endpoint_config_name": "my-endpoint-config",
      "endpoint_config_arn": "arn:aws:sagemaker:us-east-1:123456789012:endpoint-config/my-endpoint-config"
    }

| Field                | Description                                              |
|----------------------|----------------------------------------------------------|
| endpoint_config_name | Name of the created endpoint configuration               |
| endpoint_config_arn  | Full ARN of the endpoint configuration                   |

---

## Scenarios and Edge Cases

Model not found (ValidationException):
  If model_name does not refer to an existing SageMaker model in the same region, AWS raises ValidationException. Create the model first using AWSSageMakerCreateModel.

Config already exists (ValidationException):
  If an endpoint configuration with the same name already exists, AWS raises ValidationException. Use a unique name or delete the existing config before recreating.

---

## What this operator does NOT do

- Does not create the underlying SageMaker model — use AWSSageMakerCreateModel first.
- Does not create the endpoint — use AWSSageMakerCreateEndpoint after creating this config.
- Does not validate that the requested instance type is available in the region.
- Does not configure multi-variant A/B testing in a single call — each call creates one production variant; multiple variants require multiple configs or a custom ProductionVariants list.
"""

description = (
    "Creates a SageMaker endpoint configuration defining the model, instance type, and traffic "
    "routing for a real-time inference endpoint. Synchronous — returns ARN immediately."
)

publisher = "LeastActionLabs"

metadata = {
    "service": "SageMaker",
    "category": "ML",
    "tags": ["sagemaker", "endpoint-config", "inference", "aws"],
    "airflow_equivalent": "SageMakerEndpointConfigOperator",
}

version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False
status = "draft"

publisher_notes = """## Publisher Notes

An endpoint config is a prerequisite for creating a real-time endpoint — always create the model first (AWSSageMakerCreateModel), then the config, then the endpoint (AWSSageMakerCreateEndpoint).
A single endpoint config can reference multiple ProductionVariants for A/B testing by adjusting InitialVariantWeight — the current implementation creates a single variant named AllTraffic.
The config itself has no cost — charges only begin when an endpoint using this config is InService.
For multi-variant A/B testing, set different variant_name values and weights; this operator supports one variant per invocation — create two endpoint configs and update the endpoint to combine them.
data_capture_config enables SageMaker Data Capture for model monitoring — provides schema {"EnableCapture": true, "InitialSamplingPercentage": 100, "DestinationS3Uri": "s3://...", "CaptureOptions": [...]}.
"""
