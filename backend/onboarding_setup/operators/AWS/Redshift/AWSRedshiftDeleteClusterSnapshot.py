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

        snapshot_id = payload.get("snapshot_identifier")
        if not snapshot_id:
            msg = "Missing required payload field: snapshot_identifier"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        log_info("task", "run", "deleting_snapshot",
                 f"Deleting Redshift snapshot '{snapshot_id}'")

        params = {"SnapshotIdentifier": snapshot_id}
        if "snapshot_cluster_identifier" in payload:
            params["SnapshotClusterIdentifier"] = payload["snapshot_cluster_identifier"]

        resp = client.delete_cluster_snapshot(**params)
        snapshot = resp.get("Snapshot", {})

        log_info("task", "run", "snapshot_deleted",
                 f"Snapshot '{snapshot_id}' deleted successfully")

        return {
            "execution_type": "sync",
            "status": "success",
            "result": {
                "snapshot_identifier": snapshot_id,
                "snapshot_status": snapshot.get("Status", "deleted"),
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
             "AWSRedshiftDeleteClusterSnapshot is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "Redshift snapshot deletion completed",
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
    "snapshot_identifier": "my-snapshot-2024-01-01",
}

prompt = (
    "Create an operator that deletes a manual Redshift cluster snapshot. Synchronous operation. "
    "Required payload: snapshot_identifier. "
    "Optional: snapshot_cluster_identifier (cluster name if snapshot identifier is not unique). "
    "Auth: try IAM role via STS first; if unavailable, fall back to access keys from connection. "
    "Return snapshot_identifier, snapshot_status. "
    "Catch all AWS errors and return them as status:failed - never raise."
)

install_docs = """# AWSRedshiftDeleteClusterSnapshot - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "redshift:DeleteClusterSnapshot"
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

guide_docs = """# AWSRedshiftDeleteClusterSnapshot - Operator Guide

## What it does

Deletes a manual Amazon Redshift cluster snapshot. This is a synchronous operation that completes
immediately. Equivalent to Airflow's RedshiftDeleteClusterSnapshotOperator.

Note: Only manual snapshots can be deleted. Automated snapshots are managed by AWS retention policy.

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
      "snapshot_identifier": "my-snapshot-2024-01-01"
    }

| Field                        | Required | Description                                             |
|------------------------------|----------|---------------------------------------------------------|
| snapshot_identifier          | Yes      | Name of the snapshot to delete                          |
| snapshot_cluster_identifier  | No       | Cluster name (required if snapshot ID is not unique)    |

---

## Output (on success)

    {
      "snapshot_identifier": "my-snapshot-2024-01-01",
      "snapshot_status": "deleted"
    }

---

## What this operator does NOT do

- Cannot delete automated snapshots (AWS-managed, expiry-based)
- Does not verify the snapshot exists before attempting delete (AWS returns error if not found)
"""

description = """
Deletes a manual Amazon Redshift cluster snapshot. Synchronous operation.
Equivalent to Airflow's RedshiftDeleteClusterSnapshotOperator. Required: snapshot_identifier.
Optional: snapshot_cluster_identifier. Auth: IAM role via STS first, fallback to access keys.
Returns snapshot_identifier, snapshot_status.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "Redshift",
    "category": "Data Warehouse",
    "tags": ["redshift", "snapshot", "delete", "aws"],
    "airflow_equivalent": "RedshiftDeleteClusterSnapshotOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

Only manual snapshots can be deleted — automated snapshots cannot be deleted directly; they expire based on the cluster's retention period. Deletion is synchronous and immediate. `snapshot_cluster_identifier` is only needed if the snapshot was created from a different cluster than implied by the snapshot identifier. Deleted snapshots cannot be recovered.
"""

