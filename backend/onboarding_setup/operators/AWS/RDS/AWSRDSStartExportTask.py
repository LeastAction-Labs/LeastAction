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
AWS RDS Start Export Task Operator

Exports an RDS snapshot to S3 in Parquet format. Async â€” polls until COMPLETE.
Auth priority: explicit keys â†’ assume IAM role â†’ default credential chain.
Execution is async â€” run() triggers the export; check_completion() polls until COMPLETE.

Note: Only customer managed KMS keys are supported (AWS managed keys not supported for exports).
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
            f"Initializing RDS start export task operator for task: {task_laui}"
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
    Start an RDS snapshot export task to S3 using start_export_task.

    Payload fields:
        export_task_identifier   (str, required)          -- unique identifier for the export task
        source_arn               (str, required)          -- ARN of the RDS snapshot to export
        s3_bucket_name           (str, required)          -- destination S3 bucket
        iam_role_arn             (str, required)          -- IAM role with S3 write and KMS permissions
        kms_key_id               (str, required)          -- customer managed KMS key ARN (AWS managed keys not supported)
        s3_prefix                (str, optional)          -- S3 key prefix for export files
        export_only              (list[str], optional)    -- specific tables to export (default: all)

    Returns:
        dict with status="pending", execution_type="async", result
    """
    try:
        task_laui = least_action_task_object.get("laui")
        payload = least_action_task_object.get("payload", {})

        log_info(
            "task", "run", "extracting_payload",
            f"Extracting start export task configuration for task: {task_laui}"
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

        export_task_identifier = payload.get("export_task_identifier")
        source_arn = payload.get("source_arn")
        s3_bucket_name = payload.get("s3_bucket_name")
        iam_role_arn = payload.get("iam_role_arn")
        kms_key_id = payload.get("kms_key_id")

        for field, val in [
            ("export_task_identifier", export_task_identifier),
            ("source_arn", source_arn),
            ("s3_bucket_name", s3_bucket_name),
            ("iam_role_arn", iam_role_arn),
            ("kms_key_id", kms_key_id),
        ]:
            if not val:
                log_error("task", "run", f"missing_{field}", f"{field} is required in payload")
                return {
                    "status": "failed",
                    "execution_type": "async",
                    "result": None,
                    "error": f"{field} is required in payload",
                }

        export_kwargs = {
            "ExportTaskIdentifier": export_task_identifier,
            "SourceArn": source_arn,
            "S3BucketName": s3_bucket_name,
            "IamRoleArn": iam_role_arn,
            "KmsKeyId": kms_key_id,
        }

        if payload.get("s3_prefix"):
            export_kwargs["S3Prefix"] = payload["s3_prefix"]
        if payload.get("export_only"):
            export_kwargs["ExportOnly"] = payload["export_only"]

        log_info(
            "task", "run", "starting_export_task",
            f"Issuing start_export_task: {export_task_identifier} "
            f"from {source_arn} to s3://{s3_bucket_name}"
        )

        client.start_export_task(**export_kwargs)

        log_info(
            "task", "run", "export_task_started",
            f"start_export_task call succeeded for {export_task_identifier} â€” "
            f"export is running asynchronously"
        )

        return {
            "status": "pending",
            "execution_type": "async",
            "result": {
                "export_task_identifier": export_task_identifier,
                "source_arn": source_arn,
                "s3_bucket_name": s3_bucket_name,
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
    Poll describe_export_tasks until status == COMPLETE.
    Failed if status in (FAILED, CANCELED).

    Returns:
        dict with status (success | pending | failed), message, output
    """
    try:
        if run_details.get("status") == "failed":
            log_error("task", "check_completion", "run_phase_failed",
                      f"Run phase reported failure: {run_details.get('error')}")
            return {
                "status": "failed",
                "message": f"Export failed in run phase: {run_details.get('error')}",
                "output": None,
            }

        result = run_details.get("result", {})
        export_task_identifier = result.get("export_task_identifier")
        if not export_task_identifier:
            return {"status": "failed", "message": "No export_task_identifier in run_details", "output": None}

        log_info(
            "task", "check_completion", "polling_export_status",
            f"Polling describe_export_tasks for: {export_task_identifier}"
        )

        response = client.describe_export_tasks(ExportTaskIdentifier=export_task_identifier)
        tasks = response.get("ExportTasks", [])
        if not tasks:
            return {
                "status": "failed",
                "message": f"Export task {export_task_identifier} not found",
                "output": None,
            }

        task = tasks[0]
        export_status = task.get("Status", "UNKNOWN")

        log_info(
            "task", "check_completion", "export_task_status",
            f"Export task {export_task_identifier}: status={export_status}"
        )

        if export_status == "COMPLETE":
            log_info("task", "check_completion", "export_complete",
                     f"Export task {export_task_identifier} completed successfully")
            return {
                "status": "success",
                "message": f"Export task {export_task_identifier} completed",
                "output": {
                    "export_task_identifier": export_task_identifier,
                    "source_arn": result.get("source_arn"),
                    "s3_bucket_name": result.get("s3_bucket_name"),
                    "export_status": export_status,
                    "s3_prefix": task.get("S3Prefix", ""),
                    "percent_progress": task.get("PercentProgress", 100),
                },
            }

        if export_status in ("FAILED", "CANCELED"):
            failure_cause = task.get("FailureCause", "Unknown")
            log_error("task", "check_completion", "export_failed",
                      f"Export task {export_task_identifier} {export_status}: {failure_cause}")
            return {
                "status": "failed",
                "message": f"Export task {export_status}: {failure_cause}",
                "output": {
                    "export_task_identifier": export_task_identifier,
                    "export_status": export_status,
                    "failure_cause": failure_cause,
                },
            }

        percent_progress = task.get("PercentProgress", 0)
        log_info("task", "check_completion", "export_in_progress",
                 f"Export task {export_task_identifier} in progress â€” "
                 f"status: {export_status}, progress: {percent_progress}%")
        return {
            "status": "pending",
            "message": f"Export task status: {export_status} ({percent_progress}%)",
            "output": {"export_task_identifier": export_task_identifier, "export_status": export_status,
                        "percent_progress": percent_progress},
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
                f"Export task {output.get('export_task_identifier')} completed â€” "
                f"destination: s3://{output.get('s3_bucket_name')}"
            )
        elif final_status == "failed":
            log_error("task", "finish", "operation_failed",
                      f"Export task failed: {completion_details.get('message')}")
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
    "export_task_identifier": "my-export-2024",                                                  # required
    "source_arn": "arn:aws:rds:us-east-1:123456789012:snapshot:my-snap",                        # required â€” snapshot ARN
    "s3_bucket_name": "my-bucket",                                                               # required
    "iam_role_arn": "arn:aws:iam::123456789012:role/RDSExportRole",                             # required
    "kms_key_id": "arn:aws:kms:us-east-1:123456789012:key/my-key",                             # required â€” customer managed key only
    # "s3_prefix": "rds-exports/",                                                              # optional â€” S3 key prefix
    # "export_only": ["my_database.my_table"]                                                   # optional â€” specific tables (default: all)
}

prompt = (
    "Export an RDS snapshot to S3 in Parquet format. Payload: export_task_identifier, source_arn, "
    "s3_bucket_name, iam_role_arn, kms_key_id (all required). "
    "Optional: s3_prefix, export_only (list of specific tables). "
    "Call start_export_task and return immediately with status:pending (async). "
    "check_completion polls describe_export_tasks until status == COMPLETE. "
    "Failed if status in (FAILED, CANCELED). "
    "Note: Only customer managed KMS keys are supported. "
    "Auth: explicit keys first, then assume_iam_role via STS, then default credential chain. "
    "finish() must close the boto3 client without re-raising exceptions."
)

install_docs = """# AWSRDSStartExportTask â€” Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {"Effect": "Allow", "Action": ["rds:StartExportTask", "rds:DescribeExportTasks", "rds:DescribeDBInstances"], "Resource": "*"}

## IAM Role Requirements (iam_role_arn)

The IAM role must have:
- Trust relationship with: export.rds.amazonaws.com
- Permissions: s3:PutObject*, s3:GetBucketLocation, kms:GenerateDataKey, kms:Decrypt

## Auth Setup

| Method             | How                                                                    |
|--------------------|------------------------------------------------------------------------|
| Access keys        | Set aws_access_key_id and aws_secret_access_key in connection          |
| Assume IAM role    | Set assume_iam_role (ARN) in connection â€” runner assumes it via STS    |
| Default chain      | Omit all auth fields â€” boto3 uses instance profile / ECS task role etc |
"""

guide_docs = """# AWSRDSStartExportTask â€” Operator Guide

## What it does

Exports an RDS snapshot to S3 in Apache Parquet format and returns immediately with status:pending (async).
check_completion polls describe_export_tasks until the export reaches COMPLETE status.

Note: Only customer managed KMS keys are supported (AWS managed keys not supported for exports).

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

| Field                    | Required | Description                                                         |
|--------------------------|----------|---------------------------------------------------------------------|
| export_task_identifier   | Yes      | Unique identifier for the export task                               |
| source_arn               | Yes      | ARN of the RDS snapshot to export                                   |
| s3_bucket_name           | Yes      | Destination S3 bucket                                               |
| iam_role_arn             | Yes      | IAM role with S3 write and KMS permissions                          |
| kms_key_id               | Yes      | Customer managed KMS key ARN (AWS managed keys not supported)       |
| s3_prefix                | No       | S3 key prefix for export files                                      |
| export_only              | No       | List of specific tables to export (default: all)                    |

---

## Output (on success)

    {
      "export_task_identifier": "my-export-2024",
      "source_arn": "arn:aws:rds:us-east-1:123456789012:snapshot:my-snap",
      "s3_bucket_name": "my-bucket",
      "export_status": "COMPLETE",
      "s3_prefix": "rds-exports/",
      "percent_progress": 100
    }
"""

description = """
Exports an RDS snapshot to S3 in Parquet format (async). Calls start_export_task and returns immediately.
check_completion polls describe_export_tasks until status == COMPLETE.
Requires a customer managed KMS key (AWS managed keys not supported for exports).
Auth: explicit keys first, then assume_iam_role via STS, then default credential chain.
finish() closes the boto3 client without re-raising exceptions.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "RDS",
    "category": "Database",
    "tags": ["rds", "export", "s3", "parquet", "aws"],
    "airflow_equivalent": "RdsStartExportTaskOperator"
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
