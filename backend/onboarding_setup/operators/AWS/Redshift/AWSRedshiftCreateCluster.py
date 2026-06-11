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


def _build_redshift_client(connection: dict):
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
        return session.client("redshift")

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
        return session.client("redshift")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info("task", "initialize", "auth_default",
             "Using default AWS credential chain (instance profile / ECS task role / env / config)")
    return boto3.Session(region_name=region).client("redshift")


def initialize(least_action_task_object):
    try:
        connection = least_action_task_object.get("connection", {})
        if isinstance(connection, str):
            connection = json.loads(connection)

        log_info("task", "initialize", "building_client",
                 f"region={connection.get('region', 'us-east-1')}")

        client = _build_redshift_client(connection)
        client.describe_clusters(MaxRecords=20)
        log_info("task", "initialize", "connectivity_ok",
                 "Redshift client initialized and verified")
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

        cluster_id = payload.get("cluster_identifier")
        node_type = payload.get("node_type")
        master_username = payload.get("master_username")
        master_password = payload.get("master_password")

        missing = []
        if not cluster_id:
            missing.append("cluster_identifier")
        if not node_type:
            missing.append("node_type")
        if not master_username:
            missing.append("master_username")
        if not master_password:
            missing.append("master_password")
        if missing:
            msg = f"Missing required payload fields: {missing}"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "async", "status": "failed", "result": {"error": msg}}

        poll_interval = int(payload.get("poll_interval_seconds", 30))

        params = {
            "ClusterIdentifier": cluster_id,
            "NodeType": node_type,
            "MasterUsername": master_username,
            "MasterUserPassword": master_password,
        }
        if "cluster_type" in payload:
            params["ClusterType"] = payload["cluster_type"]
        if "number_of_nodes" in payload:
            params["NumberOfNodes"] = int(payload["number_of_nodes"])
        if "db_name" in payload:
            params["DBName"] = payload["db_name"]
        if "cluster_subnet_group_name" in payload:
            params["ClusterSubnetGroupName"] = payload["cluster_subnet_group_name"]
        if "vpc_security_group_ids" in payload:
            params["VpcSecurityGroupIds"] = payload["vpc_security_group_ids"]
        if "cluster_parameter_group_name" in payload:
            params["ClusterParameterGroupName"] = payload["cluster_parameter_group_name"]
        if "iam_roles" in payload:
            params["IamRoles"] = payload["iam_roles"]
        if "tags" in payload and isinstance(payload["tags"], dict):
            params["Tags"] = [{"Key": k, "Value": v} for k, v in payload["tags"].items()]

        log_info("task", "run", "creating_cluster",
                 f"Creating Redshift cluster '{cluster_id}' with node_type={node_type}")
        client.create_cluster(**params)

        while True:
            resp = client.describe_clusters(ClusterIdentifier=cluster_id)
            clusters = resp.get("Clusters", [])
            if not clusters:
                return {
                    "execution_type": "async",
                    "status": "failed",
                    "result": {"error": f"Cluster '{cluster_id}' not found after creation"}
                }
            cluster = clusters[0]
            status = cluster.get("ClusterStatus")
            log_info("task", "run", "polling_status",
                     f"Cluster '{cluster_id}' status: {status}")
            if status == "available":
                return {
                    "execution_type": "async",
                    "status": "success",
                    "result": {
                        "cluster_identifier": cluster_id,
                        "cluster_status": status,
                        "endpoint": cluster.get("Endpoint", {}).get("Address"),
                        "port": cluster.get("Endpoint", {}).get("Port"),
                    }
                }
            if status not in {"creating", "available"}:
                return {
                    "execution_type": "async",
                    "status": "failed",
                    "result": {
                        "cluster_identifier": cluster_id,
                        "cluster_status": status,
                        "error": f"Unexpected terminal status: {status}",
                    }
                }
            time.sleep(poll_interval)

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "client_error", f"({error_code}) {error_msg}")
        return {"execution_type": "async", "status": "failed",
                "result": {"error": f"({error_code}) {error_msg}"}}
    except BotoCoreError as e:
        log_error("task", "run", "transport_error", f"BotoCoreError: {str(e)}")
        return {"execution_type": "async", "status": "failed",
                "result": {"error": f"Transport error: {str(e)}"}}
    except Exception as e:
        log_error("task", "run", "run_failed", f"Unexpected error: {str(e)}")
        return {"execution_type": "async", "status": "failed", "result": {"error": str(e)}}


def check_completion(least_action_task_object, client, run_details):
    try:
        if run_details.get("status") in ("success", "failed"):
            return {
                "status": run_details["status"],
                "message": "Redshift cluster creation completed",
                "output": run_details.get("result", {})
            }
        cluster_id = run_details.get("result", {}).get("cluster_identifier")
        resp = client.describe_clusters(ClusterIdentifier=cluster_id)
        clusters = resp.get("Clusters", [])
        if not clusters:
            return {"status": "failed", "message": f"Cluster '{cluster_id}' not found", "output": {}}
        cluster = clusters[0]
        status = cluster.get("ClusterStatus")
        log_info("task", "check_completion", "polling_status",
                 f"Cluster '{cluster_id}' status: {status}")
        if status == "available":
            return {
                "status": "success",
                "message": "Cluster is available",
                "output": {
                    "cluster_identifier": cluster_id,
                    "cluster_status": status,
                    "endpoint": cluster.get("Endpoint", {}).get("Address"),
                    "port": cluster.get("Endpoint", {}).get("Port"),
                }
            }
        if status == "creating":
            return {"status": "pending", "message": "Cluster is being created",
                    "output": {"cluster_status": status}}
        return {"status": "failed", "message": f"Unexpected status: {status}",
                "output": {"cluster_status": status}}
    except Exception as e:
        log_error("task", "check_completion", "error", f"Error: {str(e)}")
        return {"status": "failed", "message": str(e), "output": None}


def finish(least_action_task_object, client, completion_details, run_details):
    try:
        task_laui = least_action_task_object.get("laui", "unknown")
        status = completion_details.get("status", "unknown")
        log_info("task", "finish", "final_status",
                 f"Task {task_laui} completed with status: {status}")
        if status == "success":
            output = completion_details.get("output", {})
            log_info("task", "finish", "cluster_summary",
                     f"Cluster {output.get('cluster_identifier')} "
                     f"status={output.get('cluster_status')} "
                     f"endpoint={output.get('endpoint')}")
        else:
            log_error("task", "finish", "operation_failed",
                      completion_details.get("message", "No message"))
        if client:
            try:
                client.close()
                log_info("task", "finish", "client_closed", "Redshift boto3 client closed successfully")
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
    "cluster_identifier": "my-redshift-cluster",
    "node_type": "dc2.large",
    "master_username": "admin",
    "master_password": "MyPassword123!",
}

prompt = (
    "Create an operator that creates an Amazon Redshift cluster and polls every 30 seconds until "
    "it reaches 'available' status. "
    "Required payload: cluster_identifier, node_type, master_username, master_password. "
    "Optional: cluster_type, number_of_nodes, db_name, cluster_subnet_group_name, "
    "vpc_security_group_ids, cluster_parameter_group_name, iam_roles, tags (dict). "
    "Auth: try IAM role via STS first; if unavailable, fall back to access keys from connection. "
    "Return cluster_identifier, cluster_status, endpoint, port. "
    "Catch all AWS errors and return them as status:failed - never raise."
)

install_docs = """# AWSRedshiftCreateCluster - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "redshift:CreateCluster",
        "redshift:DescribeClusters"
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

guide_docs = """# AWSRedshiftCreateCluster - Operator Guide

## What it does

Creates an Amazon Redshift cluster and polls every 30 seconds until it reaches 'available' status.
Equivalent to Airflow's RedshiftCreateClusterOperator.

---

## Auth

1. IAM role - tried first via STS. Used automatically if available. No keys needed in connection.
2. Access keys - fallback to aws_access_key_id + aws_secret_access_key from connection.

---

## Connection

    {
      "region": "us-east-1"
    }

Optional fields (only needed if IAM role is not available):

| Field                  | Description                          |
|------------------------|--------------------------------------|
| aws_access_key_id      | AWS access key ID                    |
| aws_secret_access_key  | AWS secret access key                |
| aws_session_token      | Session token for temporary creds    |

---

## Payload

    {
      "cluster_identifier": "my-redshift-cluster",
      "node_type": "dc2.large",
      "master_username": "admin",
      "master_password": "MyPassword123!"
    }

| Field                        | Required | Description                                             |
|------------------------------|----------|---------------------------------------------------------|
| cluster_identifier           | Yes      | Unique cluster name                                     |
| node_type                    | Yes      | Node type (e.g. dc2.large, ra3.xlplus)                 |
| master_username              | Yes      | Admin username                                          |
| master_password              | Yes      | Admin password                                          |
| cluster_type                 | No       | single-node or multi-node (default: single-node)        |
| number_of_nodes              | No       | Number of nodes (required for multi-node)               |
| db_name                      | No       | Initial database name (default: dev)                    |
| cluster_subnet_group_name    | No       | VPC subnet group name                                   |
| vpc_security_group_ids       | No       | List of VPC security group IDs                          |
| cluster_parameter_group_name | No       | Parameter group name                                    |
| iam_roles                    | No       | List of IAM role ARNs to attach                        |
| tags                         | No       | Dict of tag key-value pairs                             |
| poll_interval_seconds        | No       | Polling interval in seconds (default: 30)               |

---

## Output (on success)

    {
      "cluster_identifier": "my-redshift-cluster",
      "cluster_status": "available",
      "endpoint": "my-redshift-cluster.abc123.us-east-1.redshift.amazonaws.com",
      "port": 5439
    }

---

## What this operator does NOT do

- Does not load data or run SQL — use AWSRedshiftDataExecuteSQL for that
- Does not enable enhanced VPC routing or encryption unless passed in params
"""

description = """
Creates an Amazon Redshift cluster and polls every 30 seconds until 'available'.
Equivalent to Airflow's RedshiftCreateClusterOperator. Required: cluster_identifier, node_type,
master_username, master_password. Optional: cluster_type, number_of_nodes, db_name, subnet group,
VPC security groups, parameter group, IAM roles, tags. Auth: IAM role via STS first, fallback to
access keys. Returns cluster_identifier, cluster_status, endpoint, port.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "Redshift",
    "category": "Data Warehouse",
    "tags": ["redshift", "cluster", "aws", "create", "data warehouse"],
    "airflow_equivalent": "RedshiftCreateClusterOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

Cluster creation takes 5-15 minutes. `cluster_type` defaults to `single-node` — for `multi-node` you must set `number_of_nodes >= 2`. `master_password` must be at least 8 characters with mixed case, numbers, and symbols. The cluster is not queryable until it reaches `available` state. `iam_roles` enables the cluster to access S3, Glue, and other AWS services from within SQL (e.g. COPY/UNLOAD commands).
"""

