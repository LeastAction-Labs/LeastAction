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
            msg = "Missing required payload field: task_definition"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        cluster = payload.get("cluster", "default")
        launch_type = payload.get("launch_type", "FARGATE")
        count = payload.get("count", 1)
        network_configuration = payload.get("network_configuration", {})
        overrides = payload.get("overrides", {})

        kwargs = {
            "cluster": cluster,
            "taskDefinition": task_definition,
            "launchType": launch_type,
            "count": count,
        }
        if network_configuration:
            kwargs["networkConfiguration"] = network_configuration
        if overrides:
            kwargs["overrides"] = overrides

        log_info("task", "run", "run_task",
                 f"Running ECS task '{task_definition}' on cluster '{cluster}' "
                 f"with launchType='{launch_type}'")
        resp = client.run_task(**kwargs)

        failures = resp.get("failures", [])
        if failures:
            failure_msgs = [f"{f.get('arn', '')}: {f.get('reason', '')}" for f in failures]
            log_error("task", "run", "task_failures", f"ECS run_task failures: {failure_msgs}")
            return {"execution_type": "sync", "status": "failed",
                    "result": {"failures": failure_msgs}}

        tasks = resp.get("tasks", [])
        task_info = tasks[0] if tasks else {}
        result = {
            "task_arn": task_info.get("taskArn"),
            "cluster_arn": task_info.get("clusterArn"),
            "task_definition_arn": task_info.get("taskDefinitionArn"),
            "last_status": task_info.get("lastStatus"),
            "launch_type": task_info.get("launchType"),
        }
        log_info("task", "run", "task_started",
                 f"ECS task started - ARN: {result['task_arn']}, status: {result['last_status']}")
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
             "ECSRunTask is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "ECSRunTask completed",
        "output": run_details.get("result", {})
    }


def finish(least_action_task_object, client, completion_details, run_details):
    try:
        result = run_details.get("result", {})
        status = completion_details.get("status", "unknown")
        log_info("task", "finish", "final_status", f"Completed with status: {status}")
        if status == "success":
            log_info("task", "finish", "summary",
                     f"Task ARN: {result.get('task_arn')} | "
                     f"Status: {result.get('last_status')} | "
                     f"LaunchType: {result.get('launch_type')}")
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
    "cluster": "my-ecs-cluster",
    "task_definition": "my-task-family:1",
    "launch_type": "FARGATE",
    "count": 1,
    "network_configuration": {
        "awsvpcConfiguration": {
            "subnets": ["subnet-xxxxxxxxxxxxxxxxx"],
            "securityGroups": [],
            "assignPublicIp": "ENABLED"
        }
    },
    "overrides": {}
}

prompt = (
    "Run an ECS task on a cluster. "
    "Payload must include task_definition. cluster defaults to 'default', launch_type to 'FARGATE', count to 1. "
    "network_configuration is required for FARGATE tasks (awsvpcConfiguration with subnets). "
    "Calls run_task and returns task_arn, cluster_arn, task_definition_arn, last_status, and launch_type. "
    "Returns failed if the response contains failures (capacity or placement issues). "
    "Auth: IAM role via STS first, fall back to access keys from connection. "
    "Note: FARGATE tasks incur per-second compute costs — ensure tasks are short-lived or expected."
)

install_docs = """# AWSECSRunTask — Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "ecs:RunTask",
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

## Cost Warning

FARGATE tasks are billed per vCPU-second and GB-second of memory.
EC2 launch type uses pre-existing EC2 instances — cost depends on your cluster's EC2 capacity.
"""

guide_docs = """# AWSECSRunTask — Operator Guide

## What it does

Starts an ECS task on a specified cluster using run_task. Returns the task ARN and initial
status (usually PROVISIONING or PENDING) immediately — the task continues running
asynchronously after this operator completes.

This operator does NOT poll for task completion. It simply fires the task and returns.
To check final task status, use the ECS console or describe_tasks separately.

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
      "cluster": "my-ecs-cluster",
      "task_definition": "my-task-family:1",
      "launch_type": "FARGATE",
      "count": 1,
      "network_configuration": {
        "awsvpcConfiguration": {
          "subnets": ["subnet-xxxxxxxxxxxxxxxxx"],
          "securityGroups": [],
          "assignPublicIp": "ENABLED"
        }
      },
      "overrides": {}
    }

| Field                 | Required | Default    | Description                                        |
|-----------------------|----------|------------|----------------------------------------------------|
| task_definition       | Yes      | —          | Task definition family:revision or ARN             |
| cluster               | No       | "default"  | Cluster name or ARN to run the task on             |
| launch_type           | No       | "FARGATE"  | "FARGATE" or "EC2"                                 |
| count                 | No       | 1          | Number of task instances to launch                 |
| network_configuration | No       | {}         | Required for FARGATE — awsvpcConfiguration dict    |
| overrides             | No       | {}         | Container-level environment or command overrides   |

---

## Output (on success)

    {
      "task_arn": "arn:aws:ecs:us-east-1:123456789012:task/my-cluster/abc123",
      "cluster_arn": "arn:aws:ecs:us-east-1:123456789012:cluster/my-ecs-cluster",
      "task_definition_arn": "arn:aws:ecs:...:task-definition/my-task-family:1",
      "last_status": "PROVISIONING",
      "launch_type": "FARGATE"
    }

---

## Cost Warning

FARGATE tasks are billed per-second from the moment they start provisioning.
Even very short tasks (< 1 minute) incur a minimum charge.
For zero-cost testing of the operator itself, use EC2 launch type on an existing cluster
with idle EC2 capacity.

---

## Scenarios and Edge Cases

No subnets / network_configuration missing for FARGATE:
  run_task returns a failure with reason "No Container Instances were found in your cluster."
  Ensure awsvpcConfiguration includes at least one valid subnet.

Task placement failure (EC2):
  run_task returns failures with reason "No Container Instances were found."
  Ensure the cluster has running EC2 instances with sufficient capacity.

Task definition not found:
  AWS returns ClientException. Caught as ClientError, returned as status:failed.
"""

description = (
    "Starts an ECS task on a specified cluster using run_task. Accepts task_definition, "
    "cluster, launch_type (FARGATE or EC2), count, network_configuration, and optional overrides. "
    "Returns the task ARN, cluster ARN, task definition ARN, and initial status immediately — "
    "the task continues running asynchronously and this operator does not poll for completion. "
    "Returns status:failed if run_task returns any failure entries (capacity or placement errors). "
    "Auth: IAM role via STS first, fallback to flat access keys in connection. "
    "Note: FARGATE tasks incur per-second billing — ensure tasks are short-lived or expected. "
    "Pair with AWSECSRegisterTaskDefinition to define the task and AWSECSCreateCluster for the cluster."
)

publisher = "LeastActionLabs"
metadata = {
    "service": "ECS", "category": "Compute",
    "tags": ["ecs", "run-task", "fargate", "ec2", "aws"],
    "airflow_equivalent": "EcsRunTaskOperator"
}
version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

This operator does NOT wait for the ECS task to finish — it returns immediately after the task enters PROVISIONING/PENDING state. The `failures` array in the response is checked; non-empty failures return `status:failed`. For FARGATE launch type, `network_configuration` with `awsvpcConfiguration` (subnets + security groups) is required. For EC2 launch type, the cluster must have registered container instances with available capacity. To wait for task completion, poll `describe_tasks` separately using the returned `task_arn`.
"""

