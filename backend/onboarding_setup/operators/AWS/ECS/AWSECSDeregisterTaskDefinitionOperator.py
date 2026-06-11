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

        task_definition = payload.get("task_definition")
        if not task_definition:
            msg = "Missing required payload field: task_definition (family:revision or ARN)"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        log_info("task", "run", "deregister_task_definition",
                 f"Deregistering ECS task definition '{task_definition}'")
        resp = client.deregister_task_definition(taskDefinition=task_definition)
        td = resp.get("taskDefinition", {})

        result = {
            "task_definition_arn": td.get("taskDefinitionArn"),
            "family": td.get("family"),
            "revision": td.get("revision"),
            "status": td.get("status"),
        }
        log_info("task", "run", "task_definition_deregistered",
                 f"Task definition '{task_definition}' deregistered - status: {result['status']}")
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
             "ECSDeregisterTaskDefinition is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "ECSDeregisterTaskDefinition completed",
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
                     f"Family: {result.get('family')} | "
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
    "task_definition": "my-task-family:3"
}

prompt = (
    "Deregister an ECS task definition revision by family:revision or full ARN. "
    "Calls deregister_task_definition and returns task_definition_arn, family, revision, and status (INACTIVE). "
    "Auth: IAM role via STS first, fall back to access keys from connection."
)

install_docs = """# AWSECSDeregisterTaskDefinition — Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {"Effect": "Allow", "Action": ["ecs:DeregisterTaskDefinition"], "Resource": "*"}

## Auth Setup

| Method      | How                                                         |
|-------------|-------------------------------------------------------------|
| IAM role    | Attach role to EC2 instance — no connection keys needed     |
| Access keys | Set aws_access_key_id and aws_secret_access_key in connection |
"""

guide_docs = """# AWSECSDeregisterTaskDefinition — Operator Guide

## What it does

Deregisters a specific revision of an ECS task definition so it can no longer be used
to run new tasks. The task definition moves to INACTIVE status. Existing running tasks
that use the revision are not affected.

---

## Payload

    {"task_definition": "my-task-family:3"}

| Field           | Required | Description                                              |
|-----------------|----------|----------------------------------------------------------|
| task_definition | Yes      | Task definition family:revision or full ARN to deregister |

## Output

    {
      "task_definition_arn": "arn:aws:ecs:us-east-1:123456789012:task-definition/my-task-family:3",
      "family": "my-task-family",
      "revision": 3,
      "status": "INACTIVE"
    }

## Scenarios

Task definition not found: AWS returns ClientException. Caught as ClientError.
Task definition already INACTIVE: AWS returns ClientException — already deregistered.
"""

description = (
    "Deregisters a specific revision of an AWS ECS task definition so it can no longer be used "
    "to launch new tasks. Accepts a family:revision string or full task definition ARN. "
    "The deregistered revision transitions to INACTIVE status — running tasks using it are unaffected. "
    "Returns task_definition_arn, family, revision, and INACTIVE status on success. "
    "Auth: IAM role via STS first, fallback to flat access keys in connection. "
    "Pair with AWSECSRegisterTaskDefinition to register new revisions and AWSECSRunTask to launch tasks."
)

publisher = "LeastActionLabs"
metadata = {
    "service": "ECS", "category": "Compute",
    "tags": ["ecs", "task-definition", "deregister", "aws"],
    "airflow_equivalent": "EcsDeregisterTaskDefinitionOperator"
}
version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

Deregistered task definitions move to INACTIVE state immediately — existing running tasks using that definition are unaffected and continue to run. AWS retains deregistered definitions indefinitely; they are not deleted and still visible in the console. Pass the full `family:revision` identifier (e.g. `my-task:3`) — deregistering without a revision number is not supported. To clean up old revisions, iterate through revisions and deregister each individually.
"""

