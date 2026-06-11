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
import base64
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
        key = payload.get("key")
        content = payload.get("content")
        encoding = payload.get("encoding", "utf-8")  # utf-8 or base64
        content_type = payload.get("content_type", "application/octet-stream")
        metadata = payload.get("metadata", {})
        acl = payload.get("acl")

        missing = [f for f, v in [("bucket", bucket), ("key", key), ("content", content)]
                   if not v and v != ""]
        if missing:
            msg = f"Missing required payload fields: {missing}"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        # Resolve body bytes
        if encoding == "base64":
            body = base64.b64decode(content)
            log_info("task", "run", "encoding", "Decoded content from base64")
        else:
            body = content.encode(encoding) if isinstance(content, str) else content
            log_info("task", "run", "encoding", f"Encoded content as {encoding}")

        put_kwargs = {
            "Bucket": bucket,
            "Key": key,
            "Body": body,
            "ContentType": content_type,
        }
        if metadata:
            put_kwargs["Metadata"] = {str(k): str(v) for k, v in metadata.items()}
        if acl:
            put_kwargs["ACL"] = acl

        log_info("task", "run", "put_object_start",
                 f"Uploading {len(body)} bytes to s3://{bucket}/{key} "
                 f"(content_type={content_type})")

        response = client.put_object(**put_kwargs)
        etag = response.get("ETag", "").strip('"')

        log_info("task", "run", "put_object_success",
                 f"Uploaded to s3://{bucket}/{key}, ETag={etag}")

        return {
            "execution_type": "sync",
            "status": "success",
            "result": {
                "bucket": bucket,
                "key": key,
                "etag": etag,
                "bytes_written": len(body),
                "content_type": content_type
            }
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "put_object_failed", f"({error_code}) {error_msg}")
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
             "S3 create object is synchronous - already complete")
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
                     f"s3://{output.get('bucket')}/{output.get('key')} | "
                     f"{output.get('bytes_written')} bytes | ETag={output.get('etag')}")
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

payload = '{"bucket": "my-bucket", "key": "data/hello.txt", "content": "Hello, World!", "encoding": "utf-8", "content_type": "text/plain"}'

prompt = (
    "Upload an object to S3 using put_object. Required payload: bucket, key, content. "
    "Optional: encoding (utf-8 or base64, default utf-8), content_type (default application/octet-stream), "
    "metadata (dict), acl (string). "
    "If encoding=base64, base64-decode content before uploading. "
    "Auth: IAM role first via STS, fallback to access keys from connection. "
    "Return bucket, key, etag, bytes_written, and content_type on success."
)

install_docs = """# AWSS3CreateObject — Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": ["arn:aws:s3:::your-bucket/*"]
    }

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance — no keys needed in connection    |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
"""

guide_docs = """# AWSS3CreateObject — Operator Guide

## What it does

Creates or uploads an object to an S3 bucket using put_object. Accepts content as a UTF-8
string (default) or base64-encoded bytes. Supports optional ContentType, user-defined metadata,
and ACL.

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

    {
      "bucket":       "my-bucket",
      "key":          "data/hello.txt",
      "content":      "Hello, World!",
      "encoding":     "utf-8",
      "content_type": "text/plain",
      "metadata":     {"source": "pipeline"},
      "acl":          "private"
    }

| Field        | Required | Description                                                          |
|--------------|----------|----------------------------------------------------------------------|
| bucket       | Yes      | Target S3 bucket                                                     |
| key          | Yes      | Full S3 key (path + filename)                                        |
| content      | Yes      | Object content as string                                             |
| encoding     | No       | utf-8 (default) or base64 — how to interpret content                 |
| content_type | No       | MIME type (default: application/octet-stream)                        |
| metadata     | No       | Dict of user-defined metadata key-value pairs                        |
| acl          | No       | S3 canned ACL (e.g. private, public-read). Omit for bucket default.  |

---

## Output (on success)

    {
      "bucket":        "my-bucket",
      "key":           "data/hello.txt",
      "etag":          "32e8455b31d487f301b2be2ed4a1697f",
      "bytes_written": 13,
      "content_type":  "text/plain"
    }

| Field         | Description                              |
|---------------|------------------------------------------|
| bucket        | Bucket the object was written to         |
| key           | Full S3 key of the created object        |
| etag          | MD5 ETag of the uploaded content         |
| bytes_written | Number of bytes uploaded                 |
| content_type  | Content-Type set on the object           |

---

## Scenarios and Edge Cases

Key already exists:
  put_object overwrites silently. No error is returned. Use AWSS3CopyObjectV2 with
  override=false if you want explicit protection against overwrites.

Binary content:
  Set encoding=base64 and pass the base64-encoded string as content.

Large objects (>5 GB):
  put_object supports up to 5 GB. For larger objects, use multipart upload instead.

---

## What this operator does NOT do

- Does not check if the key already exists before writing
- Does not support multipart upload for objects larger than 5 GB
- Does not set server-side encryption — configure at the bucket level
"""

description = """
Uploads an object directly to S3 using put_object, supporting both UTF-8 string content and
base64-encoded binary payloads. Accepts optional ContentType, user-defined metadata key-value
pairs, and S3 canned ACLs. Overwrites silently if the key already exists — use AWSS3CopyObjectV2
with override=false if explicit overwrite protection is needed. Auth: IAM role via STS first,
fallback to flat access keys in connection. Returns bucket, key, etag, bytes_written, and
content_type on success.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "S3",
    "category": "Storage",
    "tags": ["s3", "object", "upload", "create", "aws"],
    "airflow_equivalent": "S3CreateObjectOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

If an object with the same key already exists, it is silently overwritten — there is no conflict check. For versioned buckets, a new version is created rather than overwriting. content is stored as-is; if encoding is set to base64 the content is decoded first. Large objects (>5 MB) should use multipart upload — this operator is not suitable for very large files.
"""

