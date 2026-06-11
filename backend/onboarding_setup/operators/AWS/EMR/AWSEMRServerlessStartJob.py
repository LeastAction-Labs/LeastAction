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
        execution_role_arn = payload.get("execution_role_arn")
        job_driver = payload.get("job_driver")

        if not all([application_id, execution_role_arn, job_driver]):
            msg = "Missing required payload fields: application_id, execution_role_arn, job_driver"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        params = {
            "applicationId": application_id,
            "executionRoleArn": execution_role_arn,
            "jobDriver": job_driver
        }
        for src, dst in {
            "name": "name",
            "configuration_overrides": "configurationOverrides",
            "client_token": "clientToken",
            "execution_timeout_minutes": "executionTimeoutMinutes",
        }.items():
            if src in payload:
                params[dst] = payload[src]

        if "tags" in payload and isinstance(payload["tags"], dict):
            params["tags"] = payload["tags"]

        log_info("task", "run", "starting_job",
                 f"Starting job on EMR Serverless app: {application_id}")

        response = client.start_job_run(**params)
        job_run_id = response.get("jobRunId")

        log_info("task", "run", "job_submitted",
                 f"Job run {job_run_id} submitted, polling for SUCCESS state...")

        terminal_states = {"SUCCESS", "FAILED", "CANCELLED"}
        while True:
            state = client.get_job_run(
                applicationId=application_id, jobRunId=job_run_id
            )["jobRun"]["state"]
            log_info("task", "run", "polling_job_state", f"Job {job_run_id} state: {state}")
            if state == "SUCCESS":
                break
            if state in terminal_states:
                return {
                    "execution_type": "sync",
                    "status": "failed",
                    "result": {"error": f"Job ended in state: {state}", "job_run_id": job_run_id}
                }
            time.sleep(15)

        log_info("task", "run", "job_succeeded",
                 f"Job {job_run_id} succeeded on app {application_id}")

        return {
            "execution_type": "sync",
            "status": "success",
            "result": {
                "job_run_id": job_run_id,
                "application_id": application_id,
                "state": "SUCCESS"
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
             "EMR Serverless StartJob is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "EMR Serverless job completed",
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
            log_info("task", "finish", "job_summary",
                     f"Job {output.get('job_run_id')} on app {output.get('application_id')} "
                     f"state={output.get('state')}")
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
    "application_id": "00abc123",
    "execution_role_arn": "arn:aws:iam::123456789012:role/EMRServerlessExecutionRole",
    "job_driver": {
        "sparkSubmit": {
            "entryPoint": "s3://my-bucket/script.py",
            "entryPointArguments": [],
            "sparkSubmitParameters": "--conf spark.executor.cores=2 --conf spark.executor.memory=4g"
        }
    }
}

prompt = (
    "Create an operator that starts a job run on an Amazon EMR Serverless application. "
    "Required payload fields: application_id, execution_role_arn, job_driver. "
    "Optional: name, configuration_overrides, client_token, execution_timeout_minutes, tags (dict). "
    "Auth: try IAM role via STS first; if unavailable, fall back to access keys from connection. "
    "After calling start_job_run, poll get_job_run every 15 seconds until state is SUCCESS or "
    "a terminal failure state (FAILED, CANCELLED). "
    "Return job_run_id, application_id, and state=SUCCESS on success. "
    "Catch all AWS errors and return them as status:failed - never raise."
)

install_docs = """# AWSEMRServerlessStartJob - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "emr-serverless:StartJobRun",
        "emr-serverless:GetJobRun",
        "emr-serverless:ListApplications",
        "iam:PassRole"
      ],
      "Resource": "*"
    }

## Prerequisites

- An EMR Serverless application must already exist and be in CREATED or STARTED state
- An IAM execution role with S3 read access and CloudWatch Logs write access

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance - no connection keys needed       |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
| Session token | Optionally add aws_session_token in connection                |
"""

guide_docs = """# AWSEMRServerlessStartJob - Operator Guide

## What it does

Starts a Spark or Hive job run on an existing EMR Serverless application and polls
synchronously every 15 seconds until the job reaches SUCCESS or a terminal failure state.
EMR Serverless auto-starts the application if it is in CREATED state before running the job.

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
      "application_id": "00abc123",
      "execution_role_arn": "arn:aws:iam::123456789012:role/EMRServerlessExecutionRole",
      "job_driver": {
        "sparkSubmit": {
          "entryPoint": "s3://my-bucket/script.py",
          "entryPointArguments": [],
          "sparkSubmitParameters": "--conf spark.executor.cores=2 --conf spark.executor.memory=4g"
        }
      }
    }

| Field                     | Required | Description                                          |
|---------------------------|----------|------------------------------------------------------|
| application_id            | Yes      | ID of the EMR Serverless application                 |
| execution_role_arn        | Yes      | IAM role ARN for job execution                       |
| job_driver                | Yes      | Job driver config (sparkSubmit or hive)              |
| name                      | No       | Display name for the job run                         |
| configuration_overrides   | No       | Spark/monitoring configuration overrides             |
| execution_timeout_minutes | No       | Max job run duration in minutes                      |
| tags                      | No       | Dict of tag key-value pairs                          |

---

## Output (on success)

    {
      "job_run_id": "xyz789abc",
      "application_id": "00abc123",
      "state": "SUCCESS"
    }

---

## What this operator does NOT do

- Does not create the application (use AWSEMRServerlessCreateApplication)
- Does not stop or delete the application after the job completes
- Does not retrieve job output or logs (access via CloudWatch or S3 log URI)
"""

description = """
Starts a Spark or Hive job run on an existing Amazon EMR Serverless application and polls
synchronously every 15 seconds until SUCCESS or a terminal failure state. EMR Serverless
auto-provisions compute capacity for each job — no cluster management required. Requires an
existing application and an IAM execution role. Auth: IAM role via STS first, fallback to
access keys. Returns job_run_id, application_id, and state=SUCCESS on success.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "EMR",
    "category": "BigData",
    "tags": ["emr", "serverless", "spark", "hive", "job", "aws"],
    "airflow_equivalent": "EmrServerlessStartJobOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

The application must be in STARTED state before submitting jobs — use `auto_start_config.enabled: true` on create (default). `execution_timeout_minutes` caps job runtime. Configure `configurationOverrides.monitoringConfiguration.s3MonitoringConfiguration` to persist logs to S3.
"""

