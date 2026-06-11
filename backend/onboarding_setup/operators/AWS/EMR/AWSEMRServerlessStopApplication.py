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

        application_id = payload.get("application_id")
        if not application_id:
            msg = "Missing required payload field: application_id"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        log_info("task", "run", "stopping_application",
                 f"Stopping EMR Serverless app: {application_id}")

        client.stop_application(applicationId=application_id)

        log_info("task", "run", "stop_initiated",
                 f"Stop signal sent for app {application_id}, polling for STOPPED state...")

        while True:
            state = client.get_application(applicationId=application_id)["application"]["state"]
            log_info("task", "run", "polling_app_state", f"App {application_id} state: {state}")
            if state in ("STOPPED", "TERMINATED"):
                break
            time.sleep(10)

        log_info("task", "run", "application_stopped",
                 f"Application {application_id} reached {state}")

        return {
            "execution_type": "sync",
            "status": "success",
            "result": {
                "application_id": application_id,
                "state": state
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
             "EMR Serverless StopApplication is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "EMR Serverless application stopped",
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
                     f"App {output.get('application_id')} state={output.get('state')}")
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
    "application_id": "00abc123"
}

prompt = (
    "Create an operator that stops an Amazon EMR Serverless application. "
    "Required payload field: application_id. "
    "Auth: try IAM role via STS first; if unavailable, fall back to access keys from connection. "
    "After calling stop_application, poll get_application every 10 seconds until state is STOPPED or TERMINATED. "
    "Note: the application must be in STARTING or STARTED state to be stopped — "
    "applications in CREATED state will fail with a validation error. "
    "Return application_id and final state on success. "
    "Catch all AWS errors and return them as status:failed - never raise."
)

install_docs = """# AWSEMRServerlessStopApplication - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "emr-serverless:StopApplication",
        "emr-serverless:GetApplication",
        "emr-serverless:ListApplications"
      ],
      "Resource": "*"
    }

## Prerequisites

The application must be in STARTING or STARTED state.
Applications in CREATED state cannot be stopped — they are already idle.

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance - no connection keys needed       |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
| Session token | Optionally add aws_session_token in connection                |
"""

guide_docs = """# AWSEMRServerlessStopApplication - Operator Guide

## What it does

Stops a running Amazon EMR Serverless application and polls synchronously until it reaches
STOPPED or TERMINATED state. Stopping an application releases its pre-initialized workers
and reduces costs when the application is not actively processing jobs.

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

    { "application_id": "00abc123" }

| Field          | Required | Description                          |
|----------------|----------|--------------------------------------|
| application_id | Yes      | ID of the EMR Serverless application |

---

## Output (on success)

    {
      "application_id": "00abc123",
      "state": "STOPPED"
    }

---

## Important Constraints

- Application must be in STARTING or STARTED state to be stopped
- Applications in CREATED state are already idle and cannot be stopped via this API
- To delete an application entirely, use AWSEMRServerlessDeleteApplication

---

## What this operator does NOT do

- Does not cancel running jobs before stopping (AWS handles graceful drain)
- Does not delete the application
- Does not work on applications in CREATED state
"""

description = """
Stops an Amazon EMR Serverless application and polls synchronously until it reaches STOPPED or
TERMINATED state. Stopping releases pre-initialized workers and reduces cost when the application
is idle. The application must be in STARTING or STARTED state — CREATED state apps are already
idle and cannot be stopped via this API. Auth: IAM role via STS first, fallback to access keys.
Returns application_id and final state on success.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "EMR",
    "category": "BigData",
    "tags": ["emr", "serverless", "stop", "aws"],
    "airflow_equivalent": "EmrServerlessStopApplicationOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

Application must be in STARTING or STARTED state. All running jobs must complete or be cancelled before the application can stop. Configuration is preserved for restart. Use `auto_stop_config` at creation time to automate this instead of manual stops.
"""

