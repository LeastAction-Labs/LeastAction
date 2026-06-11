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
from botocore.exceptions import ClientError, BotoCoreError
from src.common.logger.logger import log_info, log_error


def _build_ssm_client(connection: dict):
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
        return session.client("ssm")

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
        return session.client("ssm")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info("task", "initialize", "auth_default",
             "Using default AWS credential chain (instance profile / ECS task role / env / config)")
    return boto3.Session(region_name=region).client("ssm")


def initialize(least_action_task_object):
    try:
        connection = least_action_task_object.get("connection", {})
        if isinstance(connection, str):
            connection = json.loads(connection)

        log_info("task", "initialize", "building_client",
                 f"region={connection.get('region', 'us-east-1')}")

        client = _build_ssm_client(connection)
        client.describe_instance_information(MaxResults=5)
        log_info("task", "initialize", "connectivity_ok", "SSM client initialized and verified")
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
        connection = least_action_task_object.get("connection", {})
        if isinstance(connection, str):
            connection = json.loads(connection)

        payload = least_action_task_object.get("payload", {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                log_error("task", "run", "payload_parse_error", "Failed to parse payload as JSON")
                return {"status": "failed", "execution_type": "sync", "result": None,
                        "error": "Invalid payload format — expected flat JSON object"}

        command_id = payload.get("command_id")
        if not command_id:
            msg = "Missing required payload field: command_id"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        instance_id = connection.get("ec2_instance_id")
        if not instance_id:
            msg = "Missing required connection field: ec2_instance_id"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        plugin_name = payload.get("plugin_name", "aws:RunShellScript")

        log_info("task", "run", "get_invocation",
                 f"Fetching invocation for CommandId: {command_id}, Instance: {instance_id}")

        response = client.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id,
            PluginName=plugin_name,
        )

        invocation_status = response.get("Status")
        standard_output = response.get("StandardOutputContent", "")
        standard_error = response.get("StandardErrorContent", "")
        response_code = response.get("ResponseCode", -1)

        op_status = "success" if invocation_status == "Success" else "failed"

        log_info("task", "run", "invocation_result",
                 f"Status: {invocation_status}, ResponseCode: {response_code}, "
                 f"stdout_len: {len(standard_output)}, stderr_len: {len(standard_error)}")

        return {
            "execution_type": "sync",
            "status": op_status,
            "result": {
                "command_id": command_id,
                "instance_id": instance_id,
                "invocation_status": invocation_status,
                "response_code": response_code,
                "standard_output": standard_output,
                "standard_error": standard_error,
            }
        }

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
             "SSM GetCommandInvocation is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "SSM GetCommandInvocation completed",
        "output": run_details.get("result", {})
    }


def finish(least_action_task_object, client, completion_details, run_details):
    try:
        result = run_details.get("result", {})
        status = completion_details.get("status", "unknown")
        log_info("task", "finish", "final_status", f"Completed with status: {status}")
        if status == "success":
            log_info("task", "finish", "summary",
                     f"CommandId: {result.get('command_id')} | "
                     f"InvocationStatus: {result.get('invocation_status')} | "
                     f"ResponseCode: {result.get('response_code')}")
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
    "region": "us-east-1",
    "ec2_instance_id": "i-0abc123def456789"
}

payload = {
    "command_id": "abc12345-1234-1234-1234-abc123456789",
    "plugin_name": "aws:RunShellScript"
}

prompt = (
    "Retrieve the output of a previously dispatched SSM Run Command invocation. "
    "Reads command_id from payload and ec2_instance_id from connection. "
    "Calls get_command_invocation and returns stdout, stderr, response_code, and invocation status. "
    "Returns status:success if invocation_status == 'Success', otherwise status:failed. "
    "Auth: IAM role via STS first, fall back to access keys from connection."
)

install_docs = """# AWSSSMGetCommandInvocation — Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetCommandInvocation",
        "ssm:DescribeInstanceInformation"
      ],
      "Resource": "*"
    }

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance — no connection keys needed       |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
| Session token | Optionally add aws_session_token in connection                |
"""

guide_docs = """# AWSSSMGetCommandInvocation — Operator Guide

## What it does

Retrieves the full output of a previously dispatched SSM Run Command invocation, including
stdout, stderr, response code, and final invocation status. This is the companion to
AWSSSMRunCommand — run that operator first to get a command_id, then use this operator
to collect results.

The command_id comes from the payload. The instance_id is read from connection.ec2_instance_id
to keep payload focused on identifying the command rather than the target.

---

## Auth

1. IAM role — tried first via STS. Used automatically if available. No keys needed in connection.
2. Access keys — fallback to aws_access_key_id + aws_secret_access_key from connection.

---

## Connection

    {
      "region": "us-east-1",
      "ec2_instance_id": "i-0abc123def456789",
      "aws_access_key_id": "",       // optional — omit to use IAM role
      "aws_secret_access_key": "",   // optional — omit to use IAM role
      "aws_session_token": ""        // optional — for temporary credentials
    }

---

## Payload

    {
      "command_id": "abc12345-1234-1234-1234-abc123456789",
      "plugin_name": "aws:RunShellScript"
    }

| Field       | Required | Default              | Description                                     |
|-------------|----------|----------------------|-------------------------------------------------|
| command_id  | Yes      | —                    | Command ID returned by AWSSSMRunCommand         |
| plugin_name | No       | aws:RunShellScript   | SSM document plugin to retrieve output for      |

---

## Output (on success)

    {
      "command_id": "abc12345-...",
      "instance_id": "i-0abc123def456789",
      "invocation_status": "Success",
      "response_code": 0,
      "standard_output": "hello from LeastAction\\n",
      "standard_error": ""
    }

op_status is "success" when invocation_status == "Success", "failed" otherwise.

---

## Scenarios and Edge Cases

Command still in progress (InProgress/Pending):
  get_command_invocation returns those statuses. op_status will be "failed".
  Wait and retry, or poll with a scheduled task.

InvocationDoesNotExist:
  Raised if the command_id + instance_id pair is invalid or the command hasn't
  reached the instance yet. Caught as ClientError, returned as status:failed.

Large stdout/stderr:
  SSM truncates output at 48,000 characters. For larger output, configure the
  SSM document to write to S3 and read from there.
"""

description = (
    "Retrieves the output of a previously dispatched SSM Run Command invocation. "
    "Reads command_id from payload and ec2_instance_id from connection, then calls "
    "get_command_invocation to fetch stdout, stderr, response code, and final status. "
    "Returns status:success when invocation_status is 'Success', status:failed otherwise. "
    "Auth: IAM role via STS first, fallback to flat access keys in connection. "
    "Designed to be paired with AWSSSMRunCommand — run that first to obtain a command_id."
)

publisher = "LeastActionLabs"

metadata = {
    "service": "SSM",
    "category": "Management",
    "tags": ["ssm", "run-command", "invocation", "ec2", "aws"],
    "airflow_equivalent": "SsmGetCommandInvocationOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

Call this operator after AWSSSMRunCommand to retrieve results. If the command is still running (InProgress/Pending), invocation_status will not be 'Success' and op_status will be 'failed' — retry after a delay or poll. SSM truncates stdout/stderr at 48,000 characters; configure S3 output in the SSM document for larger output. InvocationDoesNotExist is returned if the command hasn't reached the instance yet — wait and retry.
"""
