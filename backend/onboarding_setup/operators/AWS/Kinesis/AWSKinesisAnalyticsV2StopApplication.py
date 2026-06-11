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
import time
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from src.common.logger.logger import log_info, log_error


def _build_kinesisanalytics_client(connection: dict):
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
        return session.client("kinesisanalyticsv2")

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
        return session.client("kinesisanalyticsv2")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info("task", "initialize", "auth_default",
             "Using default AWS credential chain (instance profile / ECS task role / env / config)")
    return boto3.Session(region_name=region).client("kinesisanalyticsv2")


def initialize(least_action_task_object):
    try:
        connection = least_action_task_object.get("connection", {})
        if isinstance(connection, str):
            connection = json.loads(connection)

        log_info("task", "initialize", "building_client",
                 f"region={connection.get('region', 'us-east-1')}")

        client = _build_kinesisanalytics_client(connection)
        client.list_applications(Limit=1)
        log_info("task", "initialize", "connectivity_ok",
                 "KinesisAnalyticsV2 client initialized and verified")
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

        app_name = payload.get("application_name")
        if not app_name:
            msg = "Missing required payload field: application_name"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "async", "status": "failed", "result": {"error": msg}}

        force = bool(payload.get("force", False))
        poll_interval = int(payload.get("poll_interval_seconds", 15))

        desc = client.describe_application(ApplicationName=app_name)
        detail = desc["ApplicationDetail"]
        current_status = detail.get("ApplicationStatus")
        app_arn = detail.get("ApplicationARN")

        log_info("task", "run", "current_status",
                 f"Application '{app_name}' current status: {current_status}")

        if current_status == "READY":
            log_info("task", "run", "already_stopped",
                     f"Application '{app_name}' is already READY, skipping stop")
            return {
                "execution_type": "async",
                "status": "success",
                "result": {
                    "application_name": app_name,
                    "application_arn": app_arn,
                    "application_status": "READY",
                }
            }

        log_info("task", "run", "stopping_application",
                 f"Stopping KDA V2 application '{app_name}' (force={force})")
        client.stop_application(ApplicationName=app_name, Force=force)

        while True:
            desc = client.describe_application(ApplicationName=app_name)
            status = desc["ApplicationDetail"].get("ApplicationStatus")
            log_info("task", "run", "polling_status",
                     f"Application '{app_name}' status: {status}")
            if status == "READY":
                return {
                    "execution_type": "async",
                    "status": "success",
                    "result": {
                        "application_name": app_name,
                        "application_arn": app_arn,
                        "application_status": status,
                    }
                }
            if status not in {"STOPPING", "READY"}:
                return {
                    "execution_type": "async",
                    "status": "failed",
                    "result": {
                        "application_name": app_name,
                        "application_arn": app_arn,
                        "application_status": status,
                        "error": f"Unexpected terminal status: {status}",
                    }
                }
            time.sleep(poll_interval)

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "client_error", f"({error_code}) {error_msg}")
        return {"execution_type": "async", "status": "failed",
                "result": {"error": f"({error_code}) {error_msg}"}}
    except BotoCoreError as e:
        log_error("task", "run", "transport_error", f"BotoCoreError: {str(e)}")
        return {"execution_type": "async", "status": "failed",
                "result": {"error": f"Transport error: {str(e)}"}}
    except Exception as e:
        log_error("task", "run", "run_failed", f"Unexpected error: {str(e)}")
        return {"execution_type": "async", "status": "failed", "result": {"error": str(e)}}


def check_completion(least_action_task_object, client, run_details):
    try:
        if run_details.get("status") in ("success", "failed"):
            return {
                "status": run_details["status"],
                "message": "KDA application stop completed",
                "output": run_details.get("result", {})
            }
        app_name = run_details.get("result", {}).get("application_name")
        desc = client.describe_application(ApplicationName=app_name)
        status = desc["ApplicationDetail"].get("ApplicationStatus")
        log_info("task", "check_completion", "polling_status",
                 f"Application '{app_name}' status: {status}")
        if status == "READY":
            return {"status": "success", "message": "Application is READY (stopped)",
                    "output": {"application_name": app_name, "application_status": status}}
        if status == "STOPPING":
            return {"status": "pending", "message": "Application is STOPPING",
                    "output": {"application_status": status}}
        return {"status": "failed", "message": f"Unexpected status: {status}",
                "output": {"application_status": status}}
    except Exception as e:
        log_error("task", "check_completion", "error", f"Error: {str(e)}")
        return {"status": "failed", "message": str(e), "output": None}


def finish(least_action_task_object, client, completion_details, run_details):
    try:
        task_laui = least_action_task_object.get("laui", "unknown")
        status = completion_details.get("status", "unknown")
        log_info("task", "finish", "final_status",
                 f"Task {task_laui} completed with status: {status}")
        if status == "success":
            output = completion_details.get("output", {})
            log_info("task", "finish", "application_summary",
                     f"Application {output.get('application_name')} "
                     f"status={output.get('application_status')}")
        else:
            log_error("task", "finish", "operation_failed",
                      completion_details.get("message", "No message"))
        if client:
            try:
                client.close()
                log_info("task", "finish", "client_closed", "boto3 client closed successfully")
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
    "application_name": "my-kda-app",
}

prompt = (
    "Create an operator that stops an Amazon Kinesis Data Analytics V2 application and polls "
    "until READY. If already READY, return success immediately. "
    "Required payload: application_name. "
    "Optional: force (bool, default false), poll_interval_seconds (default 15). "
    "Auth: try IAM role via STS first; if unavailable, fall back to access keys from connection. "
    "Return application_name, application_arn, application_status. "
    "Catch all AWS errors and return them as status:failed - never raise."
)

install_docs = """# AWSKinesisAnalyticsV2StopApplication - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "kinesisanalyticsv2:StopApplication",
        "kinesisanalyticsv2:DescribeApplication",
        "kinesisanalyticsv2:ListApplications"
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

guide_docs = """# AWSKinesisAnalyticsV2StopApplication - Operator Guide

## What it does

Stops an Amazon Kinesis Data Analytics V2 application and polls every 15 seconds until it reaches
READY status. If the application is already READY (stopped), returns success immediately without
calling stop_application. Supports force stop to immediately terminate without snapshot.
Equivalent to Airflow's KinesisAnalyticsV2StopApplicationOperator.

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
      "application_name": "my-kda-app"
    }

| Field                 | Required | Description                                                      |
|-----------------------|----------|------------------------------------------------------------------|
| application_name      | Yes      | Name of the KDA application to stop                             |
| force                 | No       | If true, force-stops without saving snapshot (default: false)   |
| poll_interval_seconds | No       | Polling interval in seconds (default: 15)                       |

---

## Output (on success)

    {
      "application_name": "my-kda-app",
      "application_arn": "arn:aws:kinesisanalyticsv2:us-east-1:123456789012:application/my-kda-app",
      "application_status": "READY"
    }

---

## What this operator does NOT do

- Does not delete the application — use AWS Console or a separate delete operator
- Does not save application state unless force=false (default) allows graceful shutdown with snapshot
"""

description = """
Stops an Amazon Kinesis Data Analytics V2 application and polls every 15 seconds until READY.
If already READY, returns success immediately. Supports force stop (no snapshot).
Equivalent to Airflow's KinesisAnalyticsV2StopApplicationOperator. Required: application_name.
Optional: force (bool, default false), poll_interval_seconds (default 15).
Auth: IAM role via STS first, fallback to access keys. Returns application_name, application_arn,
application_status.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "KinesisAnalyticsV2",
    "category": "Streaming",
    "tags": ["kinesis", "kda", "streaming", "flink", "aws", "stop"],
    "airflow_equivalent": "KinesisAnalyticsV2StopApplicationOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

The application must be in RUNNING state. `force=true` terminates the application immediately without saving a snapshot — use only when graceful stop is not possible, as unsaved Flink state will be lost. The operator polls until the application reaches READY state. Stopping incurs no streaming charges but the application configuration is preserved.
"""

