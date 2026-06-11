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

        invocation_type = payload.get("invocation_type", "RequestResponse")
        function_payload = payload.get("function_payload", {})
        qualifier = payload.get("qualifier")

        invoke_kwargs = {
            "FunctionName": function_name,
            "InvocationType": invocation_type,
            "Payload": json.dumps(function_payload).encode("utf-8"),
        }
        if qualifier:
            invoke_kwargs["Qualifier"] = qualifier

        log_info("task", "run", "invoke_start",
                 f"Invoking Lambda '{function_name}' with InvocationType='{invocation_type}'")
        resp = client.invoke(**invoke_kwargs)

        status_code = resp.get("StatusCode", 0)
        function_error = resp.get("FunctionError")

        response_payload = None
        if "Payload" in resp:
            raw = resp["Payload"].read()
            try:
                response_payload = json.loads(raw.decode("utf-8"))
            except Exception:
                response_payload = raw.decode("utf-8")

        if function_error:
            log_error("task", "run", "function_error",
                      f"Lambda returned FunctionError='{function_error}': {response_payload}")
            op_status = "failed"
        else:
            op_status = "success"

        result = {
            "function_name": function_name,
            "invocation_type": invocation_type,
            "status_code": status_code,
            "function_error": function_error,
            "response_payload": response_payload,
        }
        log_info("task", "run", "invoke_complete",
                 f"Lambda '{function_name}' invoked - status_code={status_code}, "
                 f"op_status={op_status}")
        return {"execution_type": "sync", "status": op_status, "result": result}

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
             "LambdaInvokeFunction is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "LambdaInvokeFunction completed",
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
                     f"InvocationType: {result.get('invocation_type')} | "
                     f"StatusCode: {result.get('status_code')}")
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
    "invocation_type": "RequestResponse",
    "function_payload": {"key": "value"},
    "qualifier": ""
}

prompt = (
    "Invoke an AWS Lambda function synchronously (RequestResponse) or asynchronously (Event). "
    "Payload must include function_name. invocation_type defaults to RequestResponse. "
    "function_payload dict is serialized to JSON and passed as the Lambda event. "
    "qualifier is optional (e.g. version number or alias). "
    "For RequestResponse: returns status_code, function_error, and parsed response_payload. "
    "Returns status:failed if function_error is set. "
    "Auth: IAM role via STS first, fall back to access keys from connection."
)

install_docs = """# AWSLambdaInvokeFunction — Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": ["lambda:InvokeFunction"],
      "Resource": "*"
    }

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance — no connection keys needed       |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
| Session token | Optionally add aws_session_token in connection                |
"""

guide_docs = """# AWSLambdaInvokeFunction — Operator Guide

## What it does

Invokes an AWS Lambda function and returns the response. Supports both synchronous
(RequestResponse) and asynchronous (Event) invocation types. For synchronous calls,
the response payload is automatically parsed from JSON. Returns status:failed if
Lambda returns a FunctionError (unhandled exception inside the function).

---

## Auth

1. IAM role — tried first via STS. Used automatically if available. No keys needed in connection.
2. Access keys — fallback to aws_access_key_id + aws_secret_access_key from connection.

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
      "invocation_type": "RequestResponse",
      "function_payload": {"key": "value"},
      "qualifier": ""
    }

| Field            | Required | Default           | Description                                          |
|------------------|----------|-------------------|------------------------------------------------------|
| function_name    | Yes      | —                 | Lambda function name or ARN                          |
| invocation_type  | No       | RequestResponse   | "RequestResponse" (sync) or "Event" (async)          |
| function_payload | No       | {}                | JSON-serializable dict passed as the Lambda event    |
| qualifier        | No       | —                 | Version number or alias to invoke a specific version |

---

## Output (on success)

    {
      "function_name": "my-lambda-function",
      "invocation_type": "RequestResponse",
      "status_code": 200,
      "function_error": null,
      "response_payload": {"statusCode": 200, "body": "hello from LeastAction"}
    }

op_status is "success" when function_error is null, "failed" if function_error is set.

---

## Scenarios and Edge Cases

Unhandled exception in Lambda (FunctionError set):
  response_payload contains the error details. op_status is "failed".
  Fix the Lambda function code and redeploy with AWSLambdaCreateFunction.

Async invocation (invocation_type = "Event"):
  Returns status_code 202, response_payload is None. Always op_status "success"
  since Lambda accepts the request but does not return a response.

Function not found:
  AWS returns ResourceNotFoundException. Caught as ClientError, returned as status:failed.

Throttling (TooManyRequestsException):
  Caught as ClientError, returned as status:failed.
"""

description = (
    "Invokes an AWS Lambda function synchronously (RequestResponse) or asynchronously (Event). "
    "The function_payload dict is automatically serialized to JSON and passed as the Lambda event. "
    "For synchronous calls, the response payload is parsed from JSON into a Python dict. "
    "Returns status:failed if Lambda sets a FunctionError — indicating an unhandled exception "
    "inside the function. For async (Event) invocations, returns status:success with no payload. "
    "Optional qualifier supports invoking a specific version or alias. "
    "Auth: IAM role via STS first, fallback to flat access keys in connection. "
    "Pair with AWSLambdaCreateFunction to deploy the function before invoking."
)

publisher = "LeastActionLabs"
metadata = {
    "service": "Lambda", "category": "Compute",
    "tags": ["lambda", "function", "invoke", "serverless", "aws"],
    "airflow_equivalent": "LambdaInvokeFunctionOperator"
}
version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

`invocation_type` controls execution: `RequestResponse` (default) waits synchronously; `Event` triggers async execution returning 202 immediately; `DryRun` validates permissions without executing. `function_payload` is auto-serialized to JSON if a dict. The response payload is base64-decoded automatically. `qualifier` can be a version number or alias to invoke a specific published version.
"""

