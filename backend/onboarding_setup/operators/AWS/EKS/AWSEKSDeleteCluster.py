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

codeblock = {"main.py": """
import json
import time
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from src.common.logger.logger import log_info, log_error


def _build_client(connection):
    region = connection.get("region", "us-east-1")

    try:
        sts = boto3.client("sts", region_name=region)
        sts.get_caller_identity()
        log_info("task", "initialize", "auth_iam", "IAM role available - using instance profile")
        return boto3.client("eks", region_name=region)
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
        "service_name": "eks",
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

        client = _build_eks_client(connection)
        client.list_clusters(maxResults=1)
        log_info("task", "initialize", "connectivity_ok",
                 "EKS client initialized and verified")
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
            log_info("task", "run", "payload_unwrapped", "Unwrapped payload data envelope")

        cluster_name = payload.get("cluster_name")
        if not cluster_name:
            msg = "Missing required payload field: cluster_name"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        log_info("task", "run", "deleting_cluster",
                 f"Deleting EKS cluster '{cluster_name}'")

        client.delete_cluster(name=cluster_name)

        log_info("task", "run", "delete_initiated",
                 f"EKS cluster '{cluster_name}' delete initiated, polling every 30s until gone...")

        while True:
            try:
                desc = client.describe_cluster(name=cluster_name)
                status = desc["cluster"]["status"]
                log_info("task", "run", "polling_cluster_status",
                         f"Cluster '{cluster_name}' status: {status}")
                time.sleep(30)
            except ClientError as e:
                if e.response["Error"]["Code"] == "ResourceNotFoundException":
                    log_info("task", "run", "cluster_gone",
                             f"Cluster '{cluster_name}' no longer exists - deletion complete")
                    break
                raise

        log_info("task", "run", "delete_complete",
                 f"EKS cluster '{cluster_name}' successfully deleted")

        return {
            "execution_type": "sync",
            "status": "success",
            "result": {
                "cluster_name": cluster_name,
                "status": "DELETED"
            }
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "client_error", f"({error_code}) {error_msg}")
        return {"execution_type": "sync", "status": "failed",
                "result": {"error": f"({error_code}) {error_msg}"}}
    except BotoCoreError as e:
        log_error("task", "run", "transport_error", f"BotoCoreError: {str(e)}")
        return {"execution_type": "sync", "status": "failed",
                "result": {"error": f"Transport error: {str(e)}"}}
    except Exception as e:
        log_error("task", "run", "run_failed", f"Unexpected error: {str(e)}")
        return {"execution_type": "sync", "status": "failed", "result": {"error": str(e)}}


def check_completion(least_action_task_object, client, run_details):
    log_info("task", "check_completion", "sync_complete",
             "EKS DeleteCluster is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "EKS cluster deletion completed",
        "output": run_details.get("result", {})
    }


def finish(least_action_task_object, client, completion_details, run_details):
    try:
        task_laui = least_action_task_object.get("laui", "unknown")
        status = completion_details.get("status", "unknown")
        log_info("task", "finish", "final_status",
                 f"Task {task_laui} completed with status: {status}")
        if status == "success":
            output = completion_details.get("output", {})
            log_info("task", "finish", "delete_summary",
                     f"Cluster {output.get('cluster_name')} status={output.get('status')}")
        else:
            log_error("task", "finish", "operation_failed",
                      completion_details.get("message", "No message"))
        if client:
            try:
                client.close()
                log_info("task", "finish", "client_closed", "EKS boto3 client closed successfully")
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
}

payload = {
    "cluster_name": "my-eks-cluster"
}

prompt = (
    "Create an operator that deletes an Amazon EKS cluster and waits until it is fully deleted. "
    "Required payload field: cluster_name. "
    "Auth: try IAM role via STS first; if unavailable, fall back to access keys from connection. "
    "After calling delete_cluster, poll describe_cluster every 30 seconds. "
    "When ResourceNotFoundException is raised, the cluster is gone - return status:success. "
    "Return cluster_name and status=DELETED on success. "
    "Catch all AWS errors and return them as status:failed - never raise."
)

install_docs = """# AWSEKSDeleteCluster - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "eks:DeleteCluster",
        "eks:DescribeCluster",
        "eks:ListClusters"
      ],
      "Resource": "*"
    }
"""

guide_docs = """# AWSEKSDeleteCluster - Operator Guide

## What it does

Deletes an Amazon EKS cluster and polls synchronously every 30 seconds until the cluster is
fully deleted (ResourceNotFoundException is raised). All nodegroups and Fargate profiles must
be deleted before the cluster can be removed.

---

## Payload

    { "cluster_name": "my-eks-cluster" }

| Field        | Required | Description                          |
|--------------|----------|--------------------------------------|
| cluster_name | Yes      | Name of the EKS cluster to delete    |

---

## Output (on success)

    {
      "cluster_name": "my-eks-cluster",
      "status": "DELETED"
    }

---

## What this operator does NOT do

- Does not delete nodegroups or Fargate profiles first (delete those first)
- Does not delete VPC, subnets, or security groups created for the cluster
"""

description = """
Deletes an Amazon EKS cluster and polls every 30 seconds until ResourceNotFoundException confirms
deletion is complete. All nodegroups and Fargate profiles must be deleted first. Auth: IAM role
via STS first, fallback to access keys. Returns cluster_name and status=DELETED on success.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "EKS",
    "category": "Compute",
    "tags": ["eks", "kubernetes", "cluster", "delete", "aws"],
    "airflow_equivalent": "EksDeleteClusterOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

All node groups and Fargate profiles must be deleted before the cluster - AWS returns `ResourceInUseException` otherwise. Deletion completes when `describe_cluster` raises `ResourceNotFoundException`. The VPC, subnets, and security groups created for the cluster are NOT deleted - clean those up separately.
"""

