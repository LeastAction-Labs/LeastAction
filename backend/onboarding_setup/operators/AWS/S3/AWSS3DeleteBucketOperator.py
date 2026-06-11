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

codeblock = {"main.py": """import json
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from src.common.logger.logger import log_info, log_error


def _build_s3_client(connection: dict):
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
        return session.client("s3")

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
        return session.client("s3")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info("task", "initialize", "auth_default",
             "Using default AWS credential chain (instance profile / ECS task role / env / config)")
    return boto3.Session(region_name=region).client("s3")


def initialize(least_action_task_object):
    try:
        connection = least_action_task_object.get("connection", {})
        if isinstance(connection, str):
            connection = json.loads(connection)

        log_info("task", "initialize", "building_client",
                 f"region={connection.get('region', 'us-east-1')}")

        client = _build_s3_client(connection)
        client.list_buckets()
        log_info("task", "initialize", "connectivity_ok", "S3 client initialized and verified")
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

        bucket = payload.get("bucket")
        force_delete = payload.get("force_delete", False)

        if not bucket:
            msg = "Missing required payload field: bucket"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        objects_deleted = 0

        if force_delete:
            log_info("task", "run", "force_delete_start",
                     f"Emptying bucket before deletion: {bucket}")
            paginator = client.get_paginator("list_object_versions")
            for page in paginator.paginate(Bucket=bucket):
                delete_list = []
                for obj in page.get("Versions", []):
                    delete_list.append({"Key": obj["Key"], "VersionId": obj["VersionId"]})
                for marker in page.get("DeleteMarkers", []):
                    delete_list.append({"Key": marker["Key"], "VersionId": marker["VersionId"]})
                if delete_list:
                    client.delete_objects(Bucket=bucket, Delete={"Objects": delete_list})
                    objects_deleted += len(delete_list)
                    log_info("task", "run", "objects_deleted",
                             f"Deleted {len(delete_list)} objects/versions")
            log_info("task", "run", "force_delete_complete",
                     f"Bucket emptied: {objects_deleted} total objects/versions deleted")

        log_info("task", "run", "delete_bucket_start", f"Deleting bucket: {bucket}")
        client.delete_bucket(Bucket=bucket)
        log_info("task", "run", "delete_bucket_success", f"Bucket deleted: {bucket}")

        return {
            "execution_type": "sync",
            "status": "success",
            "result": {"bucket": bucket, "deleted": True, "objects_deleted": objects_deleted}
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "delete_bucket_failed", f"({error_code}) {error_msg}")
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
             "S3 delete bucket is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "Synchronous S3 operation completed",
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
            log_info("task", "finish", "summary",
                     f"Bucket: {output.get('bucket')}, Deleted: True, "
                     f"Objects removed: {output.get('objects_deleted', 0)}")
        else:
            log_error("task", "finish", "operation_failed",
                      completion_details.get("message", "No message"))
        if client:
            try:
                client.close()
                log_info("task", "finish", "client_closed", "S3 boto3 client closed successfully")
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

connection = {"region": "us-east-1"}

payload = '{"bucket": "my-bucket", "force_delete": false}'

prompt = "Delete an S3 bucket. Provide the bucket name in the payload. Set force_delete=true to empty first. Uses IAM role first, falls back to access keys in connection."

install_docs = """# AWSS3DeleteBucket — Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": ["s3:DeleteBucket", "s3:ListBucketVersions", "s3:DeleteObject", "s3:DeleteObjectVersion"],
      "Resource": ["arn:aws:s3:::your-bucket-name", "arn:aws:s3:::your-bucket-name/*"]
    }

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance — no keys needed in connection    |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
"""

guide_docs = """# AWSS3DeleteBucket — Operator Guide

## What it does

Deletes an S3 bucket. With force_delete=true, empties all objects and versions first using
the list_object_versions paginator. This is required if the bucket is not empty — AWS will
return BucketNotEmpty otherwise.

---

## Auth

| Priority | Method |
|---|---|
| 1st | IAM role — tried via STS. No keys needed in connection. |
| 2nd | aws_access_key_id + aws_secret_access_key from connection |

---

## Connection

Minimum (IAM role):

    {"region": "us-east-1"}

Sample with access keys:

    {
      "region": "us-east-1",
      "aws_access_key_id": "AKIA...",
      "aws_secret_access_key": "...",
      "aws_session_token": "..."
    }

---

## Payload

    {"bucket": "my-bucket", "force_delete": false}

| Field        | Required | Description                                                            |
|--------------|----------|------------------------------------------------------------------------|
| bucket       | Yes      | Name of the bucket to delete                                           |
| force_delete | No       | If true, empties all objects/versions before deleting. Default: false  |

---

## Output (on success)

    {
      "bucket":         "my-bucket",
      "deleted":        true,
      "objects_deleted": 0
    }

| Field           | Description                                        |
|-----------------|----------------------------------------------------|
| bucket          | The bucket that was deleted                        |
| deleted         | Always true on success                             |
| objects_deleted | Number of objects/versions removed (force_delete)  |

---

## Notes

- force_delete=false on a non-empty bucket returns BucketNotEmpty as status:failed
- Deletion is irreversible — all objects are permanently lost unless versioned elsewhere
"""

description = """
Deletes an S3 bucket, with an optional force_delete mode that empties all objects and versions
first using the list_object_versions paginator — required when the bucket is non-empty and AWS
would otherwise return BucketNotEmpty. Without force_delete, the bucket must already be empty.
Auth: IAM role via STS first, fallback to flat access keys in connection. Returns bucket name,
deleted:true, and objects_deleted count on success.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "S3",
    "category": "Storage",
    "tags": ["s3", "bucket", "delete", "aws"],
    "airflow_equivalent": "S3DeleteBucketOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

S3 buckets must be empty before they can be deleted — AWS returns BucketNotEmpty otherwise. Set force_delete=true to automatically delete all objects (including all versions and delete markers) before deleting the bucket. Use with caution — force_delete is irreversible and deletes all data. Deletion itself is permanent and the bucket name becomes available to other accounts immediately.
"""

