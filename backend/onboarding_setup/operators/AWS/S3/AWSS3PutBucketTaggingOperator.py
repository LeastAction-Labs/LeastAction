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
        tags = payload.get("tags", {})

        if not bucket:
            msg = "Missing required payload field: bucket"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        if not isinstance(tags, dict):
            msg = "tags must be a key-value dict"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        tag_set = [{"Key": k, "Value": v} for k, v in tags.items()]

        log_info("task", "run", "put_tagging_start",
                 f"Applying {len(tag_set)} tag(s) to bucket: {bucket}")

        client.put_bucket_tagging(Bucket=bucket, Tagging={"TagSet": tag_set})

        log_info("task", "run", "put_tagging_success",
                 f"Successfully applied {len(tag_set)} tag(s) to bucket: {bucket}")

        return {
            "execution_type": "sync",
            "status": "success",
            "result": {"bucket": bucket, "tags_applied": tags, "tag_count": len(tag_set)}
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "put_tagging_failed", f"({error_code}) {error_msg}")
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
             "S3 put bucket tagging is synchronous - already complete")
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
                     f"Bucket: {output.get('bucket')}, Tags applied: {output.get('tag_count', 0)}")
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

payload = '{"bucket": "my-bucket", "tags": {"Environment": "production", "Team": "data-eng"}}'

prompt = "Set or replace tags on an S3 bucket. Provide bucket and tags dict in the payload. Uses IAM role first, falls back to access keys in connection."

install_docs = """# AWSS3PutBucketTagging — Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": ["s3:PutBucketTagging"],
      "Resource": ["arn:aws:s3:::your-bucket-name"]
    }

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance — no keys needed in connection    |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
"""

guide_docs = """# AWSS3PutBucketTagging — Operator Guide

## What it does

Sets tags on an S3 bucket by completely replacing the existing tag set. The AWS put_bucket_tagging
API replaces all existing tags — it does not merge or append. To preserve existing tags, use
AWSS3GetBucketTagging first, merge, then call this operator.

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

---

## Payload

    {
      "bucket": "my-bucket",
      "tags":   {"Environment": "production", "Team": "data-eng"}
    }

| Field  | Required | Description                                               |
|--------|----------|-----------------------------------------------------------|
| bucket | Yes      | Name of the bucket to tag                                 |
| tags   | Yes      | Key-value dict of tags to apply. Replaces all existing.   |

---

## Output (on success)

    {
      "bucket":       "my-bucket",
      "tags_applied": {"Environment": "production", "Team": "data-eng"},
      "tag_count":    2
    }

---

## Notes

- AWS replaces the entire tag set — existing tags not in the payload are removed
- AWS S3 bucket tag limit: 10 tags per bucket
"""

description = """
Sets or replaces the entire tag set on an S3 bucket in a single put_bucket_tagging API call.
Accepts a key-value dict and applies it atomically — the AWS API fully replaces all existing
tags, so any tags not in the payload are removed. To preserve existing tags, pair with
AWSS3GetBucketTagging to read first, merge, then write back. Auth: IAM role via STS first,
fallback to flat access keys in connection. Returns bucket, tags_applied, and tag_count on
success.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "S3",
    "category": "Storage",
    "tags": ["s3", "bucket", "tagging", "write", "aws"],
    "airflow_equivalent": "S3PutBucketTaggingOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

put_bucket_tagging replaces ALL existing tags atomically — it is not additive. To preserve existing tags, first call AWSGetBucketTagging, merge the tag sets, then call this operator. Maximum 10 tags per bucket. Tag keys and values are case-sensitive.
"""

