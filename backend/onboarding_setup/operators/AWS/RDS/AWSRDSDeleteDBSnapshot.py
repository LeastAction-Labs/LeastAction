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

codeblock = {"main.py": '''"""
AWS RDS Delete DB Snapshot Operator

Deletes a manual RDS DB snapshot. Synchronous.
Auth priority: explicit keys â†’ assume IAM role â†’ default credential chain.
delete_db_snapshot returns immediately â€” no polling needed.

Note: Cannot delete automated snapshots, only manual ones.
"""

import json

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from src.common.logger.logger import log_error, log_info


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_rds_client(connection: dict):
    region = connection.get("region", "us-east-1")
    access_key = connection.get("aws_access_key_id")
    secret_key = connection.get("aws_secret_access_key")
    session_token = connection.get("aws_session_token")
    assume_role_arn = connection.get("assume_iam_role")

    # Case 1: Explicit credentials
    if access_key and secret_key:
        log_info(
            "task", "initialize", "auth_keys",
            f"Using explicit access key ending ...{access_key[-4:]}"
        )
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token,
            region_name=region,
        )
        return session.client("rds")

    # Case 2: Assume IAM role via STS
    if assume_role_arn:
        log_info(
            "task", "initialize", "auth_assume_role",
            f"Assuming IAM role: {assume_role_arn}"
        )
        sts = boto3.client("sts", region_name=region)
        assumed = sts.assume_role(
            RoleArn=assume_role_arn,
            RoleSessionName="leastaction_session",
        )
        creds = assumed["Credentials"]
        session = boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region,
        )
        return session.client("rds")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info(
        "task", "initialize", "auth_default",
        "Using default AWS credential chain (instance profile / ECS task role / env / config)"
    )
    session = boto3.Session(region_name=region)
    return session.client("rds")


# ---------------------------------------------------------------------------
# Operator methods
# ---------------------------------------------------------------------------

def initialize(least_action_task_object):
    """
    Build and verify the RDS boto3 client.

    Returns:
        boto3 RDS client
    """
    try:
        connection = least_action_task_object.get("connection", {})
        task_laui = least_action_task_object.get("laui")

        log_info(
            "task", "initialize", "start",
            f"Initializing RDS delete DB snapshot operator for task: {task_laui}"
        )

        rds_client = _build_rds_client(connection)

        region = connection.get("region", "us-east-1")
        log_info(
            "task", "initialize", "verify_connection",
            f"Verifying RDS connectivity in region: {region}"
        )
        rds_client.describe_db_instances(MaxRecords=20)

        log_info(
            "task", "initialize", "connection_established",
            f"RDS client ready for region: {region}"
        )
        return rds_client

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error(
            "task", "initialize", "client_error",
            f"AWS ClientError ({error_code}): {error_msg}"
        )
        raise
    except BotoCoreError as e:
        log_error(
            "task", "initialize", "botocore_error",
            f"BotoCoreError during initialization: {str(e)}"
        )
        raise
    except Exception as e:
        log_error(
            "task", "initialize", "unexpected_error",
            f"Unexpected error during initialization: {str(e)}"
        )
        raise


def run(least_action_task_object, client):
    """
    Delete a manual RDS DB snapshot using delete_db_snapshot. Synchronous â€” completes immediately.

    Payload fields:
        db_snapshot_identifier   (str, required)  -- identifier of the snapshot to delete

    Returns:
        dict with status="success", execution_type="sync", result
    """
    try:
        task_laui = least_action_task_object.get("laui")
        payload = least_action_task_object.get("payload", {})

        log_info(
            "task", "run", "extracting_payload",
            f"Extracting delete DB snapshot configuration for task: {task_laui}"
        )

        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                log_error("task", "run", "payload_parse_error", "Failed to parse payload as JSON")
                return {
                    "status": "failed",
                    "execution_type": "sync",
                    "result": None,
                    "error": "Invalid payload format â€” expected flat JSON object",
                }

        db_snapshot_identifier = payload.get("db_snapshot_identifier")
        if not db_snapshot_identifier:
            log_error("task", "run", "missing_db_snapshot_identifier",
                      "db_snapshot_identifier is required in payload")
            return {
                "status": "failed",
                "execution_type": "sync",
                "result": None,
                "error": "db_snapshot_identifier is required in payload",
            }

        log_info(
            "task", "run", "deleting_db_snapshot",
            f"Issuing delete_db_snapshot for: {db_snapshot_identifier}"
        )

        response = client.delete_db_snapshot(DBSnapshotIdentifier=db_snapshot_identifier)
        snap_arn = response["DBSnapshot"]["DBSnapshotArn"]

        log_info(
            "task", "run", "snapshot_deleted",
            f"delete_db_snapshot call succeeded for {db_snapshot_identifier} â€” ARN: {snap_arn}"
        )

        return {
            "status": "success",
            "execution_type": "sync",
            "result": {
                "db_snapshot_identifier": db_snapshot_identifier,
                "db_snapshot_arn": snap_arn,
            },
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "client_error", f"AWS ClientError ({error_code}): {error_msg}")
        return {
            "status": "failed",
            "execution_type": "sync",
            "result": None,
            "error": f"{error_code}: {error_msg}",
        }
    except Exception as e:
        log_error("task", "run", "unexpected_error", f"Unexpected error during run: {str(e)}")
        return {
            "status": "failed",
            "execution_type": "sync",
            "result": None,
            "error": str(e),
        }


def check_completion(least_action_task_object, client, run_details):
    """
    Pass through run_details â€” delete_db_snapshot is synchronous, no polling needed.

    Returns:
        dict with status, message, output passed through from run_details
    """
    log_info("task", "check_completion", "sync_passthrough",
             "DeleteDBSnapshot is synchronous â€” passing through run_details")
    result = run_details.get("result") or {}
    return {
        "status": run_details.get("status", "success"),
        "message": "Synchronous delete_db_snapshot completed",
        "output": result,
    }


def finish(least_action_task_object, client, completion_details, run_details):
    """
    Log final outcome and release any held resources.

    Returns:
        None
    """
    try:
        task_laui = least_action_task_object.get("laui")
        log_info("task", "finish", "starting_cleanup", f"Starting cleanup for task: {task_laui}")

        final_status = completion_details.get("status", "unknown")
        log_info("task", "finish", "final_status", f"Task ended with status: {final_status}")

        if client:
            try:
                client.close()
                log_info("task", "finish", "client_closed", "RDS boto3 client connection closed successfully")
            except Exception as close_error:
                log_error("task", "finish", "client_close_error", f"Error closing RDS client: {str(close_error)}")

        if final_status == "success":
            output = completion_details.get("output", {})
            log_info(
                "task", "finish", "operation_summary",
                f"Snapshot {output.get('db_snapshot_identifier')} deleted â€” "
                f"ARN: {output.get('db_snapshot_arn')}"
            )
        elif final_status == "failed":
            log_error("task", "finish", "operation_failed",
                      f"Delete snapshot operation failed: {completion_details.get('message')}")
        else:
            log_info("task", "finish", "operation_status",
                     f"Operation ended with status={final_status}, message={completion_details.get('message')}")

        log_info("task", "finish", "cleanup_complete", f"Cleanup complete for task: {task_laui}")

    except Exception as e:
        log_error("task", "finish", "cleanup_error", f"Error during finish/cleanup: {str(e)}")
        # Never re-raise from finish â€” allow graceful task completion
'''}

bashblock = {"main.sh": """#!/bin/bash
set -e
pip install boto3>=1.28.0
pip install botocore>=1.31.0
echo "Dependencies installed successfully"
"""}

connection = {"region": "us-east-1"}

payload = {
    "db_snapshot_identifier": "my-snapshot-2024"  # required
}

prompt = (
    "Delete a manual RDS DB snapshot. Payload: db_snapshot_identifier (required). "
    "Call delete_db_snapshot and return immediately with status:success (sync). "
    "check_completion passes through run_details â€” no polling needed. "
    "Note: Cannot delete automated snapshots, only manual ones. "
    "Auth: explicit keys first, then assume_iam_role via STS, then default credential chain. "
    "finish() must close the boto3 client without re-raising exceptions."
)

install_docs = """# AWSRDSDeleteDBSnapshot â€” Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {"Effect": "Allow", "Action": ["rds:DeleteDBSnapshot"], "Resource": "*"}

## Auth Setup

| Method             | How                                                                    |
|--------------------|------------------------------------------------------------------------|
| Access keys        | Set aws_access_key_id and aws_secret_access_key in connection          |
| Assume IAM role    | Set assume_iam_role (ARN) in connection â€” runner assumes it via STS    |
| Default chain      | Omit all auth fields â€” boto3 uses instance profile / ECS task role etc |
"""

guide_docs = """# AWSRDSDeleteDBSnapshot â€” Operator Guide

## What it does

Deletes a manual RDS DB snapshot synchronously. Returns status:success immediately after the API call.

Note: Cannot delete automated snapshots, only manual ones.

---

## Auth

1. **Access keys** â€” aws_access_key_id + aws_secret_access_key in connection
2. **Assume IAM role** â€” assume_iam_role (ARN) in connection, assumed via STS
3. **Default credential chain** â€” instance profile, ECS task role, env vars, ~/.aws/credentials

---

## Connection

**Scenario 1:** `{"region": "us-east-1", "aws_access_key_id": "AKIA...", "aws_secret_access_key": "..."}`
**Scenario 2:** `{"region": "us-east-1", "assume_iam_role": "arn:aws:iam::123456789012:role/MyRole"}`
**Scenario 3:** `{"region": "us-east-1"}`

---

## Payload

| Field                    | Required | Description                          |
|--------------------------|----------|--------------------------------------|
| db_snapshot_identifier   | Yes      | Identifier of the snapshot to delete |

---

## Output (on success)

    {
      "db_snapshot_identifier": "my-snapshot-2024",
      "db_snapshot_arn": "arn:aws:rds:us-east-1:123456789012:snapshot:my-snapshot-2024"
    }
"""

description = """
Deletes a manual RDS DB snapshot (sync). Calls delete_db_snapshot and returns immediately with success.
check_completion passes through run_details â€” no polling needed.
Note: Cannot delete automated snapshots, only manual ones.
Auth: explicit keys first, then assume_iam_role via STS, then default credential chain.
finish() closes the boto3 client without re-raising exceptions.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "RDS",
    "category": "Database",
    "tags": ["rds", "snapshot", "delete", "aws"],
    "airflow_equivalent": "RdsDeleteDbSnapshotOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Notes

This operator has been reviewed and tested by LeastActionLabs.
"""
