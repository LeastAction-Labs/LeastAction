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

codeblock = {"main.py": """import json
import base64
import boto3
from botocore.exceptions import ClientError
from src.common.logger.logger import log_info, log_error


def _build_lambda_client(connection: dict):
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
        return session.client("lambda")

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
        return session.client("lambda")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info("task", "initialize", "auth_default",
             "Using default AWS credential chain (instance profile / ECS task role / env / config)")
    return boto3.Session(region_name=region).client("lambda")


def initialize(least_action_task_object):
    try:
        connection = least_action_task_object.get("connection", {})
        if isinstance(connection, str):
            connection = json.loads(connection)
        client = _build_lambda_client(connection)
        log_info("task", "initialize", "client_ready", "Lambda client initialized")
        return client
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "initialize", "client_error", f"({error_code}) {error_msg}")
        raise
    except Exception as e:
        log_error("task", "initialize", "init_failed", f"Error: {str(e)}")
        raise


def run(least_action_task_object, client):
    try:
        payload = least_action_task_object.get("payload", "{}")
        if isinstance(payload, str):
            payload = json.loads(payload)
        if "data" in payload and isinstance(payload["data"], dict):
            payload = payload["data"]

        function_name = payload.get("function_name")
        if not function_name:
            msg = "Missing required payload field: function_name"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        zip_file_b64 = payload.get("zip_file_b64")
        if not zip_file_b64:
            msg = "Missing required payload field: zip_file_b64 (base64-encoded deployment zip)"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        zip_bytes = base64.b64decode(zip_file_b64)
        runtime = payload.get("runtime", "python3.11")
        handler = payload.get("handler", "lambda_function.lambda_handler")
        timeout = payload.get("timeout", 30)
        memory_size = payload.get("memory_size", 128)
        description = payload.get("description", "")
        environment = payload.get("environment", {})

        # Check if function already exists
        function_exists = False
        try:
            client.get_function(FunctionName=function_name)
            function_exists = True
        except client.exceptions.ResourceNotFoundException:
            function_exists = False

        if function_exists:
            log_info("task", "run", "update_function",
                     f"Function '{function_name}' exists - updating code and config")
            code_resp = client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_bytes,
                Publish=True,
            )
            client.update_function_configuration(
                FunctionName=function_name,
                Handler=handler,
                Runtime=runtime,
                Timeout=timeout,
                MemorySize=memory_size,
                Description=description,
                Environment={"Variables": environment},
            )
            result = {
                "action": "updated",
                "function_name": function_name,
                "function_arn": code_resp.get("FunctionArn"),
                "runtime": runtime,
                "handler": handler,
                "version": str(code_resp.get("Version", "")),
                "last_modified": str(code_resp.get("LastModified", "")),
            }
        else:
            role_arn = payload.get("role_arn")
            if not role_arn:
                msg = "Missing required payload field: role_arn (required when creating a new function)"
                log_error("task", "run", "payload_validation_failed", msg)
                return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

            log_info("task", "run", "create_function", f"Creating new Lambda function '{function_name}'")
            resp = client.create_function(
                FunctionName=function_name,
                Runtime=runtime,
                Role=role_arn,
                Handler=handler,
                Code={"ZipFile": zip_bytes},
                Description=description,
                Timeout=timeout,
                MemorySize=memory_size,
                Publish=True,
                Environment={"Variables": environment},
            )
            result = {
                "action": "created",
                "function_name": function_name,
                "function_arn": resp.get("FunctionArn"),
                "runtime": runtime,
                "handler": handler,
                "version": str(resp.get("Version", "")),
                "last_modified": str(resp.get("LastModified", "")),
            }

        log_info("task", "run", "function_ready",
                 f"Lambda function '{function_name}' {result['action']} successfully - "
                 f"ARN: {result['function_arn']}")
        return {"execution_type": "sync", "status": "success", "result": result}

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "client_error", f"({error_code}) {error_msg}")
        return {"execution_type": "sync", "status": "failed",
                "result": {"error": f"({error_code}) {error_msg}"}}
    except Exception as e:
        log_error("task", "run", "run_failed", f"Unexpected error: {str(e)}")
        return {"execution_type": "sync", "status": "failed", "result": {"error": str(e)}}


def check_completion(least_action_task_object, client, run_details):
    log_info("task", "check_completion", "sync_complete",
             "LambdaCreateFunction is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "LambdaCreateFunction completed",
        "output": run_details.get("result", {})
    }


def finish(least_action_task_object, client, completion_details, run_details):
    try:
        result = run_details.get("result", {})
        status = completion_details.get("status", "unknown")
        log_info("task", "finish", "final_status", f"Completed with status: {status}")
        if status == "success":
            log_info("task", "finish", "summary",
                     f"Function: {result.get('function_name')} | "
                     f"Action: {result.get('action')} | "
                     f"ARN: {result.get('function_arn')} | "
                     f"Version: {result.get('version')}")
        else:
            log_error("task", "finish", "operation_failed",
                      completion_details.get("message", "No message"))
        if client:
            try:
                client.close()
                log_info("task", "finish", "client_closed", "boto3 client closed successfully")
            except Exception as close_error:
                log_error("task", "finish", "client_close_error", f"Error closing client: {str(close_error)}")
        log_info("task", "finish", "cleanup_complete", "Cleanup complete")
    except Exception as e:
        log_error("task", "finish", "cleanup_error", f"Error in finish: {str(e)}")
"""}

bashblock = {"main.sh": """#!/bin/bash
set -e
pip install boto3>=1.28.0
pip install botocore>=1.31.0
echo "Dependencies installed successfully"
"""}

connection = {
    "region": "us-east-1"
}

payload = {
    "function_name": "my-lambda-function",
    "runtime": "python3.11",
    "handler": "lambda_function.lambda_handler",
    "role_arn": "arn:aws:iam::123456789012:role/my-lambda-role",
    "timeout": 30,
    "memory_size": 128,
    "description": "My Lambda function",
    "environment": {},
    "zip_file_b64": "<base64-encoded zip file content>"
}

prompt = (
    "Create or update an AWS Lambda function from a base64-encoded zip archive. "
    "If the function already exists (by name), updates its code and configuration. "
    "If it does not exist, creates it — role_arn is required only for creation. "
    "Payload must include function_name and zip_file_b64. "
    "Optional: runtime, handler, timeout, memory_size, description, environment. "
    "Returns action (created/updated), function_arn, runtime, handler, version, and last_modified. "
    "Auth: IAM role via STS first, fall back to access keys from connection. "
    "No connectivity check in initialize() — Lambda has no lightweight read-only call under LambdaFullAccess."
)

install_docs = """# AWSLambdaCreateFunction — Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "lambda:CreateFunction",
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration",
        "lambda:GetFunction",
        "iam:PassRole"
      ],
      "Resource": "*"
    }

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance — no connection keys needed       |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
| Session token | Optionally add aws_session_token in connection                |

## Preparing the zip_file_b64

    zip function.zip lambda_function.py
    python3 -c "import base64; print(base64.b64encode(open('function.zip','rb').read()).decode())"
"""

guide_docs = """# AWSLambdaCreateFunction — Operator Guide

## What it does

Creates or updates an AWS Lambda function using a deployment zip archive provided as
base64-encoded bytes in the payload. If the function already exists by name, its code
and configuration are updated in place. If it does not exist, a new function is created —
in which case role_arn is required.

Returns action ("created" or "updated"), function ARN, runtime, handler, version, and
last_modified timestamp.

---

## Auth

1. IAM role — tried first via STS. Used automatically if available. No keys needed in connection.
2. Access keys — fallback to aws_access_key_id + aws_secret_access_key from connection.

Note: initialize() does not perform a connectivity check because lambda:ListFunctions
is not included under AWSLambdaFullAccess. Auth is validated implicitly on the first API call.

---

## Connection

    {
      "region": "us-east-1",
      "aws_access_key_id": "",       // optional — omit to use IAM role
      "aws_secret_access_key": "",   // optional — omit to use IAM role
      "aws_session_token": ""        // optional — for temporary credentials
    }

---

## Payload

    {
      "function_name": "my-lambda-function",
      "runtime": "python3.11",
      "handler": "lambda_function.lambda_handler",
      "role_arn": "arn:aws:iam::123456789012:role/my-lambda-role",
      "timeout": 30,
      "memory_size": 128,
      "description": "My Lambda function",
      "environment": {},
      "zip_file_b64": "<base64-encoded zip>"
    }

| Field         | Required      | Default                            | Description                                     |
|---------------|---------------|------------------------------------|-------------------------------------------------|
| function_name | Yes           | —                                  | Lambda function name                            |
| zip_file_b64  | Yes           | —                                  | Base64-encoded deployment zip archive           |
| role_arn      | If creating   | —                                  | IAM role ARN for the function execution role    |
| runtime       | No            | python3.11                         | Lambda runtime identifier                       |
| handler       | No            | lambda_function.lambda_handler     | Module.function entrypoint                      |
| timeout       | No            | 30                                 | Max execution time in seconds (max 900)         |
| memory_size   | No            | 128                                | Memory in MB (128–10240)                        |
| description   | No            | ""                                 | Human-readable description                      |
| environment   | No            | {}                                 | Dict of environment variable key-value pairs    |

---

## Output (on success)

    {
      "action": "created",
      "function_name": "my-lambda-function",
      "function_arn": "arn:aws:lambda:us-east-1:123456789012:function:my-lambda-function",
      "runtime": "python3.11",
      "handler": "lambda_function.lambda_handler",
      "version": "1",
      "last_modified": "2026-04-09T13:07:45.250+0000"
    }

action is "created" on first run, "updated" on subsequent runs.

---

## Scenarios and Edge Cases

Function does not exist + role_arn missing:
  Returns status:failed — role_arn is required for create_function.

zip_file_b64 missing or invalid base64:
  base64.b64decode raises an exception — caught and returned as status:failed.

IAM permission missing (iam:PassRole):
  AWS returns AccessDeniedException when creating a function. Caught as ClientError.
"""

description = (
    "Creates or updates an AWS Lambda function from a base64-encoded zip deployment archive. "
    "If the function already exists by name, updates its code via update_function_code and "
    "reconfigures it via update_function_configuration. If it does not exist, calls create_function "
    "with the full configuration — role_arn is required only for creation. "
    "Supports runtime, handler, timeout, memory_size, description, and environment variables. "
    "Returns action (created/updated), function_arn, runtime, handler, version, and last_modified. "
    "Auth: IAM role via STS first, fallback to flat access keys in connection. "
    "No connectivity check in initialize() since lambda:ListFunctions is not available under LambdaFullAccess. "
    "Pair with AWSLambdaInvokeFunction to invoke the deployed function."
)

publisher = "LeastActionLabs"
metadata = {
    "service": "Lambda", "category": "Compute",
    "tags": ["lambda", "function", "deploy", "serverless", "aws"],
    "airflow_equivalent": "LambdaCreateFunctionOperator"
}
version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

`zip_file_b64` must be a base64-encoded zip containing your function code and dependencies. The zip must include the handler file matching the `handler` field (e.g. `index.handler` means `index.py` with a `handler` function). If the function already exists, this operator updates its code. `role_arn` must trust `lambda.amazonaws.com` as a service principal.
"""

