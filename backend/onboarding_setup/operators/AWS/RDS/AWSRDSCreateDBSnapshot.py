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
AWS RDS Create DB Snapshot Operator

Creates a manual RDS DB snapshot. Async â€” polls until available.
Auth priority: explicit keys â†’ assume IAM role â†’ default credential chain.
Execution is async â€” run() triggers snapshot creation; check_completion() polls until available.
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
            f"Initializing RDS create DB snapshot operator for task: {task_laui}"
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
    Create a manual RDS DB snapshot using create_db_snapshot.

    Payload fields:
        db_snapshot_identifier   (str, required)          -- identifier for the new snapshot
        db_instance_identifier   (str, required)          -- source DB instance identifier
        tags                     (list[dict], optional)   -- list of {"Key": str, "Value": str}

    Returns:
        dict with status="pending", execution_type="async", result
    """
    try:
        task_laui = least_action_task_object.get("laui")
        payload = least_action_task_object.get("payload", {})

        log_info(
            "task", "run", "extracting_payload",
            f"Extracting create DB snapshot configuration for task: {task_laui}"
        )

        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                log_error("task", "run", "payload_parse_error", "Failed to parse payload as JSON")
                return {
                    "status": "failed",
                    "execution_type": "async",
                    "result": None,
                    "error": "Invalid payload format â€” expected flat JSON object",
                }

        db_snapshot_identifier = payload.get("db_snapshot_identifier")
        db_instance_identifier = payload.get("db_instance_identifier")

        for field, val in [
            ("db_snapshot_identifier", db_snapshot_identifier),
            ("db_instance_identifier", db_instance_identifier),
        ]:
            if not val:
                log_error("task", "run", f"missing_{field}", f"{field} is required in payload")
                return {
                    "status": "failed",
                    "execution_type": "async",
                    "result": None,
                    "error": f"{field} is required in payload",
                }

        create_kwargs = {
            "DBSnapshotIdentifier": db_snapshot_identifier,
            "DBInstanceIdentifier": db_instance_identifier,
        }

        if payload.get("tags"):
            create_kwargs["Tags"] = payload["tags"]

        log_info(
            "task", "run", "creating_db_snapshot",
            f"Issuing create_db_snapshot: {db_snapshot_identifier} from instance {db_instance_identifier}"
        )

        response = client.create_db_snapshot(**create_kwargs)
        snap_arn = response["DBSnapshot"]["DBSnapshotArn"]

        log_info(
            "task", "run", "snapshot_creation_issued",
            f"create_db_snapshot call succeeded for {db_snapshot_identifier} â€” "
            f"ARN: {snap_arn} â€” snapshot is being created asynchronously"
        )

        return {
            "status": "pending",
            "execution_type": "async",
            "result": {
                "db_snapshot_identifier": db_snapshot_identifier,
                "db_snapshot_arn": snap_arn,
                "db_instance_identifier": db_instance_identifier,
            },
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "client_error", f"AWS ClientError ({error_code}): {error_msg}")
        return {
            "status": "failed",
            "execution_type": "async",
            "result": None,
            "error": f"{error_code}: {error_msg}",
        }
    except Exception as e:
        log_error("task", "run", "unexpected_error", f"Unexpected error during run: {str(e)}")
        return {
            "status": "failed",
            "execution_type": "async",
            "result": None,
            "error": str(e),
        }


def check_completion(least_action_task_object, client, run_details):
    """
    Poll describe_db_snapshots to determine whether the snapshot is available.

    Returns:
        dict with status (success | pending | failed), message, output
    """
    try:
        if run_details.get("status") == "failed":
            log_error("task", "check_completion", "run_phase_failed",
                      f"Run phase reported failure: {run_details.get('error')}")
            return {
                "status": "failed",
                "message": f"Snapshot creation failed in run phase: {run_details.get('error')}",
                "output": None,
            }

        result = run_details.get("result", {})
        db_snapshot_identifier = result.get("db_snapshot_identifier")
        if not db_snapshot_identifier:
            return {"status": "failed", "message": "No db_snapshot_identifier in run_details", "output": None}

        log_info(
            "task", "check_completion", "polling_snapshot_status",
            f"Polling describe_db_snapshots for: {db_snapshot_identifier}"
        )

        response = client.describe_db_snapshots(DBSnapshotIdentifier=db_snapshot_identifier)
        snapshot = response["DBSnapshots"][0]
        snap_status = snapshot.get("Status", "unknown")

        log_info(
            "task", "check_completion", "snapshot_status",
            f"Snapshot {db_snapshot_identifier}: status={snap_status}"
        )

        if snap_status == "available":
            log_info("task", "check_completion", "snapshot_available",
                     f"Snapshot {db_snapshot_identifier} is available")
            return {
                "status": "success",
                "message": f"Snapshot {db_snapshot_identifier} is available",
                "output": {
                    "db_snapshot_identifier": db_snapshot_identifier,
                    "db_snapshot_arn": result.get("db_snapshot_arn"),
                    "db_instance_identifier": result.get("db_instance_identifier"),
                    "snapshot_status": snap_status,
                    "snapshot_create_time": str(snapshot.get("SnapshotCreateTime", "")),
                    "allocated_storage": snapshot.get("AllocatedStorage", 0),
                    "engine": snapshot.get("Engine", ""),
                },
            }

        if snap_status == "failed":
            log_error("task", "check_completion", "snapshot_failed",
                      f"Snapshot {db_snapshot_identifier} entered failed state")
            return {
                "status": "failed",
                "message": f"Snapshot entered failed state: {snap_status}",
                "output": {"db_snapshot_identifier": db_snapshot_identifier, "snapshot_status": snap_status},
            }

        log_info("task", "check_completion", "snapshot_still_creating",
                 f"Snapshot {db_snapshot_identifier} still being created â€” current status: {snap_status}")
        return {
            "status": "pending",
            "message": f"Snapshot status: {snap_status}",
            "output": {"db_snapshot_identifier": db_snapshot_identifier, "snapshot_status": snap_status},
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "check_completion", "client_error", f"AWS ClientError ({error_code}): {error_msg}")
        return {"status": "failed", "message": f"{error_code}: {error_msg}", "output": None}
    except Exception as e:
        log_error("task", "check_completion", "unexpected_error",
                  f"Unexpected error during completion check: {str(e)}")
        return {"status": "failed", "message": f"Completion check error: {str(e)}", "output": None}


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
                f"Snapshot {output.get('db_snapshot_identifier')} created â€” "
                f"ARN: {output.get('db_snapshot_arn')}, status={output.get('snapshot_status')}"
            )
        elif final_status == "failed":
            log_error("task", "finish", "operation_failed",
                      f"Snapshot creation failed: {completion_details.get('message')}")
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
    "db_snapshot_identifier": "my-snapshot-2024",    # required â€” identifier for the new snapshot
    "db_instance_identifier": "my-db-instance",      # required â€” source DB instance
    # "tags": [{"Key": "Env", "Value": "prod"}]      # optional
}

prompt = (
    "Create a manual RDS DB snapshot. Payload: db_snapshot_identifier (required), "
    "db_instance_identifier (required), tags (optional). "
    "Call create_db_snapshot and return immediately with status:pending (async). "
    "check_completion polls describe_db_snapshots until status == available. "
    "On success, output includes the snapshot ARN. "
    "Auth: explicit keys first, then assume_iam_role via STS, then default credential chain. "
    "finish() must close the boto3 client without re-raising exceptions."
)

install_docs = """# AWSRDSCreateDBSnapshot â€” Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {"Effect": "Allow", "Action": ["rds:CreateDBSnapshot", "rds:DescribeDBSnapshots", "rds:DescribeDBInstances"], "Resource": "*"}

## Auth Setup

| Method             | How                                                                    |
|--------------------|------------------------------------------------------------------------|
| Access keys        | Set aws_access_key_id and aws_secret_access_key in connection          |
| Assume IAM role    | Set assume_iam_role (ARN) in connection â€” runner assumes it via STS    |
| Default chain      | Omit all auth fields â€” boto3 uses instance profile / ECS task role etc |
"""

guide_docs = """# AWSRDSCreateDBSnapshot â€” Operator Guide

## What it does

Creates a manual RDS DB snapshot and returns immediately with status:pending (async).
check_completion polls describe_db_snapshots until the snapshot reaches available state (typically 1-5 min).

Note: The DB instance must be in the "available" state to create a snapshot.

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

| Field                    | Required | Description                              |
|--------------------------|----------|------------------------------------------|
| db_snapshot_identifier   | Yes      | Identifier for the new snapshot          |
| db_instance_identifier   | Yes      | Source DB instance identifier            |
| tags                     | No       | List of {"Key": str, "Value": str}       |

---

## Output (on success)

    {
      "db_snapshot_identifier": "my-snapshot-2024",
      "db_snapshot_arn": "arn:aws:rds:us-east-1:123456789012:snapshot:my-snapshot-2024",
      "db_instance_identifier": "my-db-instance",
      "snapshot_status": "available",
      "snapshot_create_time": "2024-01-15 10:30:00+00:00",
      "allocated_storage": 20,
      "engine": "mysql"
    }
"""

description = """
Creates a manual RDS DB snapshot (async). Calls create_db_snapshot and returns immediately.
check_completion polls describe_db_snapshots until the snapshot reaches available state.
On success, output includes the snapshot ARN.
Auth: explicit keys first, then assume_iam_role via STS, then default credential chain.
finish() closes the boto3 client without re-raising exceptions.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "RDS",
    "category": "Database",
    "tags": ["rds", "snapshot", "backup", "aws"],
    "airflow_equivalent": "RdsCreateDbSnapshotOperator"
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
