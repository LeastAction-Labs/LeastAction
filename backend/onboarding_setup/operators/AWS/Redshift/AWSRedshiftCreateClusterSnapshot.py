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
        snapshot_id = payload.get("snapshot_identifier")

        missing = []
        if not cluster_id:
            missing.append("cluster_identifier")
        if not snapshot_id:
            missing.append("snapshot_identifier")
        if missing:
            msg = f"Missing required payload fields: {missing}"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "async", "status": "failed", "result": {"error": msg}}

        poll_interval = int(payload.get("poll_interval_seconds", 15))

        params = {
            "ClusterIdentifier": cluster_id,
            "SnapshotIdentifier": snapshot_id,
        }
        if "retention_period" in payload:
            params["ManualSnapshotRetentionPeriod"] = int(payload["retention_period"])
        if "tags" in payload and isinstance(payload["tags"], dict):
            params["Tags"] = [{"Key": k, "Value": v} for k, v in payload["tags"].items()]

        log_info("task", "run", "creating_snapshot",
                 f"Creating snapshot '{snapshot_id}' for cluster '{cluster_id}'")
        client.create_cluster_snapshot(**params)

        while True:
            resp = client.describe_cluster_snapshots(SnapshotIdentifier=snapshot_id)
            snapshots = resp.get("Snapshots", [])
            if not snapshots:
                return {
                    "execution_type": "async",
                    "status": "failed",
                    "result": {"error": f"Snapshot '{snapshot_id}' not found after creation"}
                }
            snapshot = snapshots[0]
            status = snapshot.get("Status")
            log_info("task", "run", "polling_status",
                     f"Snapshot '{snapshot_id}' status: {status}")
            if status == "available":
                return {
                    "execution_type": "async",
                    "status": "success",
                    "result": {
                        "cluster_identifier": cluster_id,
                        "snapshot_identifier": snapshot_id,
                        "snapshot_status": status,
                        "snapshot_arn": snapshot.get("SnapshotArn"),
                    }
                }
            if status not in {"creating", "available"}:
                return {
                    "execution_type": "async",
                    "status": "failed",
                    "result": {
                        "cluster_identifier": cluster_id,
                        "snapshot_identifier": snapshot_id,
                        "snapshot_status": status,
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
                "message": "Redshift snapshot creation completed",
                "output": run_details.get("result", {})
            }
        snapshot_id = run_details.get("result", {}).get("snapshot_identifier")
        resp = client.describe_cluster_snapshots(SnapshotIdentifier=snapshot_id)
        snapshots = resp.get("Snapshots", [])
        if not snapshots:
            return {"status": "failed", "message": f"Snapshot '{snapshot_id}' not found", "output": {}}
        status = snapshots[0].get("Status")
        log_info("task", "check_completion", "polling_status",
                 f"Snapshot '{snapshot_id}' status: {status}")
        if status == "available":
            return {"status": "success", "message": "Snapshot is available",
                    "output": {"snapshot_identifier": snapshot_id, "snapshot_status": status}}
        if status == "creating":
            return {"status": "pending", "message": "Snapshot is being created",
                    "output": {"snapshot_status": status}}
        return {"status": "failed", "message": f"Unexpected status: {status}",
                "output": {"snapshot_status": status}}
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
            log_info("task", "finish", "snapshot_summary",
                     f"Snapshot {output.get('snapshot_identifier')} "
                     f"status={output.get('snapshot_status')}")
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
    "snapshot_identifier": "my-snapshot-2024-01-01",
}

prompt = (
    "Create an operator that creates a manual snapshot of an Amazon Redshift cluster and polls "
    "every 15 seconds until the snapshot reaches 'available' status. "
    "Required payload: cluster_identifier, snapshot_identifier. "
    "Optional: retention_period (days), tags (dict), poll_interval_seconds (default 15). "
    "Auth: try IAM role via STS first; if unavailable, fall back to access keys from connection. "
    "Return cluster_identifier, snapshot_identifier, snapshot_status, snapshot_arn. "
    "Catch all AWS errors and return them as status:failed - never raise."
)

install_docs = """# AWSRedshiftCreateClusterSnapshot - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "redshift:CreateClusterSnapshot",
        "redshift:DescribeClusterSnapshots"
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

guide_docs = """# AWSRedshiftCreateClusterSnapshot - Operator Guide

## What it does

Creates a manual snapshot of an Amazon Redshift cluster and polls every 15 seconds until the
snapshot reaches 'available' status. Equivalent to Airflow's RedshiftCreateClusterSnapshotOperator.

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
      "snapshot_identifier": "my-snapshot-2024-01-01"
    }

| Field                 | Required | Description                                             |
|-----------------------|----------|---------------------------------------------------------|
| cluster_identifier    | Yes      | Cluster to snapshot                                     |
| snapshot_identifier   | Yes      | Unique name for the snapshot                            |
| retention_period      | No       | Retention in days (-1 = indefinite)                     |
| tags                  | No       | Dict of tag key-value pairs                             |
| poll_interval_seconds | No       | Polling interval in seconds (default: 15)               |

---

## Output (on success)

    {
      "cluster_identifier": "my-redshift-cluster",
      "snapshot_identifier": "my-snapshot-2024-01-01",
      "snapshot_status": "available",
      "snapshot_arn": "arn:aws:redshift:us-east-1:123456789012:snapshot:..."
    }

---

## What this operator does NOT do

- Does not restore from snapshot — use a separate restore operator
- Does not copy snapshot to another region
"""

description = """
Creates a manual snapshot of an Amazon Redshift cluster and polls until 'available'.
Equivalent to Airflow's RedshiftCreateClusterSnapshotOperator. Required: cluster_identifier,
snapshot_identifier. Optional: retention_period, tags, poll_interval_seconds (default 15).
Auth: IAM role via STS first, fallback to access keys. Returns cluster_identifier,
snapshot_identifier, snapshot_status, snapshot_arn.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "Redshift",
    "category": "Data Warehouse",
    "tags": ["redshift", "snapshot", "backup", "aws"],
    "airflow_equivalent": "RedshiftCreateClusterSnapshotOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

Snapshots can only be created when the cluster is in `available` state. The snapshot identifier must be unique within the account. `retention_period` controls automated snapshot retention (not this manual snapshot). Manual snapshots persist until explicitly deleted — they are not subject to the cluster's automated retention policy. Snapshot creation typically takes 5-30 minutes depending on cluster size.
"""

