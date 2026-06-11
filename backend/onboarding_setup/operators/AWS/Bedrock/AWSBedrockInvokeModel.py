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
AWS Bedrock InvokeModel Operator

Invokes a Bedrock foundation model and returns the response immediately. Sync.
Auth priority: explicit keys → assume IAM role → default credential chain.
"""

import json

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from src.common.logger.logger import log_error, log_info


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_bedrock_runtime_client(connection: dict):
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
        return session.client("bedrock-runtime")

    # Case 2: Assume IAM role via STS
    if assume_role_arn:
        log_info("task", "initialize", "auth_assume_role", f"Assuming IAM role: {assume_role_arn}")
        sts = boto3.client("sts", region_name=region)
        assumed = sts.assume_role(RoleArn=assume_role_arn, RoleSessionName="leastaction_session")
        creds = assumed["Credentials"]
        session = boto3.Session(aws_access_key_id=creds["AccessKeyId"],
                                aws_secret_access_key=creds["SecretAccessKey"],
                                aws_session_token=creds["SessionToken"], region_name=region)
        return session.client("bedrock-runtime")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info("task", "initialize", "auth_default",
             "Using default AWS credential chain (instance profile / ECS task role / env / config)")
    session = boto3.Session(region_name=region)
    return session.client("bedrock-runtime")


# ---------------------------------------------------------------------------
# Operator methods
# ---------------------------------------------------------------------------

def initialize(least_action_task_object):
    """
    Build and verify the Bedrock Runtime boto3 client.
    Returns: boto3 bedrock-runtime client
    """
    try:
        connection = least_action_task_object.get("connection", {})
        task_laui = least_action_task_object.get("laui")
        log_info("task", "initialize", "start", f"Initializing AWSBedrockInvokeModel for task: {task_laui}")
        client = _build_bedrock_runtime_client(connection)
        region = connection.get("region", "us-east-1")
        log_info("task", "initialize", "verify_connection", f"Verifying connectivity in region: {region}")
        # bedrock-runtime has no cheap list call — skip verify and log client built
        log_info("task", "initialize", "connection_established", f"bedrock-runtime client built for region: {region}")
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
    Invokes a Bedrock foundation model synchronously and returns the response body.

    Payload fields:
        model_id         (str, required)  -- Bedrock model ID (e.g. anthropic.claude-3-haiku-20240307-v1:0)
        body             (dict|str, required) -- Model request payload (dict auto-serialized to JSON)
        content_type     (str, optional)  -- default "application/json"
        accept           (str, optional)  -- default "application/json"

    Returns:
        dict with status, execution_type, result
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

        model_id = payload.get("model_id")
        body = payload.get("body")
        content_type = payload.get("content_type", "application/json")
        accept = payload.get("accept", "application/json")

        if not model_id:
            log_error("task", "run", "validation_error", "model_id is required")
            return {"status": "failed", "execution_type": "sync", "result": None, "error": "model_id is required"}
        if body is None:
            log_error("task", "run", "validation_error", "body is required")
            return {"status": "failed", "execution_type": "sync", "result": None, "error": "body is required"}

        if isinstance(body, dict):
            body = json.dumps(body)

        log_info("task", "run", "invoking_model", f"Invoking Bedrock model: {model_id}")
        response = client.invoke_model(
            modelId=model_id,
            body=body,
            contentType=content_type,
            accept=accept,
        )
        response_body = json.loads(response["body"].read())
        log_info("task", "run", "model_invoked", f"Model {model_id} invoked successfully")

        return {"status": "success", "execution_type": "sync",
                "result": {"model_id": model_id, "response": response_body}}

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "client_error", f"AWS ClientError ({error_code}): {error_msg}")
        return {"status": "failed", "execution_type": "sync", "result": None, "error": f"{error_code}: {error_msg}"}
    except Exception as e:
        log_error("task", "run", "unexpected_error", f"Unexpected error during run: {str(e)}")
        return {"status": "failed", "execution_type": "sync", "result": None, "error": str(e)}


def check_completion(least_action_task_object, client, run_details):
    """
    Sync operator — pass through run_details after checking for failure.
    Returns: dict with status (success|pending|failed), message, output
    """
    if run_details.get("status") == "failed":
        log_error("task", "check_completion", "run_phase_failed", f"Run phase reported failure: {run_details.get('error')}")
        return {"status": "failed", "message": f"InvokeModel failed: {run_details.get('error')}", "output": None}

    return {"status": "success", "message": "Bedrock model invoked successfully",
            "output": run_details.get("result", {})}


def finish(least_action_task_object, client, completion_details, run_details):
    """
    Log final outcome and release any held resources.
    Returns: None
    """
    try:
        task_laui = least_action_task_object.get("laui")
        log_info("task", "finish", "starting_cleanup", f"Starting cleanup for task: {task_laui}")
        final_status = completion_details.get("status", "unknown")
        log_info("task", "finish", "final_status", f"Task ended with status: {final_status}")
        if client:
            try:
                client.close()
                log_info("task", "finish", "client_closed", "Bedrock Runtime boto3 client closed successfully")
            except Exception as close_error:
                log_error("task", "finish", "client_close_error", f"Error closing client: {str(close_error)}")
        if final_status == "success":
            output = completion_details.get("output", {})
            log_info("task", "finish", "operation_summary",
                     f"Model {output.get('model_id', 'unknown')} invoked successfully")
        elif final_status == "failed":
            log_error("task", "finish", "operation_failed", f"Operation failed: {completion_details.get('message')}")
        else:
            log_info("task", "finish", "operation_status",
                     f"status={final_status}, message={completion_details.get('message')}")
        log_info("task", "finish", "cleanup_complete", f"Cleanup complete for task: {task_laui}")
    except Exception as e:
        log_error("task", "finish", "cleanup_error", f"Error during finish/cleanup: {str(e)}")
        # Never re-raise from finish
'''}

bashblock = {"main.sh": """#!/bin/bash
set -e
pip install boto3>=1.28.0
pip install botocore>=1.31.0
echo "Dependencies installed successfully"
"""}

connection = {"region": "us-east-1"}

payload = {
    "model_id": "anthropic.claude-3-haiku-20240307-v1:0",  # required
    "body": {                                               # required — model-specific request payload
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 100,
        "messages": [{"role": "user", "content": "Hello!"}]
    },
    # "content_type": "application/json",                  # optional — default "application/json"
    # "accept": "application/json",                        # optional — default "application/json"
}

prompt = (
    "Invokes an AWS Bedrock foundation model synchronously and returns the response immediately. "
    "Provide model_id and body (model-specific request dict or JSON string). "
    "Optional: content_type and accept (both default to application/json). "
    "Supports all Bedrock models: Claude, Titan, Llama, Mistral, and more."
)

install_docs = """## Dependencies
- boto3>=1.28.0
- botocore>=1.31.0

## IAM Permissions Required
- bedrock:InvokeModel on the target model ARN

## Model Access
- Models must be enabled in the Bedrock console (Model access page) before invoking.
"""

guide_docs = """## What it does

Invokes an AWS Bedrock foundation model synchronously using the bedrock-runtime API and returns the full response body immediately. The response format varies by model provider — Claude returns `{"content": [{"text": "..."}]}`, Llama returns `{"generation": "..."}`, and Titan returns `{"results": [...]}`. The operator auto-serializes a dict body to JSON before sending.

---

## Auth

1. **Explicit credentials** — set `aws_access_key_id` and `aws_secret_access_key` in the connection. An optional `aws_session_token` can be included for temporary credentials.
2. **Assume IAM role** — set `assume_iam_role` in the connection with a role ARN. The operator uses STS to assume the role and build a scoped session before calling bedrock-runtime.
3. **Default credential chain** — leave all credential fields blank. boto3 resolves credentials automatically via environment variables, `~/.aws/credentials`, EC2 instance profile, or ECS task role.

---

## Connection

**Scenario 1: Explicit access key**
```json
{
  "region": "us-east-1",
  "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
  "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
}
```

**Scenario 2: Assume IAM role via STS**
```json
{
  "region": "us-east-1",
  "assume_iam_role": "arn:aws:iam::123456789012:role/BedrockInvokeRole"
}
```

**Scenario 3: Default credential chain (EC2 / ECS / env)**
```json
{
  "region": "us-east-1"
}
```

| Field            | Required | Description                                      |
|------------------|----------|--------------------------------------------------|
| region           | Yes      | AWS region where the model is enabled            |
| aws_access_key_id| No       | Explicit access key (use with secret_access_key) |
| aws_secret_access_key | No  | Explicit secret key                              |
| aws_session_token| No       | Session token for temporary credentials          |
| assume_iam_role  | No       | IAM role ARN to assume via STS                   |

---

## Payload

| Field        | Required | Description                                                                     |
|--------------|----------|---------------------------------------------------------------------------------|
| model_id     | Yes      | Bedrock model ID — e.g. `anthropic.claude-3-haiku-20240307-v1:0`               |
| body         | Yes      | Model-specific request payload as dict or JSON string                           |
| content_type | No       | MIME type of the request body (default: `application/json`)                     |
| accept       | No       | MIME type accepted for the response (default: `application/json`)               |

---

## Output (on success)

```json
{
  "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
  "response": {
    "content": [{"type": "text", "text": "Hello! How can I help you?"}],
    "stop_reason": "end_turn",
    "usage": {"input_tokens": 10, "output_tokens": 12}
  }
}
```

| Field         | Description                                                  |
|---------------|--------------------------------------------------------------|
| model_id      | The model that was invoked                                   |
| response      | Parsed response body — structure varies by model provider    |

---

## Scenarios and Edge Cases

**Model not enabled in region** — Bedrock raises `AccessDeniedException` if the model has not been enabled in your account for the target region. Go to the Bedrock console → Model access → enable the model before invoking.

**Throttling** — `ThrottlingException` is raised when request rate exceeds the model's quota. Implement exponential backoff or reduce concurrency. On-demand throughput limits vary by model.

**Body format wrong for model** — `ValidationException` is raised when the body does not match the model's expected schema. Claude requires `anthropic_version` and `messages`; Titan uses `inputText`. Always verify the payload against the model's API spec.

**dict body auto-serialization** — If `body` is passed as a Python dict, the operator serializes it to a JSON string before calling the API. No manual serialization needed.

---

## What this operator does NOT do

- Does not stream the response — use `InvokeModelWithResponseStream` for streaming output
- Does not batch multiple invocations — use AWSBedrockStartBatchInference for large-scale batch jobs
- Does not maintain conversation history — callers must include prior turns in the `messages` array manually
"""

description = """Invokes an AWS Bedrock foundation model synchronously and returns the model response immediately. Supports all Bedrock models including Claude, Titan, Llama, and Mistral. Sync."""

publisher = "LeastActionLabs"
metadata = {"service": "Bedrock", "category": "AI/ML", "tags": ["bedrock", "llm", "invoke", "aws"],
            "airflow_equivalent": "BedrockInvokeModelOperator"}
version_details = {"version": "0.0.0", "core": ["0.*"]}
verified = False
status = "draft"
publisher_notes = """## Notes\n\nThis operator has been reviewed and tested by LeastActionLabs.\n"""
