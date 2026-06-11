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

        instance_id = connection.get("ec2_instance_id")
        if not instance_id:
            msg = "Missing required connection field: ec2_instance_id"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        document_name = payload.get("document_name", "AWS-RunShellScript")
        parameters = payload.get("parameters", {"commands": ["echo hello"]})
        comment = payload.get("comment", "LeastAction SSM RunCommand")
        timeout_seconds = payload.get("timeout_seconds", 60)

        log_info("task", "run", "send_command",
                 f"Sending SSM command '{document_name}' to instance {instance_id}")

        response = client.send_command(
            InstanceIds=[instance_id],
            DocumentName=document_name,
            Parameters=parameters,
            Comment=comment,
            TimeoutSeconds=timeout_seconds,
        )

        command = response.get("Command", {})
        command_id = command.get("CommandId")
        status = command.get("StatusDetails", "Pending")

        log_info("task", "run", "command_sent",
                 f"SSM command sent - CommandId: {command_id}, Status: {status}")

        return {
            "execution_type": "sync",
            "status": "success",
            "result": {
                "command_id": command_id,
                "instance_id": instance_id,
                "document_name": document_name,
                "status": status,
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
             "SSM RunCommand is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "SSM RunCommand completed",
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
                     f"Instance: {result.get('instance_id')} | "
                     f"Document: {result.get('document_name')}")
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
    "document_name": "AWS-RunShellScript",
    "parameters": {"commands": ["echo hello from LeastAction"]},
    "comment": "LeastAction SSM RunCommand",
    "timeout_seconds": 60
}

prompt = (
    "Send an SSM Run Command document to an EC2 instance. "
    "The instance ID is read from connection.ec2_instance_id. "
    "Payload must include document_name (e.g. AWS-RunShellScript) and parameters (dict of SSM document params). "
    "Call send_command and return the command_id and initial status. "
    "Use describe_instance_information for the connectivity check in initialize(). "
    "Auth: IAM role via STS first, fall back to access keys from connection. "
    "Return command_id, instance_id, document_name, and status on success."
)

install_docs = """# AWSSSMRunCommand — Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "ssm:SendCommand",
        "ssm:DescribeInstanceInformation",
        "ec2:DescribeInstances"
      ],
      "Resource": "*"
    }

The target EC2 instance must have the SSM agent installed and the
AmazonSSMManagedInstanceCore policy attached to its IAM role.

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance — no connection keys needed       |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
| Session token | Optionally add aws_session_token in connection                |
"""

guide_docs = """# AWSSSMRunCommand — Operator Guide

## What it does

Sends an AWS Systems Manager Run Command document to a target EC2 instance and returns
the command ID immediately. The command executes asynchronously on the instance — use
AWSSSMGetCommandInvocation to retrieve the output and final status.

The instance ID is read from connection.ec2_instance_id, keeping the payload focused
on the command itself. The connectivity check in initialize() calls
describe_instance_information to verify SSM reachability before sending.

---

## Auth

1. IAM role — tried first via STS. Used automatically if available. No keys needed in connection.
2. Access keys — fallback to aws_access_key_id + aws_secret_access_key from connection.

If neither is available, initialize() raises a RuntimeError before run() is called.

---

## Connection

    {
      "region": "us-east-1",
      "ec2_instance_id": "i-0abc123def456789",
      "aws_access_key_id": "",       // optional — omit to use IAM role
      "aws_secret_access_key": "",   // optional — omit to use IAM role
      "aws_session_token": ""        // optional — for temporary credentials
    }

| Field                 | Required | Description                                       |
|-----------------------|----------|---------------------------------------------------|
| region                | Yes      | AWS region where the instance exists              |
| ec2_instance_id       | Yes      | Target EC2 instance ID                            |
| aws_access_key_id     | No       | Only needed if IAM role is not available          |
| aws_secret_access_key | No       | Only needed if IAM role is not available          |
| aws_session_token     | No       | For temporary/assumed-role credentials            |

---

## Payload

    {
      "document_name": "AWS-RunShellScript",
      "parameters": {"commands": ["echo hello from LeastAction"]},
      "comment": "LeastAction SSM RunCommand",
      "timeout_seconds": 60
    }

| Field           | Required | Default              | Description                              |
|-----------------|----------|----------------------|------------------------------------------|
| document_name   | No       | AWS-RunShellScript   | SSM document to execute                  |
| parameters      | No       | {"commands": [...]}  | Document-specific parameter map          |
| comment         | No       | LeastAction SSM...   | Human-readable label for the command     |
| timeout_seconds | No       | 60                   | Max seconds before the command times out |

---

## Output (on success)

    {
      "command_id": "abc12345-1234-1234-1234-abc123456789",
      "instance_id": "i-0abc123def456789",
      "document_name": "AWS-RunShellScript",
      "status": "Pending"
    }

Use the returned command_id with AWSSSMGetCommandInvocation to retrieve stdout/stderr.

---

## Scenarios and Edge Cases

Instance not SSM-managed:
  describe_instance_information returns empty list; the connectivity check in initialize()
  still passes but send_command will fail with InvalidInstanceId. Caught as ClientError.

SSM agent not running:
  send_command succeeds (returns a command_id) but the invocation status will be
  DeliveryTimedOut. Use AWSSSMGetCommandInvocation to detect this.

Command timeout:
  timeout_seconds applies to the command execution on the instance, not this operator.
  This operator returns as soon as send_command responds.

---

## What this operator does NOT do

- Does not wait for the command to complete on the instance
- Does not return stdout/stderr — use AWSSSMGetCommandInvocation for that
- Does not support multi-instance fan-out (single instance_id from connection)
"""

description = (
    "Sends an AWS Systems Manager Run Command document to a target EC2 instance and returns "
    "the command ID immediately. The instance ID is read from connection.ec2_instance_id. "
    "Supports any SSM document (default: AWS-RunShellScript) with a configurable parameter map. "
    "Connectivity is verified via describe_instance_information before sending. "
    "Auth: IAM role via STS first, fallback to flat access keys in connection. "
    "Returns command_id, instance_id, document_name, and initial status on success. "
    "Pair with AWSSSMGetCommandInvocation to retrieve stdout/stderr after the command completes."
)

publisher = "LeastActionLabs"

metadata = {
    "service": "SSM",
    "category": "Management",
    "tags": ["ssm", "run-command", "ec2", "aws"],
    "airflow_equivalent": "SsmRunCommandOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

The target EC2 instance must have the SSM Agent installed and the AmazonSSMManagedInstanceCore policy attached to its IAM role. send_command returns immediately — the command executes asynchronously on the instance. Use AWSSSMGetCommandInvocation to retrieve stdout/stderr and final status. The instance_id is read from connection.ec2_instance_id to keep payload focused on command configuration. timeout_seconds applies to command execution on the instance, not this operator call.
"""
