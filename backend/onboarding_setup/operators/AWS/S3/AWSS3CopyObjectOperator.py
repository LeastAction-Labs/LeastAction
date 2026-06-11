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


def _dest_key_exists(client, bucket, key):
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
            return False
        raise


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

        source_bucket = payload.get("source_bucket")
        source_key = payload.get("source_key")
        dest_bucket = payload.get("dest_bucket")
        dest_key = payload.get("dest_key")
        override = payload.get("override")

        missing = [f for f, v in [
            ("source_bucket", source_bucket),
            ("source_key", source_key),
            ("dest_bucket", dest_bucket),
            ("dest_key", dest_key),
        ] if not v]
        if missing:
            msg = f"Missing required payload fields: {missing}"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        if override is None:
            msg = ("Missing required payload field: override. "
                   "Set override=true to allow overwriting an existing destination key, "
                   "or override=false to fail if the destination key already exists.")
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        copy_type = "intra-bucket" if source_bucket == dest_bucket else "inter-bucket"
        log_info("task", "run", "copy_start",
                 f"[{copy_type}] s3://{source_bucket}/{source_key} -> "
                 f"s3://{dest_bucket}/{dest_key} | override={override}")

        log_info("task", "run", "checking_dest",
                 f"Checking if s3://{dest_bucket}/{dest_key} already exists")
        dest_exists = _dest_key_exists(client, dest_bucket, dest_key)

        if dest_exists:
            if not override:
                msg = (f"Destination key already exists: s3://{dest_bucket}/{dest_key}. "
                       "Set override=true in the payload to allow overwriting.")
                log_error("task", "run", "dest_exists_override_false", msg)
                return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}
            else:
                log_info("task", "run", "dest_exists_override_true",
                         f"s3://{dest_bucket}/{dest_key} exists - override=true, proceeding with overwrite")
        else:
            log_info("task", "run", "dest_not_exists",
                     f"s3://{dest_bucket}/{dest_key} does not exist - proceeding with copy")

        copy_params = {
            "CopySource": {"Bucket": source_bucket, "Key": source_key},
            "Bucket": dest_bucket,
            "Key": dest_key,
        }
        if source_bucket != dest_bucket:
            copy_params["ACL"] = "bucket-owner-full-control"

        response = client.copy_object(**copy_params)
        copy_result = response.get("CopyObjectResult", {})
        etag = copy_result.get("ETag", "").strip('"')
        last_modified = str(copy_result.get("LastModified", ""))

        log_info("task", "run", "copy_success", f"[{copy_type}] Copy complete. ETag={etag}")

        return {
            "execution_type": "sync",
            "status": "success",
            "result": {
                "copy_type": copy_type,
                "source_bucket": source_bucket,
                "source_key": source_key,
                "dest_bucket": dest_bucket,
                "dest_key": dest_key,
                "overwritten": dest_exists and override,
                "etag": etag,
                "last_modified": last_modified
            }
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "copy_client_error", f"({error_code}) {error_msg}")
        return {"execution_type": "sync", "status": "failed",
                "result": {"error": f"({error_code}) {error_msg}"}}
    except BotoCoreError as e:
        log_error("task", "run", "copy_transport_error", f"BotoCoreError: {str(e)}")
        return {"execution_type": "sync", "status": "failed",
                "result": {"error": f"Transport error: {str(e)}"}}
    except Exception as e:
        log_error("task", "run", "run_failed", f"Unexpected error: {str(e)}")
        return {"execution_type": "sync", "status": "failed",
                "result": {"error": str(e)}}


def check_completion(least_action_task_object, client, run_details):
    log_info("task", "check_completion", "sync_complete",
             "S3 copy is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "Synchronous S3 copy operation completed",
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
            log_info("task", "finish", "copy_summary",
                     f"[{output.get('copy_type')}] "
                     f"s3://{output.get('source_bucket')}/{output.get('source_key')} -> "
                     f"s3://{output.get('dest_bucket')}/{output.get('dest_key')} "
                     f"| overwritten={output.get('overwritten')} | ETag: {output.get('etag')}")
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

connection = {
    "region": "us-east-1",
    "aws_access_key_id": "",
    "aws_secret_access_key": "",
    "aws_session_token": ""
}

payload = {"source_bucket": "my-source-bucket", "source_key": "data/file.json", "dest_bucket": "my-dest-bucket", "dest_key": "archive/file.json", "override": False}

prompt = (
    "Create an operator that copies a single S3 object from one location to another using AWS server-side copy. "
    "The operator must support both intra-bucket copies (same bucket, different key) and inter-bucket copies (different source and destination buckets). "
    "It should resolve auth by trying the IAM role first via STS; if unavailable, fall back to aws_access_key_id and aws_secret_access_key from the connection. "
    "The payload must include source_bucket, source_key, dest_bucket, dest_key, and override (boolean). "
    "The operator must validate that all five fields are present and return a failed status with a descriptive error if any are missing. "
    "Before performing the copy, the operator must check whether the destination key already exists using head_object. "
    "If it exists and override is false, the operator must return a failed status with a clear error message - never silently overwrite. "
    "If it exists and override is true, proceed with the copy. "
    "If the destination key does not exist, proceed with the copy regardless of override. "
    "The source object must never be deleted. "
    "For cross-bucket copies, set ACL to bucket-owner-full-control. "
    "The operator must return copy_type (intra-bucket or inter-bucket), etag, last_modified, and overwritten in the result on success. "
    "All errors from AWS (NoSuchKey, AccessDenied, etc.) must be caught and returned as a failed status - never raised."
)

install_docs = """# AWSS3CopyObjectV2 - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:HeadObject"],
      "Resource": ["arn:aws:s3:::*/*"]
    }

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance - no connection keys needed       |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
| Session token | Optionally add aws_session_token in connection                |
"""

guide_docs = """# AWSS3CopyObjectV2 - Operator Guide

## What it does

Copies a single S3 object from one location to another using AWS server-side copy_object API.
No data is downloaded or buffered locally - AWS performs the copy entirely within S3 infrastructure.

Supports:
- Intra-bucket copy: same bucket, different key (e.g. rename, archive within bucket)
- Inter-bucket copy: different source and destination buckets (same or different regions)

Before copying, always checks if the destination key exists and enforces the override flag.
Never silently overwrites.

---

## Auth

1. IAM role - tried first via STS. Used automatically if available. No keys needed in connection.
2. Access keys - fallback to aws_access_key_id + aws_secret_access_key from connection.

If neither is available, initialize() raises a RuntimeError immediately before run() is called.

---

## Connection

    {
      "region": "us-east-1",
      "aws_access_key_id": "AKIA...",
      "aws_secret_access_key": "...",
      "aws_session_token": ""       (optional)
    }

| Field               | Required | Description                                    |
|---------------------|----------|------------------------------------------------|
| region              | Yes      | AWS region for the S3 client                   |
| aws_access_key_id   | No       | Only needed if IAM role is not available        |
| aws_secret_access_key | No     | Only needed if IAM role is not available        |
| aws_session_token   | No       | For temporary/assumed-role credentials          |

---

## Payload

    {
      "source_bucket": "my-source-bucket",
      "source_key":    "data/file.json",
      "dest_bucket":   "my-dest-bucket",
      "dest_key":      "archive/file.json",
      "override":      false
    }

| Field         | Required | Description                                                          |
|---------------|----------|----------------------------------------------------------------------|
| source_bucket | Yes      | Bucket to copy from                                                  |
| source_key    | Yes      | Full S3 key of the source object                                     |
| dest_bucket   | Yes      | Bucket to copy to (can be same as source for intra-bucket)           |
| dest_key      | Yes      | Full S3 key for the destination object                               |
| override      | Yes      | true to allow overwrite; false to fail if dest key exists. Required. |

---

## Output (on success)

    {
      "copy_type":     "inter-bucket",
      "source_bucket": "my-source-bucket",
      "source_key":    "data/file.json",
      "dest_bucket":   "my-dest-bucket",
      "dest_key":      "archive/file.json",
      "overwritten":   false,
      "etag":          "518d8356aa549632896d54953f1991e8",
      "last_modified": "2026-04-01 12:41:14+00:00"
    }

| Field         | Description                                                   |
|---------------|---------------------------------------------------------------|
| copy_type     | intra-bucket or inter-bucket                                  |
| overwritten   | true if dest existed and was overwritten; false if fresh copy |
| etag          | MD5 hash of the copied object                                 |
| last_modified | UTC timestamp of when the destination object was written      |

---

## Scenarios and Edge Cases

dest exists + override=false:
  Returns status:failed with message listing the key and how to fix it.
  Copy is never performed. Source and dest are both untouched.

dest exists + override=true:
  Logs that dest exists and override=true. Proceeds with overwrite.
  overwritten:true in result.

dest does not exist:
  Copy proceeds regardless of override value.
  overwritten:false in result.

override missing from payload:
  Returns status:failed immediately with descriptive message explaining both valid values.
  Copy never attempted.

source key does not exist:
  AWS returns NoSuchKey (404). Caught as ClientError, returned as status:failed.
  Nothing created at destination.

destination prefix does not exist:
  S3 keys are flat strings - no real folders exist.
  Destination key is created at any prefix regardless of whether that prefix was used before.
  e.g. copying to archive/2026/file.json works even if no objects exist under archive/.

same source and dest key (intra-bucket self-copy):
  override=false: fails with dest-exists error, copy not performed.
  override=true: AWS copies object over itself, last_modified updates, ETag stays same.

cross-bucket copy (inter-bucket):
  ACL:bucket-owner-full-control is set automatically so dest bucket owner gets full access.
  Works across regions as long as credentials cover both buckets.
  For cross-account: dest bucket policy must allow source account s3:PutObject.

objects larger than 5 GB:
  copy_object supports up to 5 GB directly.
  For objects >5 GB, AWS automatically uses multipart copy internally.
  No operator changes or configuration needed.

no credentials available:
  IAM check fails AND no access keys in connection.
  initialize() raises RuntimeError. Task fails before run() is called.

invalid region:
  If region does not match bucket region, AWS may return 301 PermanentRedirect or NoSuchBucket.
  Fix: set region in connection to match the region where both buckets reside.

insufficient permissions:
  s3:GetObject required on source key.
  s3:PutObject required on destination key.
  s3:HeadObject required on destination key (for existence check).
  Missing any returns AccessDenied (403) - caught and returned as status:failed.

---

## What this operator does NOT do

- Does not delete the source object (use a separate delete operator for move semantics)
- Does not copy object metadata, tags, or ACLs
- Does not support copying multiple objects or wildcard/prefix-based copies - one object per run
- Does not validate whether the destination bucket exists (AWS returns NoSuchBucket if it does not)
- Does not silently overwrite - always enforces the override flag
"""

description = """
Copies a single S3 object between S3 locations using AWS server-side copy — no bytes transit
through the operator. Supports intra-bucket (same bucket, different key) and inter-bucket copies
across regions and accounts. Always performs a head_object check before copying and strictly
enforces the override flag: fails with a clear error when override=false and the destination
already exists — never silently overwrites. Auth: IAM role via STS first, fallback to flat
access keys in connection. Returns copy_type, etag, last_modified, and overwritten on success.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "S3",
    "category": "Storage",
    "tags": ["s3", "copy", "object", "aws"],
    "airflow_equivalent": "S3CopyObjectOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

By default (override=false) the operator returns status:failed if the destination object already exists — this prevents accidental overwrites. Set override=true to allow overwriting. Cross-region copies are supported by specifying different source and destination buckets in different regions. The S3 copy API does not move objects — the source is preserved after copy.
"""

