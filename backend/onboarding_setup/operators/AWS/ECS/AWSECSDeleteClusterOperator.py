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

        cluster = payload.get("cluster")
        if not cluster:
            msg = "Missing required payload field: cluster (name or ARN)"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        log_info("task", "run", "delete_cluster", f"Deleting ECS cluster '{cluster}'")
        resp = client.delete_cluster(cluster=cluster)
        cluster_info = resp.get("cluster", {})

        result = {
            "cluster_name": cluster_info.get("clusterName"),
            "cluster_arn": cluster_info.get("clusterArn"),
            "status": cluster_info.get("status"),
        }
        log_info("task", "run", "cluster_deleted",
                 f"Cluster '{cluster}' deleted - status: {result['status']}")
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
             "ECSDeleteCluster is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "ECSDeleteCluster completed",
        "output": run_details.get("result", {})
    }


def finish(least_action_task_object, client, completion_details, run_details):
    try:
        result = run_details.get("result", {})
        status = completion_details.get("status", "unknown")
        log_info("task", "finish", "final_status", f"Completed with status: {status}")
        if status == "success":
            log_info("task", "finish", "summary",
                     f"Cluster: {result.get('cluster_name')} | Status: {result.get('status')}")
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

connection = {"region": "us-east-1"}
payload = {"cluster": "my-ecs-cluster"}

prompt = (
    "Delete an ECS cluster by name or ARN. Cluster must have no running tasks or active services. "
    "Calls delete_cluster and returns cluster_name, cluster_arn, and final status (INACTIVE). "
    "Auth: IAM role via STS first, fall back to access keys from connection."
)

install_docs = """# AWSECSDeleteCluster — Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {"Effect": "Allow", "Action": ["ecs:DeleteCluster"], "Resource": "*"}

## Auth Setup

| Method      | How                                                         |
|-------------|-------------------------------------------------------------|
| IAM role    | Attach role to EC2 instance — no connection keys needed     |
| Access keys | Set aws_access_key_id and aws_secret_access_key in connection |
"""

guide_docs = """# AWSECSDeleteCluster — Operator Guide

## What it does

Deletes an ECS cluster by name or ARN. The cluster must have no running or pending tasks
and no active services before deletion is allowed. Returns INACTIVE status on success.

---

## Payload

    {"cluster": "my-ecs-cluster"}

| Field   | Required | Description                        |
|---------|----------|------------------------------------|
| cluster | Yes      | Cluster name or full ARN to delete |

## Output

    {"cluster_name": "my-ecs-cluster", "cluster_arn": "arn:aws:ecs:...", "status": "INACTIVE"}

## Scenarios

Cluster has running tasks: AWS returns ClusterContainsTasksException. Caught as ClientError.
Cluster does not exist: AWS returns ClusterNotFoundException. Caught as ClientError.
"""

description = (
    "Deletes an AWS ECS cluster by name or ARN. The cluster must have no running tasks "
    "or active services — AWS will reject the call otherwise with ClusterContainsTasksException. "
    "Returns cluster_name, cluster_arn, and INACTIVE status on success. "
    "Auth: IAM role via STS first, fallback to flat access keys in connection. "
    "Typically used as the final cleanup step after AWSECSRunTask completes."
)

publisher = "LeastActionLabs"
metadata = {
    "service": "ECS", "category": "Compute",
    "tags": ["ecs", "cluster", "delete", "aws"],
    "airflow_equivalent": "EcsDeleteClusterOperator"
}
version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

All services and running tasks must be stopped before a cluster can be deleted — AWS returns `ClusterContainsServicesException` or `ClusterContainsTasksException` otherwise. The cluster enters INACTIVE state immediately on successful deletion. Registered container instances (EC2 launch type) are not terminated by this operator — deregister or terminate them separately.
"""

