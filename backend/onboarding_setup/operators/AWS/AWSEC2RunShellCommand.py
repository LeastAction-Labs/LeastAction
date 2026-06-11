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
import time
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

        instance_id = connection.get("ec2_instance_id")
        if not instance_id:
            raise ValueError("ec2_instance_id is required in connection")

        log_info("task", "initialize", "building_client",
                 f"region={connection.get('region', 'us-east-1')}, instance={instance_id}")

        client = _build_ssm_client(connection)
        desc = client.describe_instance_information(
            Filters=[{"Key": "InstanceIds", "Values": [instance_id]}]
        )
        items = desc.get("InstanceInformationList", [])
        if not items:
            raise RuntimeError(
                f"Instance {instance_id} not found in SSM — ensure SSM Agent is running "
                "and the instance has the AmazonSSMManagedInstanceCore policy."
            )
        ping = items[0].get("PingStatus", "Unknown")
        log_info("task", "initialize", "ssm_ping",
                 f"Instance {instance_id} SSM PingStatus: {ping}")
        if ping != "Online":
            raise RuntimeError(
                f"Instance {instance_id} SSM PingStatus is '{ping}', expected 'Online'."
            )
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
        instance_id = connection.get("ec2_instance_id")

        payload = least_action_task_object.get("payload", {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                log_error("task", "run", "payload_parse_error", "Failed to parse payload as JSON")
                return {"status": "failed", "execution_type": "async", "result": None,
                        "error": "Invalid payload format - expected flat JSON object"}

        command = payload.get("command")
        if not command:
            msg = "Missing required payload field: command"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "async", "status": "failed", "result": {"error": msg}}

        working_directory = payload.get("working_directory", "")
        timeout_seconds = int(payload.get("timeout_seconds", 3600))

        log_info("task", "run", "sending_command",
                 f"Sending shell command to instance {instance_id}")

        kwargs = {
            "InstanceIds": [instance_id],
            "DocumentName": "AWS-RunShellScript",
            "Parameters": {"commands": [command]},
            "TimeoutSeconds": timeout_seconds,
        }
        if working_directory:
            kwargs["Parameters"]["workingDirectory"] = [working_directory]

        response = client.send_command(**kwargs)
        command_id = response["Command"]["CommandId"]

        log_info("task", "run", "command_sent", f"Command ID: {command_id}")

        return {
            "execution_type": "async",
            "status": "pending",
            "result": {
                "command_id": command_id,
                "instance_id": instance_id,
            },
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "client_error", f"({error_code}) {error_msg}")
        return {"execution_type": "async", "status": "failed",
                "result": {"error": f"({error_code}) {error_msg}"}}
    except Exception as e:
        log_error("task", "run", "run_failed", f"Unexpected error: {str(e)}")
        return {"execution_type": "async", "status": "failed", "result": {"error": str(e)}}


def check_completion(least_action_task_object, client, run_details):
    try:
        command_id = run_details.get("result", {}).get("command_id")
        instance_id = run_details.get("result", {}).get("instance_id")

        if not command_id or not instance_id:
            return {"status": "failed", "message": "Missing command_id or instance_id", "output": None}

        response = client.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id,
        )
        status = response.get("StatusDetails", "Unknown")
        log_info("task", "check_completion", "status", f"Command {command_id} status: {status}")

        if status in ("Success",):
            return {
                "status": "success",
                "message": "Command completed successfully",
                "output": {
                    "command_id": command_id,
                    "status": status,
                    "stdout": response.get("StandardOutputContent", ""),
                    "stderr": response.get("StandardErrorContent", ""),
                    "exit_code": response.get("ResponseCode", 0),
                },
            }
        if status in ("Failed", "Cancelled", "TimedOut", "Undeliverable", "Terminated"):
            return {
                "status": "failed",
                "message": f"Command {status}",
                "output": {
                    "command_id": command_id,
                    "status": status,
                    "stdout": response.get("StandardOutputContent", ""),
                    "stderr": response.get("StandardErrorContent", ""),
                    "exit_code": response.get("ResponseCode", -1),
                },
            }
        return {"status": "pending", "message": f"Command is {status}", "output": None}

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        if error_code == "InvocationDoesNotExist":
            return {"status": "pending", "message": "Invocation not yet available", "output": None}
        log_error("task", "check_completion", "client_error", str(e))
        return {"status": "failed", "message": str(e), "output": None}
    except Exception as e:
        log_error("task", "check_completion", "error", str(e))
        return {"status": "failed", "message": str(e), "output": None}


def finish(least_action_task_object, client, completion_details, run_details):
    try:
        status = completion_details.get("status", "unknown")
        command_id = run_details.get("result", {}).get("command_id", "unknown")
        log_info("task", "finish", "final_status",
                 f"Command {command_id} completed with status: {status}")
        if status == "success":
            output = completion_details.get("output", {})
            log_info("task", "finish", "summary",
                     f"exit_code={output.get('exit_code')}, "
                     f"stdout_len={len(output.get('stdout', ''))}")
        else:
            log_error("task", "finish", "operation_failed",
                      completion_details.get("message", "No message"))
        if client:
            try:
                client.close()
                log_info("task", "finish", "client_closed", "SSM boto3 client closed successfully")
            except Exception as close_error:
                log_error("task", "finish", "client_close_error", f"Error closing client: {str(close_error)}")
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
    "ec2_instance_id": "i-0123456789abcdef0",
    "region": "us-east-1",
    }

payload = {
    "command": "echo hello && ls /tmp",
    "working_directory": "",
    "timeout_seconds": 3600
}

prompt = (
    "Run a shell command on an EC2 instance using SSM Run Command (AWS-RunShellScript document). "
    "Required connection fields: ec2_instance_id, region. Optional: aws_access_key_id, aws_secret_access_key, session_token. "
    "Required payload field: command (shell command string). Optional: working_directory, timeout_seconds (default 3600). "
    "Auth: IAM role via STS first, fallback to access keys from connection. "
    "Async execution: send_command returns a command_id, check_completion polls get_command_invocation until "
    "status is Success/Failed/Cancelled/TimedOut. "
    "Returns stdout, stderr, exit_code, and command_id on completion."
)

install_docs = """# AWSEC2RunShellCommand — Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "ssm:SendCommand",
        "ssm:GetCommandInvocation",
        "ssm:DescribeInstanceInformation"
      ],
      "Resource": "*"
    }

## EC2 Instance Requirements

The target EC2 instance must have:
- SSM Agent installed and running (pre-installed on Amazon Linux 2/2023, Ubuntu 16.04+)
- The AmazonSSMManagedInstanceCore IAM policy attached to its instance profile

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance — no connection keys needed       |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
| Session token | Optionally add session_token in connection                    |
"""

guide_docs = """# AWSEC2RunShellCommand — Operator Guide

## What it does

Sends a shell command to a specific EC2 instance via the SSM Run Command API using the
AWS-RunShellScript document. Polls for completion asynchronously and returns stdout, stderr,
and exit code on finish.

Useful for running maintenance scripts, deployments, health checks, or any ad-hoc shell
operation on an EC2 instance without requiring SSH access.

---

## Auth

1. IAM role — tried first via STS. Used automatically if available. No keys needed in connection.
2. Access keys — fallback to aws_access_key_id + aws_secret_access_key from connection.

---

## Connection

    {
      "ec2_instance_id": "i-0123456789abcdef0",
      "region": "us-east-1",
      "aws_access_key_id": "",    // optional — omit to use IAM role
      "aws_secret_access_key": "", // optional — omit to use IAM role
      "session_token": ""          // optional — for temporary credentials
    }

| Field                 | Required | Description                                       |
|-----------------------|----------|---------------------------------------------------|
| ec2_instance_id       | Yes      | The target EC2 instance ID                        |
| region                | Yes      | AWS region where the instance lives               |
| aws_access_key_id     | No       | Only needed if IAM role is not available          |
| aws_secret_access_key | No       | Only needed if IAM role is not available          |
| session_token         | No       | For temporary/assumed-role credentials            |

---

## Payload

    {
      "command": "echo hello && ls /tmp",
      "working_directory": "/home/ec2-user",
      "timeout_seconds": 3600
    }

| Field             | Required | Default | Description                                       |
|-------------------|----------|---------|---------------------------------------------------|
| command           | Yes      | —       | Shell command string to execute on the instance   |
| working_directory | No       | ""      | Working directory on the instance                 |
| timeout_seconds   | No       | 3600    | SSM command timeout in seconds (max 172800)       |

---

## Output (on success)

    {
      "command_id": "abc123",
      "status": "Success",
      "stdout": "hello\\n/tmp/...",
      "stderr": "",
      "exit_code": 0
    }

---

## Scenarios and Edge Cases

Instance not registered with SSM:
  initialize() raises RuntimeError with a clear message.
  Fix: install SSM Agent and attach AmazonSSMManagedInstanceCore to the instance profile.

SSM Agent offline:
  PingStatus will not be "Online". initialize() raises RuntimeError.

Command times out:
  Status becomes TimedOut. Returned as status:failed with stdout/stderr captured so far.

Non-zero exit code:
  The SSM command status will be "Failed" even if stderr is empty.
  Returned as status:failed with exit_code and stdout/stderr.
"""

description = """
Runs a shell command on an EC2 instance via AWS SSM Run Command (AWS-RunShellScript document).
Verifies the instance is SSM-reachable in initialize(), submits the command asynchronously,
then polls get_command_invocation in check_completion until the command reaches a terminal state.
Returns stdout, stderr, and exit code. Auth: IAM role via STS first, fallback to access keys.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "SSM, EC2",
    "category": "Compute",
    "tags": ["ec2", "ssm", "shell", "command", "run", "script", "aws"],
    "airflow_equivalent": "SSHOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

The target EC2 instance must have SSM Agent installed and the AmazonSSMManagedInstanceCore IAM policy attached. initialize() proactively checks SSM reachability (PingStatus must be Online) — if the instance is not registered or the agent is offline, the task fails immediately with a clear error before the command is sent. The ec2_instance_id is read from connection (not payload) so the same operator can be reused with different commands against the same instance. session_token key is aws_session_token (not session_token).
"""
