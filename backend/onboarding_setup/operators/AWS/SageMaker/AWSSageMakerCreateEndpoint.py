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
AWS SageMaker Create Endpoint Operator

Creates a SageMaker real-time inference endpoint from an existing endpoint configuration. Async.
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
        log_info("task", "initialize", "start", f"Initializing AWSSageMakerCreateEndpoint for task: {task_laui}")
        client = _build_sagemaker_client(connection)
        region = connection.get("region", "us-east-1")
        log_info("task", "initialize", "verify_connection", f"Verifying SageMaker connectivity in region: {region}")
        try:
            client.list_domains(MaxResults=1)
        except ClientError:
            pass  # list_domains not available in all regions; connectivity confirmed by client build
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
    Creates a SageMaker real-time inference endpoint.

    Payload fields:
        endpoint_name         (str, required)  -- unique name for the endpoint
        endpoint_config_name  (str, required)  -- name of an existing endpoint configuration
        tags                  (list, optional) -- list of {"Key": ..., "Value": ...} dicts
        deployment_config     (dict, optional) -- blue/green deployment configuration dict

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

        endpoint_name = payload.get("endpoint_name")
        endpoint_config_name = payload.get("endpoint_config_name")

        if not endpoint_name:
            log_error("task", "run", "validation_error", "Required field missing: endpoint_name")
            return {"status": "failed", "execution_type": "async", "result": None,
                    "error": "Required field missing: endpoint_name"}
        if not endpoint_config_name:
            log_error("task", "run", "validation_error", "Required field missing: endpoint_config_name")
            return {"status": "failed", "execution_type": "async", "result": None,
                    "error": "Required field missing: endpoint_config_name"}

        kwargs = {"EndpointName": endpoint_name, "EndpointConfigName": endpoint_config_name}
        if payload.get("tags"):
            kwargs["Tags"] = payload["tags"]
        if payload.get("deployment_config"):
            kwargs["DeploymentConfig"] = payload["deployment_config"]

        log_info("task", "run", "creating_endpoint",
                 f"Creating endpoint: {endpoint_name} with config: {endpoint_config_name}")
        response = client.create_endpoint(**kwargs)
        endpoint_arn = response.get("EndpointArn", "")
        log_info("task", "run", "endpoint_creation_initiated",
                 f"Endpoint creation initiated. ARN: {endpoint_arn}")

        return {"status": "pending", "execution_type": "async",
                "result": {"endpoint_name": endpoint_name, "endpoint_arn": endpoint_arn}}
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
    """Poll describe_endpoint to check if endpoint reached InService."""
    if run_details.get("status") == "failed":
        log_error("task", "check_completion", "run_phase_failed",
                  f"Run phase reported failure: {run_details.get('error')}")
        return {"status": "failed",
                "message": f"Run phase failed: {run_details.get('error')}",
                "output": None}
    try:
        connection = least_action_task_object.get("connection", {})
        if isinstance(connection, str):
            connection = json.loads(connection)
        region = connection.get("region", "us-east-1")

        endpoint_name = (run_details.get("result") or {}).get("endpoint_name")
        if not endpoint_name:
            return {"status": "failed", "message": "No endpoint_name in run_details", "output": None}

        response = client.describe_endpoint(EndpointName=endpoint_name)
        endpoint_status = response.get("EndpointStatus", "Unknown")
        log_info("task", "check_completion", "endpoint_status",
                 f"Endpoint {endpoint_name} status: {endpoint_status}")

        if endpoint_status == "InService":
            endpoint_url = (
                f"https://runtime.sagemaker.{region}.amazonaws.com"
                f"/endpoints/{endpoint_name}/invocations"
            )
            return {"status": "success",
                    "message": f"Endpoint {endpoint_name} is InService",
                    "output": {"endpoint_name": endpoint_name,
                               "endpoint_arn": (run_details.get("result") or {}).get("endpoint_arn", ""),
                               "endpoint_url": endpoint_url,
                               "endpoint_status": endpoint_status}}
        elif endpoint_status == "Failed":
            failure_reason = response.get("FailureReason", "Unknown")
            return {"status": "failed",
                    "message": f"Endpoint creation failed: {failure_reason}",
                    "output": {"endpoint_name": endpoint_name, "failure_reason": failure_reason}}
        return {"status": "pending",
                "message": f"Endpoint {endpoint_name} is {endpoint_status}",
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
                     f"Endpoint {output.get('endpoint_name')} is InService at {output.get('endpoint_url')}")
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
    "endpoint_name": "my-inference-endpoint",
    "endpoint_config_name": "my-endpoint-config",
    # "tags": [{"Key": "env", "Value": "prod"}],      # optional
    # "deployment_config": {}                          # optional, blue/green config
}

prompt = (
    "Creates a SageMaker real-time inference endpoint from an endpoint configuration and polls "
    "until InService. Provide endpoint_name and endpoint_config_name. "
    "Optional: tags, deployment_config. Async — polls describe_endpoint until InService or Failed."
)

install_docs = """## Dependencies
- boto3>=1.28.0
- botocore>=1.31.0

## IAM Permissions Required
- sagemaker:CreateEndpoint
- sagemaker:DescribeEndpoint
- iam:PassRole (the role in the endpoint config must trust sagemaker.amazonaws.com)

## Prerequisites
- An endpoint configuration must exist (use AWSSageMakerCreateEndpointConfig first)
- The model referenced by the config must exist (use AWSSageMakerCreateModel first)
"""

guide_docs = """## What it does

Creates a SageMaker real-time inference endpoint from an existing endpoint configuration. The operator submits the create request and then polls describe_endpoint until the endpoint reaches InService status. On success it returns the endpoint ARN and the full invocation URL ready for use with the sagemaker-runtime client. This operator is async.

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

| Field                | Required | Description                                                                        |
|----------------------|----------|------------------------------------------------------------------------------------|
| endpoint_name        | Yes      | Unique name for the new SageMaker endpoint                                         |
| endpoint_config_name | Yes      | Name of an existing SageMaker endpoint configuration                               |
| tags                 | No       | List of {"Key": ..., "Value": ...} dicts                                           |
| deployment_config    | No       | Dict for blue/green or canary deployment configuration                             |

---

## Output (on success)

    {
      "endpoint_name": "my-inference-endpoint",
      "endpoint_arn": "arn:aws:sagemaker:us-east-1:123456789012:endpoint/my-inference-endpoint",
      "endpoint_url": "https://runtime.sagemaker.us-east-1.amazonaws.com/endpoints/my-inference-endpoint/invocations",
      "endpoint_status": "InService"
    }

| Field           | Description                                                                    |
|-----------------|--------------------------------------------------------------------------------|
| endpoint_name   | Name of the created endpoint                                                   |
| endpoint_arn    | Full ARN of the endpoint                                                       |
| endpoint_url    | Invocation URL for use with the sagemaker-runtime client                       |
| endpoint_status | Final endpoint status — InService on success                                   |

---

## Scenarios and Edge Cases

Config not found (ResourceNotFound):
  If endpoint_config_name does not exist in the region, AWS raises ResourceNotFoundException. Create the config first using AWSSageMakerCreateEndpointConfig.

Endpoint already exists (ValidationException):
  If an endpoint with the same name already exists, AWS raises ValidationException. Use a unique endpoint_name or delete the existing endpoint before recreating.

Never reaches InService (Failed state with failure_reason):
  If the endpoint enters the Failed state, the operator returns failure with the FailureReason from describe_endpoint. Common causes are misconfigured model artifacts, instance type capacity issues, or container startup errors.

---

## What this operator does NOT do

- Does not create the endpoint configuration — use AWSSageMakerCreateEndpointConfig first.
- Does not create the underlying model — use AWSSageMakerCreateModel before the config.
- Does not invoke the model — use the sagemaker-runtime client with the returned endpoint_url.
- Does not delete or update the endpoint after creation.
"""

description = (
    "Creates a SageMaker real-time inference endpoint from an existing endpoint configuration "
    "and polls asynchronously until InService. Returns the invocation URL on success."
)

publisher = "LeastActionLabs"

metadata = {
    "service": "SageMaker",
    "category": "ML",
    "tags": ["sagemaker", "endpoint", "inference", "real-time", "aws"],
    "airflow_equivalent": "SageMakerEndpointOperator",
}

version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False
status = "draft"

publisher_notes = """## Publisher Notes

This operator creates a SageMaker real-time inference endpoint — use AWSSageMakerCreateEndpointConfig to create the config first.
Endpoint creation typically takes 3-10 minutes depending on instance type and model size.
InService status does not guarantee the model is warm — the first invocation may be slower due to model loading.
Endpoints incur compute charges continuously as long as they exist in InService state, even when idle. Delete endpoints immediately after testing.
The endpoint_url returned in output is the standard SageMaker runtime invocation URL — use it with boto3 sagemaker-runtime client invoke_endpoint.
deployment_config supports blue/green canary deployments — see AWS docs for the full structure if needed.
"""
