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
AWS RDS Delete DB Instance Operator

Deletes an RDS DB instance. Irreversible. Async â€” polls until deleted.
Auth priority: explicit keys â†’ assume IAM role â†’ default credential chain.
Execution is async â€” run() triggers deletion; check_completion() polls until DBInstanceNotFound.

Warning: Irreversible â€” all data lost unless skip_final_snapshot=False.
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
            f"Initializing RDS delete DB instance operator for task: {task_laui}"
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
    Delete an RDS DB instance using delete_db_instance.

    Payload fields:
        db_instance_identifier         (str, required)   -- DB instance to delete
        skip_final_snapshot            (bool, optional)  -- skip final snapshot before deletion, default True
        final_db_snapshot_identifier   (str, optional)   -- required if skip_final_snapshot=False
        delete_automated_backups       (bool, optional)  -- delete automated backups, default True

    Returns:
        dict with status="pending", execution_type="async", result
    """
    try:
        task_laui = least_action_task_object.get("laui")
        payload = least_action_task_object.get("payload", {})

        log_info(
            "task", "run", "extracting_payload",
            f"Extracting delete DB instance configuration for task: {task_laui}"
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

        db_instance_identifier = payload.get("db_instance_identifier")
        if not db_instance_identifier:
            log_error("task", "run", "missing_db_instance_identifier",
                      "db_instance_identifier is required in payload")
            return {
                "status": "failed",
                "execution_type": "async",
                "result": None,
                "error": "db_instance_identifier is required in payload",
            }

        skip_final_snapshot = payload.get("skip_final_snapshot", True)
        delete_automated_backups = payload.get("delete_automated_backups", True)
        final_db_snapshot_identifier = payload.get("final_db_snapshot_identifier")

        delete_kwargs = {
            "DBInstanceIdentifier": db_instance_identifier,
            "SkipFinalSnapshot": skip_final_snapshot,
            "DeleteAutomatedBackups": delete_automated_backups,
        }

        if not skip_final_snapshot and final_db_snapshot_identifier:
            delete_kwargs["FinalDBSnapshotIdentifier"] = final_db_snapshot_identifier
            log_info(
                "task", "run", "final_snapshot",
                f"Will create final snapshot {final_db_snapshot_identifier} before deletion"
            )

        log_info(
            "task", "run", "deleting_db_instance",
            f"Issuing delete_db_instance for: {db_instance_identifier} "
            f"(skip_final_snapshot={skip_final_snapshot})"
        )

        client.delete_db_instance(**delete_kwargs)

        log_info(
            "task", "run", "delete_issued",
            f"delete_db_instance call succeeded for {db_instance_identifier} â€” "
            f"instance is being deleted asynchronously"
        )

        return {
            "status": "pending",
            "execution_type": "async",
            "result": {
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
    Poll describe_db_instances; when DBInstanceNotFound is raised, the instance is deleted (success).

    Returns:
        dict with status (success | pending | failed), message, output
    """
    try:
        if run_details.get("status") == "failed":
            log_error("task", "check_completion", "run_phase_failed",
                      f"Run phase reported failure: {run_details.get('error')}")
            return {
                "status": "failed",
                "message": f"Delete failed in run phase: {run_details.get('error')}",
                "output": None,
            }

        result = run_details.get("result", {})
        db_instance_identifier = result.get("db_instance_identifier")
        if not db_instance_identifier:
            return {"status": "failed", "message": "No db_instance_identifier in run_details", "output": None}

        log_info(
            "task", "check_completion", "polling_db_status",
            f"Polling describe_db_instances for: {db_instance_identifier}"
        )

        try:
            response = client.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
            db = response["DBInstances"][0]
            db_status = db.get("DBInstanceStatus", "unknown")

            log_info(
                "task", "check_completion", "db_instance_status",
                f"DB instance {db_instance_identifier}: status={db_status}"
            )

            log_info("task", "check_completion", "db_still_deleting",
                     f"DB instance {db_instance_identifier} still deleting â€” current status: {db_status}")
            return {
                "status": "pending",
                "message": f"DB instance status: {db_status}",
                "output": {"db_instance_identifier": db_instance_identifier, "db_instance_status": db_status},
            }

        except ClientError as inner_e:
            error_code = inner_e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "DBInstanceNotFound":
                log_info("task", "check_completion", "db_deleted",
                         f"DB instance {db_instance_identifier} has been deleted (DBInstanceNotFound)")
                return {
                    "status": "success",
                    "message": f"DB instance {db_instance_identifier} deleted successfully",
                    "output": {
                        "db_instance_identifier": db_instance_identifier,
                        "db_instance_status": "deleted",
                    },
                }
            raise

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
                f"DB instance {output.get('db_instance_identifier')} deleted successfully"
            )
        elif final_status == "failed":
            log_error("task", "finish", "operation_failed",
                      f"Delete operation failed: {completion_details.get('message')}")
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
    "db_instance_identifier": "my-db-instance",   # required
    # "skip_final_snapshot": True,                  # optional â€” default True; set False to create final snapshot
    # "final_db_snapshot_identifier": "my-final-snap",  # optional â€” required if skip_final_snapshot=False
    # "delete_automated_backups": True              # optional â€” default True
}

prompt = (
    "Delete an RDS DB instance. Payload: db_instance_identifier (required). "
    "Optional: skip_final_snapshot (default True), final_db_snapshot_identifier "
    "(required if skip_final_snapshot=False), delete_automated_backups (default True). "
    "Call delete_db_instance and return immediately with status:pending (async). "
    "check_completion polls describe_db_instances; when DBInstanceNotFound is raised, deletion is complete. "
    "Warning: Irreversible â€” all data lost unless skip_final_snapshot=False. "
    "Auth: explicit keys first, then assume_iam_role via STS, then default credential chain. "
    "finish() must close the boto3 client without re-raising exceptions."
)

install_docs = """# AWSRDSDeleteDBInstance â€” Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {"Effect": "Allow", "Action": ["rds:DeleteDBInstance", "rds:DescribeDBInstances"], "Resource": "*"}

## Auth Setup

| Method             | How                                                                    |
|--------------------|------------------------------------------------------------------------|
| Access keys        | Set aws_access_key_id and aws_secret_access_key in connection          |
| Assume IAM role    | Set assume_iam_role (ARN) in connection â€” runner assumes it via STS    |
| Default chain      | Omit all auth fields â€” boto3 uses instance profile / ECS task role etc |
"""

guide_docs = """# AWSRDSDeleteDBInstance â€” Operator Guide

## What it does

Deletes an RDS DB instance and returns immediately with status:pending (async).
check_completion polls describe_db_instances; when DBInstanceNotFound is raised, deletion is complete.

WARNING: This operation is irreversible. All data will be lost unless skip_final_snapshot=False.

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

| Field                          | Required | Description                                              |
|--------------------------------|----------|----------------------------------------------------------|
| db_instance_identifier         | Yes      | DB instance identifier to delete                         |
| skip_final_snapshot            | No       | Skip final snapshot, default True                        |
| final_db_snapshot_identifier   | No       | Required if skip_final_snapshot=False                    |
| delete_automated_backups       | No       | Delete automated backups, default True                   |

---

## Output (on success)

    {
      "db_instance_identifier": "my-db-instance",
      "db_instance_status": "deleted"
    }
"""

description = """
Deletes an RDS DB instance (async). Calls delete_db_instance and returns immediately.
check_completion polls describe_db_instances until DBInstanceNotFound â€” confirming deletion.
WARNING: Irreversible â€” all data lost unless skip_final_snapshot=False.
Auth: explicit keys first, then assume_iam_role via STS, then default credential chain.
finish() closes the boto3 client without re-raising exceptions.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "RDS",
    "category": "Database",
    "tags": ["rds", "database", "delete", "aws"],
    "airflow_equivalent": "RdsDeleteDbInstanceOperator"
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
