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
        nodegroup_name = payload.get("nodegroup_name")
        node_role = payload.get("node_role")
        subnets = payload.get("subnets")

        missing = []
        if not cluster_name:
            missing.append("cluster_name")
        if not nodegroup_name:
            missing.append("nodegroup_name")
        if not node_role:
            missing.append("node_role")
        if not subnets:
            missing.append("subnets")
        if missing:
            msg = f"Missing required payload fields: {missing}"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        scaling_config = payload.get("scaling_config", {"minSize": 1, "maxSize": 2, "desiredSize": 1})
        instance_types = payload.get("instance_types", ["t3.medium"])
        ami_type = payload.get("ami_type", "AL2023_x86_64_STANDARD")
        capacity_type = payload.get("capacity_type", "ON_DEMAND")
        tags = payload.get("tags", {})

        create_params = {
            "clusterName": cluster_name,
            "nodegroupName": nodegroup_name,
            "nodeRole": node_role,
            "subnets": subnets,
            "scalingConfig": scaling_config,
            "instanceTypes": instance_types,
            "amiType": ami_type,
            "capacityType": capacity_type,
        }
        if tags:
            create_params["tags"] = tags

        log_info("task", "run", "creating_nodegroup",
                 f"Creating EKS nodegroup '{nodegroup_name}' on cluster '{cluster_name}'")

        client.create_nodegroup(**create_params)

        log_info("task", "run", "nodegroup_creating",
                 f"Nodegroup '{nodegroup_name}' creation initiated, polling every 30s for ACTIVE state...")

        terminal_fail_states = {"CREATE_FAILED", "DEGRADED", "DELETE_FAILED"}
        while True:
            desc = client.describe_nodegroup(clusterName=cluster_name, nodegroupName=nodegroup_name)
            status = desc["nodegroup"]["status"]
            log_info("task", "run", "polling_nodegroup_status",
                     f"Nodegroup '{nodegroup_name}' status: {status}")
            if status == "ACTIVE":
                break
            if status in terminal_fail_states:
                health = desc["nodegroup"].get("health", {})
                return {
                    "execution_type": "sync",
                    "status": "failed",
                    "result": {
                        "error": f"Nodegroup ended in state: {status}",
                        "cluster_name": cluster_name,
                        "nodegroup_name": nodegroup_name,
                        "status": status,
                        "health": health
                    }
                }
            time.sleep(30)

        nodegroup_info = desc["nodegroup"]
        log_info("task", "run", "nodegroup_active",
                 f"EKS nodegroup '{nodegroup_name}' is ACTIVE")

        return {
            "execution_type": "sync",
            "status": "success",
            "result": {
                "cluster_name": cluster_name,
                "nodegroup_name": nodegroup_name,
                "status": "ACTIVE",
                "arn": nodegroup_info.get("nodegroupArn"),
                "instance_types": nodegroup_info.get("instanceTypes"),
                "scaling_config": nodegroup_info.get("scalingConfig")
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
             "EKS CreateNodegroup is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "EKS nodegroup creation completed",
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
            log_info("task", "finish", "nodegroup_summary",
                     f"Nodegroup {output.get('nodegroup_name')} on cluster {output.get('cluster_name')} "
                     f"status={output.get('status')}")
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
    "cluster_name": "my-eks-cluster",
    "nodegroup_name": "my-nodegroup",
    "node_role": "arn:aws:iam::123456789012:role/EKSNodeRole",
    "subnets": ["subnet-abc123", "subnet-def456"]
}

prompt = (
    "Create an operator that creates an EKS managed nodegroup and waits for it to become ACTIVE. "
    "Required payload fields: cluster_name, nodegroup_name, node_role (IAM role ARN), subnets (list). "
    "Optional: scaling_config (default {minSize:1, maxSize:2, desiredSize:1}), "
    "instance_types (default ['t3.medium']), ami_type (default 'AL2_x86_64'), "
    "capacity_type (default 'ON_DEMAND'), tags (dict). "
    "Auth: try IAM role via STS first; if unavailable, fall back to access keys from connection. "
    "After calling create_nodegroup, poll describe_nodegroup every 30 seconds until status is ACTIVE. "
    "If status is CREATE_FAILED, DEGRADED, or DELETE_FAILED, return status:failed. "
    "Return cluster_name, nodegroup_name, status, arn, instance_types, scaling_config on success. "
    "Catch all AWS errors and return them as status:failed - never raise."
)

install_docs = """# AWSEKSCreateNodegroup - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "eks:CreateNodegroup",
        "eks:DescribeNodegroup",
        "eks:ListClusters",
        "iam:PassRole"
      ],
      "Resource": "*"
    }

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance - no connection keys needed       |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
| Session token | Optionally add aws_session_token in connection                |
"""

guide_docs = """# AWSEKSCreateNodegroup - Operator Guide

## What it does

Creates an Amazon EKS managed nodegroup on an existing cluster and polls synchronously every
30 seconds until the nodegroup reaches ACTIVE status. Nodegroup creation typically takes 5-10 minutes.

---

## Auth

1. IAM role - tried first via STS. Used automatically if available. No keys needed in connection.
2. Access keys - fallback to aws_access_key_id + aws_secret_access_key from connection.

---

## Connection

    {
      "region": "us-east-1",
      "aws_access_key_id": "AKIA...",    //optional - omit to use IAM role
      "aws_secret_access_key": "...",    //optional - omit to use IAM role
      "aws_session_token": ""            //optional - for temporary credentials
    }

---

## Payload

    {
      "cluster_name": "my-eks-cluster",
      "nodegroup_name": "my-nodegroup",
      "node_role": "arn:aws:iam::123456789012:role/EKSNodeRole",
      "subnets": ["subnet-abc123", "subnet-def456"]
    }

| Field          | Required | Description                                                      |
|----------------|----------|------------------------------------------------------------------|
| cluster_name   | Yes      | Name of the EKS cluster to add the nodegroup to                  |
| nodegroup_name | Yes      | Name for the new nodegroup                                       |
| node_role      | Yes      | IAM role ARN for the EC2 worker nodes                            |
| subnets        | Yes      | List of subnet IDs for the nodegroup                             |
| scaling_config | No       | {minSize, maxSize, desiredSize} (default: 1/2/1)                 |
| instance_types | No       | List of EC2 instance types (default: ['t3.medium'])              |
| ami_type       | No       | AMI type (default: AL2_x86_64)                                   |
| capacity_type  | No       | ON_DEMAND or SPOT (default: ON_DEMAND)                           |
| tags           | No       | Dict of tag key-value pairs                                      |

---

## Output (on success)

    {
      "cluster_name": "my-eks-cluster",
      "nodegroup_name": "my-nodegroup",
      "status": "ACTIVE",
      "arn": "arn:aws:eks:...",
      "instance_types": ["t3.medium"],
      "scaling_config": {"minSize": 1, "maxSize": 2, "desiredSize": 1}
    }

---

## What this operator does NOT do

- Does not create the EKS cluster (use AWSEKSCreateCluster)
- Does not configure auto-scaling policies
- Does not install node-level add-ons
"""

description = """
Creates an Amazon EKS managed nodegroup on an existing EKS cluster and polls every 30 seconds
until ACTIVE status. Nodegroup creation takes 5-10 minutes. Required: cluster_name,
nodegroup_name, node_role, subnets. Optional: scaling_config, instance_types, ami_type,
capacity_type, tags. Auth: IAM role via STS first, fallback to access keys. Returns cluster_name,
nodegroup_name, status, arn, instance_types, and scaling_config on success.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "EKS",
    "category": "Compute",
    "tags": ["eks", "kubernetes", "nodegroup", "ec2", "aws"],
    "airflow_equivalent": "EksCreateNodegroupOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

The `node_role` must have `AmazonEKSWorkerNodePolicy`, `AmazonEKS_CNI_Policy`, and `AmazonEC2ContainerRegistryReadOnly` attached. Nodegroup creation takes 3-5 minutes. `capacity_type` SPOT reduces cost by 70-90% but instances can be interrupted - only use SPOT for fault-tolerant workloads. `subnets` should be private subnets for production node groups.
"""

