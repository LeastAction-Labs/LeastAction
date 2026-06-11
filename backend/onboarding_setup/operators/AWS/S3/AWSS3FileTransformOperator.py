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
import os
import subprocess
import tempfile
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
    tmp_input = None
    tmp_output = None
    try:
        payload = least_action_task_object.get("payload", {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                log_error("task", "run", "payload_parse_error", "Failed to parse payload as JSON")
                return {"status": "failed", "execution_type": "sync", "result": None,
                        "error": "Invalid payload format -- expected flat JSON object"}

        source_bucket = payload.get("source_bucket")
        source_key = payload.get("source_key")
        dest_bucket = payload.get("dest_bucket")
        dest_key = payload.get("dest_key")
        transform_script = payload.get("transform_script")

        missing = [f for f, v in [
            ("source_bucket", source_bucket),
            ("source_key", source_key),
            ("dest_bucket", dest_bucket),
            ("dest_key", dest_key),
            ("transform_script", transform_script),
        ] if not v]
        if missing:
            msg = f"Missing required payload fields: {missing}"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        # Download
        tmp_input = tempfile.NamedTemporaryFile(delete=False, suffix="_input")
        tmp_input.close()
        log_info("task", "run", "download_start",
                 f"Downloading s3://{source_bucket}/{source_key} -> {tmp_input.name}")
        client.download_file(source_bucket, source_key, tmp_input.name)
        log_info("task", "run", "download_complete",
                 f"Downloaded {os.path.getsize(tmp_input.name)} bytes")

        # Transform
        tmp_output = tempfile.NamedTemporaryFile(delete=False, suffix="_output")
        tmp_output.close()
        log_info("task", "run", "transform_start", f"Running transform: {transform_script}")

        with open(tmp_input.name, "rb") as stdin_f, open(tmp_output.name, "wb") as stdout_f:
            result = subprocess.run(
                transform_script,
                shell=True,
                stdin=stdin_f,
                stdout=stdout_f,
                stderr=subprocess.PIPE
            )

        if result.returncode != 0:
            stderr_msg = result.stderr.decode("utf-8", errors="replace").strip()
            msg = f"Transform script exited with code {result.returncode}: {stderr_msg}"
            log_error("task", "run", "transform_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        bytes_uploaded = os.path.getsize(tmp_output.name)
        log_info("task", "run", "transform_complete",
                 f"Transform complete, output size: {bytes_uploaded} bytes")

        # Upload
        log_info("task", "run", "upload_start",
                 f"Uploading {tmp_output.name} -> s3://{dest_bucket}/{dest_key}")
        client.upload_file(tmp_output.name, dest_bucket, dest_key)
        log_info("task", "run", "upload_complete",
                 f"Uploaded {bytes_uploaded} bytes to s3://{dest_bucket}/{dest_key}")

        return {
            "execution_type": "sync",
            "status": "success",
            "result": {
                "source_bucket": source_bucket,
                "source_key": source_key,
                "dest_bucket": dest_bucket,
                "dest_key": dest_key,
                "transform_script": transform_script,
                "bytes_uploaded": bytes_uploaded
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
    finally:
        for tmp in [tmp_input, tmp_output]:
            if tmp and os.path.exists(tmp.name):
                try:
                    os.unlink(tmp.name)
                    log_info("task", "run", "cleanup", f"Removed temp file: {tmp.name}")
                except Exception:
                    pass


def check_completion(least_action_task_object, client, run_details):
    log_info("task", "check_completion", "sync_complete",
             "S3 file transform is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "Synchronous S3 file transform completed",
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
                     f"s3://{output.get('source_bucket')}/{output.get('source_key')} "
                     f"-> [{output.get('transform_script')}] "
                     f"-> s3://{output.get('dest_bucket')}/{output.get('dest_key')} "
                     f"| {output.get('bytes_uploaded')} bytes")
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

payload = '{"source_bucket": "my-bucket", "source_key": "input/data.csv", "dest_bucket": "my-bucket", "dest_key": "output/data.csv", "transform_script": "tr \',\' \'\\t\'"}'

prompt = (
    "Download an S3 object, apply a shell transform command to it (stdin -> stdout), "
    "then re-upload the result to S3. "
    "Required payload: source_bucket, source_key, dest_bucket, dest_key, transform_script. "
    "Auth: IAM role first via STS, fallback to access keys from connection. "
    "If transform exits non-zero, return status:failed with stderr. "
    "Temp files are always cleaned up in finally block. "
    "Return source, dest, transform_script, and bytes_uploaded on success."
)

install_docs = """# AWSS3FileTransform -- Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": [
        "arn:aws:s3:::source-bucket/*",
        "arn:aws:s3:::dest-bucket/*"
      ]
    }

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance -- no keys needed in connection    |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
"""

guide_docs = """# AWSS3FileTransform -- Operator Guide

## What it does

Downloads a file from S3 to a temp location, runs a shell transform_script against it
(stdin -> stdout), then uploads the output back to S3. The temp files are cleaned up after
the run, even on failure.

---

## Auth

| Priority | Method |
|---|---|
| 1st | IAM role -- tried via STS. No keys needed in connection. |
| 2nd | aws_access_key_id + aws_secret_access_key from connection |

---

## Connection

Minimum (IAM role):

    {"region": "us-east-1"}

---

## Payload

    {
      "source_bucket":    "my-bucket",
      "source_key":       "input/data.csv",
      "dest_bucket":      "my-bucket",
      "dest_key":         "output/data.csv",
      "transform_script": "tr ',' '\\t'"
    }

| Field            | Required | Description                                                    |
|------------------|----------|----------------------------------------------------------------|
| source_bucket    | Yes      | Bucket to download from                                        |
| source_key       | Yes      | Key of the source object                                       |
| dest_bucket      | Yes      | Bucket to upload the transformed file to                       |
| dest_key         | Yes      | Key for the destination object                                 |
| transform_script | Yes      | Shell command to run. Reads from stdin, writes to stdout.      |

---

## Output (on success)

    {
      "source_bucket":    "my-bucket",
      "source_key":       "input/data.csv",
      "dest_bucket":      "my-bucket",
      "dest_key":         "output/data.csv",
      "transform_script": "tr ',' '\\t'",
      "bytes_uploaded":   1024
    }

---

## Notes

- The transform runs as: sh -c "<transform_script>"
- If the command exits non-zero, operator returns status:failed with stderr
- Temp files are always cleaned up, even on failure
- Source and dest can be the same or different bucket/key
"""

description = """
Downloads an S3 object to a local temp file, pipes it through a shell transform command
(stdin -> stdout), then re-uploads the result back to S3. Source and destination can be the
same or different bucket/key -- useful for in-place transforms such as CSV->TSV, compression,
or schema normalization. The transform runs via sh -c; a non-zero exit code returns
status:failed with stderr included. Temp files are always cleaned up in a finally block.
Auth: IAM role via STS first, fallback to flat access keys in connection. Returns source,
dest, transform_script, and bytes_uploaded on success.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "S3",
    "category": "Storage",
    "tags": ["s3", "transform", "etl", "file", "aws"],
    "airflow_equivalent": "S3FileTransformOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

The transform_script receives the source file content as stdin and must write the transformed content to stdout. The script runs inside the operator's execution environment -- ensure all dependencies are available. Large files may cause memory issues since the entire content is read into memory. The original source object is not modified.
"""

