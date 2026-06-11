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


def _build_client(connection):
    region = connection.get("region", "us-east-1")

    try:
        sts = boto3.client("sts", region_name=region)
        sts.get_caller_identity()
        log_info("task", "initialize", "auth_iam", "IAM role available - using instance profile")
        return boto3.client("ecs", region_name=region)
    except Exception as e:
        log_info("task", "initialize", "auth_iam_failed",
                 f"IAM role not available ({str(e)}) - falling back to access keys")

    access_key = connection.get("aws_access_key_id")
    secret_key = connection.get("aws_secret_access_key")
    session_token = connection.get("aws_session_token")

    if not (access_key and secret_key):
        raise RuntimeError(
            "No usable credentials: IAM role unavailable and "
            "aws_access_key_id/aws_secret_access_key not found in connection."
        )

    params = {
        "service_name": "ecs",
        "region_name": region,
        "aws_access_key_id": access_key,
        "aws_secret_access_key": secret_key,
    }
    if session_token:
        params["aws_session_token"] = session_token
    return boto3.client(**params)


def initialize(least_action_task_object):
    try:
        connection = least_action_task_object.get("connection", {})
        if isinstance(connection, str):
            connection = json.loads(connection)
        client = _build_ecs_client(connection)
        log_info("task", "initialize", "client_ready", "ECS client initialized")
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

        family = payload.get("family")
        if not family:
            msg = "Missing required payload field: family"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        container_definitions = payload.get("container_definitions")
        if not container_definitions:
            msg = "Missing required payload field: container_definitions"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        kwargs = {
            "family": family,
            "containerDefinitions": container_definitions,
        }

        # Optional fields
        for key, api_key in [
            ("task_role_arn", "taskRoleArn"),
            ("execution_role_arn", "executionRoleArn"),
            ("network_mode", "networkMode"),
            ("cpu", "cpu"),
            ("memory", "memory"),
        ]:
            if payload.get(key):
                kwargs[api_key] = payload[key]

        if payload.get("requires_compatibilities"):
            kwargs["requiresCompatibilities"] = payload["requires_compatibilities"]

        if payload.get("tags"):
            kwargs["tags"] = payload["tags"]

        log_info("task", "run", "register_task_definition",
                 f"Registering ECS task definition family '{family}'")
        resp = client.register_task_definition(**kwargs)
        td = resp.get("taskDefinition", {})

        result = {
            "task_definition_arn": td.get("taskDefinitionArn"),
            "family": td.get("family"),
            "revision": td.get("revision"),
            "status": td.get("status"),
        }
        log_info("task", "run", "task_definition_registered",
                 f"Task definition '{family}' registered - revision: {result['revision']}, "
                 f"ARN: {result['task_definition_arn']}")
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
             "ECSRegisterTaskDefinition is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "ECSRegisterTaskDefinition completed",
        "output": run_details.get("result", {})
    }


def finish(least_action_task_object, client, completion_details, run_details):
    try:
        result = run_details.get("result", {})
        status = completion_details.get("status", "unknown")
        log_info("task", "finish", "final_status", f"Completed with status: {status}")
        if status == "success":
            log_info("task", "finish", "summary",
                     f"TaskDef: {result.get('task_definition_arn')} | "
                     f"Revision: {result.get('revision')} | "
                     f"Status: {result.get('status')}")
        else:
            log_error("task", "finish", "operation_failed",
                      completion_details.get("message", "No message"))
        if client:
            try:
                client.close()
                log_info("task", "finish", "client_closed", "ECS boto3 client closed successfully")
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
    "family": "my-task-family",
    "container_definitions": [
        {
            "name": "my-container",
            "image": "amazon/amazon-ecs-sample",
            "cpu": 256,
            "memory": 512,
            "essential": True
        }
    ],
    "network_mode": "awsvpc",
    "requires_compatibilities": ["FARGATE"],
    "cpu": "256",
    "memory": "512",
    "execution_role_arn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
    "task_role_arn": "",
    "tags": []
}

prompt = (
    "Register a new ECS task definition revision. "
    "Payload must include family and container_definitions. "
    "Optional: task_role_arn, execution_role_arn, network_mode, cpu, memory, requires_compatibilities, tags. "
    "Calls register_task_definition and returns task_definition_arn, family, revision, and status (ACTIVE). "
    "Auth: IAM role via STS first, fall back to access keys from connection."
)

install_docs = """# AWSECSRegisterTaskDefinition — Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": ["ecs:RegisterTaskDefinition", "iam:PassRole"],
      "Resource": "*"
    }

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance — no connection keys needed       |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
| Session token | Optionally add aws_session_token in connection                |
"""

guide_docs = """# AWSECSRegisterTaskDefinition — Operator Guide

## What it does

Registers a new revision of an ECS task definition. Each call creates a new revision
(e.g. my-task-family:1, :2, etc.). The task definition is immediately ACTIVE after
registration and can be used with AWSECSRunTask.

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
      "family": "my-task-family",
      "container_definitions": [
        {
          "name": "my-container",
          "image": "amazon/amazon-ecs-sample",
          "cpu": 256,
          "memory": 512,
          "essential": true
        }
      ],
      "network_mode": "awsvpc",
      "requires_compatibilities": ["FARGATE"],
      "cpu": "256",
      "memory": "512",
      "execution_role_arn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
      "task_role_arn": "",
      "tags": []
    }

| Field                    | Required | Description                                              |
|--------------------------|----------|----------------------------------------------------------|
| family                   | Yes      | Task definition family name                              |
| container_definitions    | Yes      | List of container definition dicts                       |
| network_mode             | No       | Network mode: awsvpc, bridge, host, none                 |
| requires_compatibilities | No       | List: ["FARGATE"] or ["EC2"]                             |
| cpu                      | No       | Task-level CPU units (required for Fargate)              |
| memory                   | No       | Task-level memory in MiB (required for Fargate)          |
| execution_role_arn       | No       | IAM role ARN for ECS agent to pull images and push logs  |
| task_role_arn            | No       | IAM role ARN for the task containers                     |
| tags                     | No       | List of {key, value} tag dicts                           |

---

## Output (on success)

    {
      "task_definition_arn": "arn:aws:ecs:us-east-1:123456789012:task-definition/my-task-family:1",
      "family": "my-task-family",
      "revision": 1,
      "status": "ACTIVE"
    }

---

## What this operator does NOT do

- Does not launch tasks — use AWSECSRunTask for that
- Does not create clusters — use AWSECSCreateCluster for that
- Does not deregister old revisions — use AWSECSDeregisterTaskDefinition for that
"""

description = (
    "Registers a new revision of an AWS ECS task definition from container definitions and "
    "configuration provided in the payload. Supports optional task role, execution role, "
    "network mode, CPU/memory limits, Fargate compatibility, and tags. Each call increments "
    "the revision number (e.g. family:1, family:2). The new revision is immediately ACTIVE. "
    "Returns task_definition_arn, family, revision, and ACTIVE status on success. "
    "Auth: IAM role via STS first, fallback to flat access keys in connection. "
    "Use AWSECSRunTask to launch tasks from this definition, and AWSECSDeregisterTaskDefinition "
    "to retire old revisions."
)

publisher = "LeastActionLabs"
metadata = {
    "service": "ECS", "category": "Compute",
    "tags": ["ecs", "task-definition", "register", "fargate", "aws"],
    "airflow_equivalent": "EcsRegisterTaskDefinitionOperator"
}
version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

Task definitions are immutable once registered — to update, register a new revision (revisions auto-increment, e.g. `my-task:3`). The returned `task_definition_arn` includes the revision. For Fargate compatibility, set `requires_compatibilities: ["FARGATE"]`, `network_mode: "awsvpc"`, and specify `cpu`/`memory` at the task level (not just the container level). The `execution_role_arn` (needed to pull images from ECR and write logs to CloudWatch) is different from `task_role_arn` (permissions for the running container).
"""

