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
        if not cluster_id:
            msg = "Missing required payload field: cluster_identifier"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "async", "status": "failed", "result": {"error": msg}}

        poll_interval = int(payload.get("poll_interval_seconds", 15))
        skip_final_snapshot = bool(payload.get("skip_final_cluster_snapshot", True))

        params = {
            "ClusterIdentifier": cluster_id,
            "SkipFinalClusterSnapshot": skip_final_snapshot,
        }
        if not skip_final_snapshot:
            final_snapshot_id = payload.get("final_cluster_snapshot_identifier")
            if final_snapshot_id:
                params["FinalClusterSnapshotIdentifier"] = final_snapshot_id

        log_info("task", "run", "deleting_cluster",
                 f"Deleting Redshift cluster '{cluster_id}' "
                 f"(skip_final_snapshot={skip_final_snapshot})")

        while True:
            try:
                client.delete_cluster(**params)
                log_info("task", "run", "delete_accepted",
                         "Delete request accepted, polling for completion")
                break
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                if error_code == "InvalidClusterState":
                    log_info("task", "run", "cluster_busy",
                             f"Cluster busy (InvalidClusterState), retrying in {poll_interval}s...")
                    time.sleep(poll_interval)
                    continue
                raise

        while True:
            try:
                resp = client.describe_clusters(ClusterIdentifier=cluster_id)
                clusters = resp.get("Clusters", [])
                if not clusters:
                    log_info("task", "run", "cluster_deleted",
                             f"Cluster '{cluster_id}' no longer found — deletion complete")
                    return {
                        "execution_type": "async",
                        "status": "success",
                        "result": {
                            "cluster_identifier": cluster_id,
                            "cluster_status": "deleted",
                        }
                    }
                status = clusters[0].get("ClusterStatus")
                log_info("task", "run", "polling_status",
                         f"Cluster '{cluster_id}' status: {status}")
                if status not in {"deleting", "final-snapshot"}:
                    return {
                        "execution_type": "async",
                        "status": "failed",
                        "result": {
                            "cluster_identifier": cluster_id,
                            "cluster_status": status,
                            "error": f"Unexpected terminal status: {status}",
                        }
                    }
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                if error_code == "ClusterNotFound":
                    log_info("task", "run", "cluster_deleted",
                             f"Cluster '{cluster_id}' not found — deletion complete")
                    return {
                        "execution_type": "async",
                        "status": "success",
                        "result": {
                            "cluster_identifier": cluster_id,
                            "cluster_status": "deleted",
                        }
                    }
                raise
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
                "message": "Redshift cluster deletion completed",
                "output": run_details.get("result", {})
            }
        cluster_id = run_details.get("result", {}).get("cluster_identifier")
        try:
            resp = client.describe_clusters(ClusterIdentifier=cluster_id)
            clusters = resp.get("Clusters", [])
            if not clusters:
                return {"status": "success", "message": "Cluster deleted",
                        "output": {"cluster_identifier": cluster_id, "cluster_status": "deleted"}}
            status = clusters[0].get("ClusterStatus")
            log_info("task", "check_completion", "polling_status",
                     f"Cluster '{cluster_id}' status: {status}")
            if status in {"deleting", "final-snapshot"}:
                return {"status": "pending", "message": f"Cluster is {status}",
                        "output": {"cluster_status": status}}
            return {"status": "failed", "message": f"Unexpected status: {status}",
                    "output": {"cluster_status": status}}
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ClusterNotFound":
                return {"status": "success", "message": "Cluster deleted",
                        "output": {"cluster_identifier": cluster_id, "cluster_status": "deleted"}}
            raise
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
                     f"status={output.get('cluster_status')}")
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
    "skip_final_cluster_snapshot": True,
}

prompt = (
    "Create an operator that deletes an Amazon Redshift cluster and polls every 15 seconds until "
    "ClusterNotFound (deletion complete). "
    "Required payload: cluster_identifier. "
    "Optional: skip_final_cluster_snapshot (bool, default true), "
    "final_cluster_snapshot_identifier (required if skip=false), poll_interval_seconds (default 15). "
    "Auth: try IAM role via STS first; if unavailable, fall back to access keys from connection. "
    "Return cluster_identifier, cluster_status. "
    "Catch ClusterNotFound as success. Catch all other AWS errors as status:failed - never raise."
)

install_docs = """# AWSRedshiftDeleteCluster - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "redshift:DeleteCluster",
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

guide_docs = """# AWSRedshiftDeleteCluster - Operator Guide

## What it does

Deletes an Amazon Redshift cluster and polls every 15 seconds until it receives `ClusterNotFound`
(indicating deletion is complete). Supports optional final snapshot before deletion.
Equivalent to Airflow's RedshiftDeleteClusterOperator.

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
      "skip_final_cluster_snapshot": true
    }

| Field                              | Required | Description                                             |
|------------------------------------|----------|---------------------------------------------------------|
| cluster_identifier                 | Yes      | Cluster to delete                                       |
| skip_final_cluster_snapshot        | No       | Skip final snapshot before delete (default: true)       |
| final_cluster_snapshot_identifier  | No       | Snapshot name if skip=false                             |
| poll_interval_seconds              | No       | Polling interval in seconds (default: 15)               |

---

## Output (on success)

    {
      "cluster_identifier": "my-redshift-cluster",
      "cluster_status": "deleted"
    }

---

## What this operator does NOT do

- Does not restore data after deletion (irreversible unless final snapshot was taken)
- Does not wait for automated snapshot creation (use skip_final_cluster_snapshot=false for that)
"""

description = """
Deletes an Amazon Redshift cluster and polls until ClusterNotFound (deletion complete). Supports
optional final snapshot. Equivalent to Airflow's RedshiftDeleteClusterOperator. Required:
cluster_identifier. Optional: skip_final_cluster_snapshot (default true),
final_cluster_snapshot_identifier, poll_interval_seconds (default 15). Auth: IAM role via STS
first, fallback to access keys. Returns cluster_identifier, cluster_status.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "Redshift",
    "category": "Data Warehouse",
    "tags": ["redshift", "cluster", "delete", "aws"],
    "airflow_equivalent": "RedshiftDeleteClusterOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

Deletion is irreversible. `skip_final_cluster_snapshot` defaults to True — set to False and provide `final_snapshot_id` to preserve a snapshot before deletion. The cluster must not be in a pending state. Deletion completes when the cluster disappears from describe_clusters (ClusterNotFound error). Automated snapshots are also deleted unless retention is configured.
"""

