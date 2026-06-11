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
        service_role = payload.get("service_execution_role")

        missing = []
        if not app_name:
            missing.append("application_name")
        if not service_role:
            missing.append("service_execution_role")
        if missing:
            msg = f"Missing required payload fields: {missing}"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        runtime = payload.get("runtime_environment", "FLINK-1_18")

        log_info("task", "run", "creating_application",
                 f"Creating KDA V2 application '{app_name}' with runtime={runtime}")

        params = {
            "ApplicationName": app_name,
            "RuntimeEnvironment": runtime,
            "ServiceExecutionRole": service_role,
        }
        if "application_configuration" in payload:
            params["ApplicationConfiguration"] = payload["application_configuration"]
        if "cloud_watch_logging_options" in payload:
            params["CloudWatchLoggingOptions"] = payload["cloud_watch_logging_options"]
        if "tags" in payload and isinstance(payload["tags"], dict):
            params["Tags"] = [{"Key": k, "Value": v} for k, v in payload["tags"].items()]

        resp = client.create_application(**params)
        detail = resp.get("ApplicationDetail", {})

        log_info("task", "run", "application_created",
                 f"Application '{app_name}' created with status={detail.get('ApplicationStatus')}")

        return {
            "execution_type": "sync",
            "status": "success",
            "result": {
                "application_name": detail.get("ApplicationName"),
                "application_arn": detail.get("ApplicationARN"),
                "application_status": detail.get("ApplicationStatus"),
                "application_version_id": detail.get("ApplicationVersionId"),
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


def check_completion(least_action_task_object, client, run_details):
    log_info("task", "check_completion", "sync_complete",
             "AWSKinesisAnalyticsV2CreateApplication is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "KDA application creation completed",
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
            log_info("task", "finish", "application_summary",
                     f"Application {output.get('application_name')} "
                     f"arn={output.get('application_arn')} "
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
    "service_execution_role": "arn:aws:iam::123456789012:role/KDAExecutionRole",
}

prompt = (
    "Create an operator that creates an Amazon Kinesis Data Analytics V2 application. "
    "Required payload: application_name, service_execution_role. "
    "Optional: runtime_environment (default FLINK-1_18), application_configuration (dict), "
    "cloud_watch_logging_options (list), tags (key-value dict). "
    "Auth: try IAM role via STS first; if unavailable, fall back to access keys from connection. "
    "Return application_name, application_arn, application_status, application_version_id. "
    "Catch all AWS errors and return them as status:failed - never raise."
)

install_docs = """# AWSKinesisAnalyticsV2CreateApplication - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "kinesisanalyticsv2:CreateApplication",
        "kinesisanalyticsv2:DescribeApplication",
        "iam:PassRole"
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

guide_docs = """# AWSKinesisAnalyticsV2CreateApplication - Operator Guide

## What it does

Creates an Amazon Kinesis Data Analytics V2 application with the specified runtime environment
(Flink or SQL). Supports optional application configuration, CloudWatch logging, and resource tags.
Equivalent to Airflow's KinesisAnalyticsV2CreateApplicationOperator.

This operator does NOT start the application — use AWSKinesisAnalyticsV2StartApplication after creation.

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
      "application_name": "my-kda-app",
      "service_execution_role": "arn:aws:iam::123456789012:role/KDAExecutionRole"
    }

| Field                        | Required | Description                                                        |
|------------------------------|----------|--------------------------------------------------------------------|
| application_name             | Yes      | Name of the KDA application to create                             |
| service_execution_role       | Yes      | IAM role ARN for the application to access AWS resources          |
| runtime_environment          | No       | Runtime: FLINK-1_18, FLINK-1_15, SQL-1_0 (default: FLINK-1_18)  |
| application_configuration    | No       | Application config dict (FlinkApplicationConfiguration, etc.)     |
| cloud_watch_logging_options  | No       | List of CloudWatch logging option dicts                           |
| tags                         | No       | Dict of tag key-value pairs to apply to the application           |

---

## Output (on success)

    {
      "application_name": "my-kda-app",
      "application_arn": "arn:aws:kinesisanalyticsv2:us-east-1:123456789012:application/my-kda-app",
      "application_status": "READY",
      "application_version_id": 1
    }

---

## What this operator does NOT do

- Does not start the application — pair with AWSKinesisAnalyticsV2StartApplication
- Does not configure VPC or custom Flink parallelism unless passed in application_configuration
"""

description = """
Creates an Amazon Kinesis Data Analytics V2 application (Flink or SQL runtime). Configures
application name, runtime, service execution role, and optional application configuration,
CloudWatch logging, and tags. Equivalent to Airflow's KinesisAnalyticsV2CreateApplicationOperator.
Required: application_name, service_execution_role. Optional: runtime_environment (default
FLINK-1_18), application_configuration, cloud_watch_logging_options, tags.
Auth: IAM role via STS first, fallback to access keys. Returns application_name, application_arn,
application_status, application_version_id.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "KinesisAnalyticsV2",
    "category": "Streaming",
    "tags": ["kinesis", "kda", "streaming", "flink", "sql", "aws"],
    "airflow_equivalent": "KinesisAnalyticsV2CreateApplicationOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

Creates a Kinesis Data Analytics (KDA) v2 application for streaming SQL or Apache Flink processing. `runtime_environment` defaults to FLINK-1_15 — ensure your `application_configuration` matches the runtime. `service_execution_role` must have permissions to read from source streams and write to destinations. Application creation is synchronous — the application is in READY state immediately.
"""

