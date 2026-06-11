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

    log_info("task", "initialize", "auth_keys",
             f"Using explicit access key ending ...{access_key[-4:]}")

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

        log_info("task", "initialize", "building_client",
                 f"region={connection.get('region', 'us-east-1')}")

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
        payload = least_action_task_object.get("payload", {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                log_error("task", "run", "payload_parse_error", "Failed to parse payload as JSON")
                return {"status": "failed", "execution_type": "sync", "result": None,
                        "error": "Invalid payload format — expected flat JSON object"}

        cluster_name = payload.get("cluster_name")
        if not cluster_name:
            msg = "Missing required payload field: cluster_name"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        capacity_providers = payload.get("capacity_providers", [])
        tags = payload.get("tags", [])

        kwargs = {"clusterName": cluster_name}
        if capacity_providers:
            kwargs["capacityProviders"] = capacity_providers
        if tags:
            kwargs["tags"] = tags

        log_info("task", "run", "create_cluster", f"Creating ECS cluster '{cluster_name}'")
        resp = client.create_cluster(**kwargs)
        cluster = resp.get("cluster", {})

        result = {
            "cluster_name": cluster.get("clusterName"),
            "cluster_arn": cluster.get("clusterArn"),
            "status": cluster.get("status"),
        }
        log_info("task", "run", "cluster_created",
                 f"Cluster '{cluster_name}' created - ARN: {result['cluster_arn']}, "
                 f"Status: {result['status']}")

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
             "ECSCreateCluster is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "ECSCreateCluster completed",
        "output": run_details.get("result", {})
    }


def finish(least_action_task_object, client, completion_details, run_details):
    try:
        result = run_details.get("result", {})
        status = completion_details.get("status", "unknown")
        log_info("task", "finish", "final_status", f"Completed with status: {status}")
        if status == "success":
            log_info("task", "finish", "summary",
                     f"Cluster: {result.get('cluster_name')} | "
                     f"ARN: {result.get('cluster_arn')} | "
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
    "cluster_name": "my-ecs-cluster",
    "capacity_providers": [],
    "tags": []
}

prompt = (
    "Create an ECS cluster with the specified name. "
    "Payload must include cluster_name. capacity_providers and tags are optional. "
    "Calls create_cluster and returns cluster_name, cluster_arn, and status. "
    "Auth: IAM role via STS first, fall back to access keys from connection. "
    "The cluster is created immediately and returns ACTIVE status on success."
)

install_docs = """# AWSECSCreateCluster — Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": ["ecs:CreateCluster", "ecs:DescribeClusters"],
      "Resource": "*"
    }

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance — no connection keys needed       |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
| Session token | Optionally add aws_session_token in connection                |
"""

guide_docs = """# AWSECSCreateCluster — Operator Guide

## What it does

Creates an ECS cluster with the specified name. The cluster is available immediately
after creation with ACTIVE status. Supports optional capacity providers and resource tags.

Cluster creation itself is free — costs only occur when tasks or services are launched
within the cluster (EC2 instances for EC2 launch type, or Fargate per-second billing).

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
      "cluster_name": "my-ecs-cluster",
      "capacity_providers": [],
      "tags": []
    }

| Field               | Required | Description                                            |
|---------------------|----------|--------------------------------------------------------|
| cluster_name        | Yes      | Name for the new ECS cluster                           |
| capacity_providers  | No       | List of capacity provider names to associate           |
| tags                | No       | List of {key, value} tag dicts to attach to cluster    |

---

## Output (on success)

    {
      "cluster_name": "my-ecs-cluster",
      "cluster_arn": "arn:aws:ecs:us-east-1:123456789012:cluster/my-ecs-cluster",
      "status": "ACTIVE"
    }

---

## What this operator does NOT do

- Does not register task definitions or launch tasks
- Does not configure autoscaling or capacity provider strategies
- Does not delete the cluster — use AWSECSDeleteCluster for that
"""

description = (
    "Creates an AWS ECS cluster with the specified name and returns its ARN and status. "
    "Supports optional capacity providers and resource tags. Cluster creation is synchronous "
    "and the cluster is immediately ACTIVE on success. Cluster creation itself is free — "
    "costs only occur when tasks run inside it. "
    "Auth: IAM role via STS first, fallback to flat access keys in connection. "
    "Pair with AWSECSRegisterTaskDefinition and AWSECSRunTask to launch workloads, "
    "and AWSECSDeleteCluster to clean up when done."
)

publisher = "LeastActionLabs"

metadata = {
    "service": "ECS",
    "category": "Compute",
    "tags": ["ecs", "cluster", "fargate", "aws"],
    "airflow_equivalent": "EcsCreateClusterOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

ECS cluster creation is immediate — the cluster reaches ACTIVE state within seconds, no polling needed. A cluster is purely a logical grouping; no compute is provisioned at creation time. Actual capacity comes from EC2 Auto Scaling groups (EC2 launch type) or Fargate (serverless). Capacity providers must be registered separately after creation. Cluster creation itself is free — costs only occur when tasks or services run inside it.
"""

