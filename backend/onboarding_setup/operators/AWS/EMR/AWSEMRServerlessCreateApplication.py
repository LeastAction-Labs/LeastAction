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


def _build_emr_serverless_client(connection: dict):
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
        return session.client("emr-serverless")

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
        return session.client("emr-serverless")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info("task", "initialize", "auth_default",
             "Using default AWS credential chain (instance profile / ECS task role / env / config)")
    return boto3.Session(region_name=region).client("emr-serverless")


def initialize(least_action_task_object):
    try:
        connection = least_action_task_object.get("connection", {})
        if isinstance(connection, str):
            connection = json.loads(connection)

        log_info("task", "initialize", "building_client",
                 f"region={connection.get('region', 'us-east-1')}")

        client = _build_emr_serverless_client(connection)
        client.list_applications(maxResults=1)
        log_info("task", "initialize", "connectivity_ok",
                 "EMR Serverless client initialized and verified")
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

        name = payload.get("name")
        release_label = payload.get("release_label")

        if not all([name, release_label]):
            msg = "Missing required payload fields: name, release_label"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        params = {
            "name": name,
            "releaseLabel": release_label,
            "type": payload.get("type", "SPARK")
        }
        for src, dst in {
            "initial_capacity": "initialCapacity",
            "maximum_capacity": "maximumCapacity",
            "auto_start_config": "autoStartConfiguration",
            "auto_stop_config": "autoStopConfiguration",
            "network_config": "networkConfiguration",
            "client_token": "clientToken",
            "architecture": "architecture",
        }.items():
            if src in payload:
                params[dst] = payload[src]

        if "tags" in payload and isinstance(payload["tags"], dict):
            params["tags"] = payload["tags"]

        log_info("task", "run", "creating_application",
                 f"Creating EMR Serverless app '{name}', type={params['type']}, release={release_label}")

        response = client.create_application(**params)
        application_id = response.get("applicationId")
        arn = response.get("arn")

        log_info("task", "run", "application_created",
                 f"Application {application_id} created, polling for CREATED state...")

        while True:
            state = client.get_application(applicationId=application_id)["application"]["state"]
            log_info("task", "run", "polling_app_state", f"App {application_id} state: {state}")
            if state == "CREATED":
                break
            if state in ("TERMINATED", "STOPPED"):
                return {
                    "execution_type": "sync",
                    "status": "failed",
                    "result": {"error": f"App reached unexpected state: {state}", "application_id": application_id}
                }
            time.sleep(10)

        log_info("task", "run", "application_ready",
                 f"Application {application_id} is in CREATED state and ready")

        return {
            "execution_type": "sync",
            "status": "success",
            "result": {
                "application_id": application_id,
                "arn": arn,
                "state": "CREATED"
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
             "EMR Serverless CreateApplication is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "EMR Serverless application creation completed",
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
                     f"App {output.get('application_id')} state={output.get('state')} arn={output.get('arn')}")
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
    "name": "my-serverless-app",
    "release_label": "emr-6.15.0",
    "type": "SPARK"
}

prompt = (
    "Create an operator that creates an Amazon EMR Serverless application. "
    "Required payload fields: name, release_label. Optional: type (default SPARK), "
    "initial_capacity, maximum_capacity, auto_start_config, auto_stop_config, network_config, "
    "client_token, architecture, tags (dict). "
    "Auth: try IAM role via STS first; if unavailable, fall back to access keys from connection. "
    "After creating, poll get_application every 10 seconds until state is CREATED. "
    "Return application_id, arn, and state=CREATED on success. "
    "Catch all AWS errors and return them as status:failed - never raise."
)

install_docs = """# AWSEMRServerlessCreateApplication - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "emr-serverless:CreateApplication",
        "emr-serverless:GetApplication",
        "emr-serverless:ListApplications"
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

guide_docs = """# AWSEMRServerlessCreateApplication - Operator Guide

## What it does

Creates an Amazon EMR Serverless application and polls until it reaches CREATED state.
EMR Serverless applications are the compute containers that run Spark or Hive jobs without
requiring you to provision or manage clusters. Once created, use AWSEMRServerlessStartJob
to submit jobs to the application.

---

## Auth

1. IAM role - tried first via STS. Used automatically if available. No keys needed in connection.
2. Access keys - fallback to aws_access_key_id + aws_secret_access_key from connection.

---

## Connection

    {
      "region": "us-east-1",
      "aws_access_key_id": "AKIA...",    //optional - omit to use IAM role
      "aws_secret_access_key": "...",    //optional - omit to use IAM role
      "aws_session_token": ""            //optional - for temporary credentials
    }

---

## Payload

    {
      "name": "my-serverless-app",
      "release_label": "emr-6.15.0",
      "type": "SPARK"
    }

| Field            | Required | Description                                               |
|------------------|----------|-----------------------------------------------------------|
| name             | Yes      | Display name for the application                          |
| release_label    | Yes      | EMR release version (e.g. emr-6.15.0)                    |
| type             | No       | SPARK or HIVE (default: SPARK)                            |
| initial_capacity | No       | Pre-initialized worker capacity config                    |
| maximum_capacity | No       | Max vCPU, memory, disk limits                             |
| auto_start_config| No       | Auto-start settings                                       |
| auto_stop_config | No       | Auto-stop settings (idle timeout)                         |
| network_config   | No       | VPC/subnet config for private networking                  |
| architecture     | No       | X86_64 or ARM64                                           |
| tags             | No       | Dict of tag key-value pairs                               |

---

## Output (on success)

    {
      "application_id": "00abc123",
      "arn": "arn:aws:emr-serverless:us-east-1:123456789012:/applications/00abc123",
      "state": "CREATED"
    }

---

## What this operator does NOT do

- Does not start the application (it starts automatically when a job is submitted if auto_start is enabled)
- Does not submit jobs (use AWSEMRServerlessStartJob)
- Does not delete the application (use AWSEMRServerlessDeleteApplication)
"""

description = """
Creates an Amazon EMR Serverless application and polls synchronously until it reaches CREATED
state. EMR Serverless eliminates the need to provision or manage clusters — compute is allocated
automatically when jobs are submitted. Supports Spark and Hive workloads with optional VPC
networking, capacity limits, and auto-stop configuration. Auth: IAM role via STS first,
fallback to access keys. Returns application_id, ARN, and state=CREATED on success.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "EMR",
    "category": "BigData",
    "tags": ["emr", "serverless", "spark", "hive", "create", "aws"],
    "airflow_equivalent": "EmrServerlessCreateApplicationOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

Applications auto-scale workers on demand. `auto_stop_config` (default 15 min idle) controls cost — set `enabled: false` for always-on lower latency. `initial_capacity` pre-warms workers for faster first-job start. Type defaults to SPARK.
"""

