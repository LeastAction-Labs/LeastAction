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


def _build_glue_client(connection: dict):
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
        return session.client("glue")

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
        return session.client("glue")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info("task", "initialize", "auth_default",
             "Using default AWS credential chain (instance profile / ECS task role / env / config)")
    return boto3.Session(region_name=region).client("glue")


def initialize(least_action_task_object):
    try:
        connection = least_action_task_object.get("connection", {})
        if isinstance(connection, str):
            connection = json.loads(connection)

        log_info("task", "initialize", "building_client",
                 f"region={connection.get('region', 'us-east-1')}")

        client = _build_glue_client(connection)
        client.list_jobs(MaxResults=1)
        log_info("task", "initialize", "connectivity_ok",
                 "Glue client initialized and verified")
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

        job_name = payload.get("job_name")
        if not job_name:
            msg = "Missing required payload field: job_name"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        params = {"JobName": job_name}
        if "arguments" in payload and isinstance(payload["arguments"], dict):
            params["Arguments"] = payload["arguments"]
        if "worker_type" in payload:
            params["WorkerType"] = payload["worker_type"]
        if "number_of_workers" in payload:
            params["NumberOfWorkers"] = payload["number_of_workers"]
        if "timeout" in payload:
            params["Timeout"] = payload["timeout"]
        if "security_configuration" in payload:
            params["SecurityConfiguration"] = payload["security_configuration"]

        log_info("task", "run", "starting_job", f"Starting Glue job: {job_name}")
        response = client.start_job_run(**params)
        job_run_id = response.get("JobRunId")

        log_info("task", "run", "job_submitted",
                 f"Job run {job_run_id} submitted, polling for SUCCEEDED state...")

        terminal_states = {"SUCCEEDED", "FAILED", "STOPPED", "TIMEOUT", "ERROR"}
        while True:
            run_resp = client.get_job_run(JobName=job_name, RunId=job_run_id)
            state = run_resp["JobRun"]["JobRunState"]
            log_info("task", "run", "polling_job_state", f"Job {job_run_id} state: {state}")
            if state == "SUCCEEDED":
                break
            if state in terminal_states:
                error_msg = run_resp["JobRun"].get("ErrorMessage", f"Job ended in state: {state}")
                return {
                    "execution_type": "sync",
                    "status": "failed",
                    "result": {"error": error_msg, "job_run_id": job_run_id, "state": state}
                }
            time.sleep(15)

        log_info("task", "run", "job_succeeded",
                 f"Glue job {job_name} run {job_run_id} succeeded")

        return {
            "execution_type": "sync",
            "status": "success",
            "result": {
                "job_name": job_name,
                "job_run_id": job_run_id,
                "state": "SUCCEEDED"
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
             "Glue StartJob is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "Glue job run completed",
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
                     f"Job {output.get('job_name')} run {output.get('job_run_id')} state={output.get('state')}")
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
    "job_name": "my-glue-etl-job"
}

prompt = (
    "Create an operator that starts an AWS Glue ETL job run and waits for it to complete. "
    "Required payload field: job_name. "
    "Optional: arguments (dict), worker_type, number_of_workers, timeout, security_configuration. "
    "Auth: try IAM role via STS first; if unavailable, fall back to access keys from connection. "
    "After calling start_job_run, poll get_job_run every 15 seconds until state is SUCCEEDED or "
    "a terminal failure state (FAILED, STOPPED, TIMEOUT, ERROR). "
    "Return job_name, job_run_id, and state=SUCCEEDED on success. "
    "Catch all AWS errors and return them as status:failed - never raise."
)

install_docs = """# AWSGlueStartJob - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "glue:StartJobRun",
        "glue:GetJobRun",
        "glue:ListJobs"
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

guide_docs = """# AWSGlueStartJob - Operator Guide

## What it does

Starts an AWS Glue ETL job run and polls synchronously every 15 seconds until the job reaches
SUCCEEDED or a terminal failure state. Supports custom arguments, worker configuration, and
execution timeout overrides per run.

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

    { "job_name": "my-glue-etl-job" }

| Field                  | Required | Description                                          |
|------------------------|----------|------------------------------------------------------|
| job_name               | Yes      | Name of the Glue job to run                          |
| arguments              | No       | Dict of job arguments (e.g. {"--key": "value"})      |
| worker_type            | No       | G.1X, G.2X, G.025X, Standard, Z.2X                  |
| number_of_workers      | No       | Number of workers to allocate                        |
| timeout                | No       | Max run duration in minutes                          |
| security_configuration | No       | Name of the security configuration to use            |

---

## Output (on success)

    {
      "job_name": "my-glue-etl-job",
      "job_run_id": "jr_abc123",
      "state": "SUCCEEDED"
    }

---

## What this operator does NOT do

- Does not create or update the Glue job definition
- Does not retrieve job metrics or CloudWatch logs
- Does not cancel a running job
"""

description = """
Starts an AWS Glue ETL job run and polls synchronously every 15 seconds until the job reaches
SUCCEEDED or a terminal failure state (FAILED, STOPPED, TIMEOUT, ERROR). Supports per-run
argument overrides, worker type and count configuration, and execution timeout. Auth: IAM role
via STS first, fallback to access keys. Returns job_name, job_run_id, and state=SUCCEEDED on success.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "Glue",
    "category": "Analytics",
    "tags": ["glue", "etl", "job", "spark", "aws"],
    "airflow_equivalent": "GlueJobOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

`arguments` keys must start with `--`. `worker_type` and `number_of_workers` override the job's default settings for this run. Terminal states: FAILED, STOPPED, TIMEOUT, ERROR. `timeout` in minutes caps the run — exceeded jobs enter TIMEOUT state.
"""

