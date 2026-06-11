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


def _build_emr_client(connection: dict):
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
        return session.client("emr")

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
        return session.client("emr")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info("task", "initialize", "auth_default",
             "Using default AWS credential chain (instance profile / ECS task role / env / config)")
    return boto3.Session(region_name=region).client("emr")


def initialize(least_action_task_object):
    try:
        connection = least_action_task_object.get("connection", {})
        if isinstance(connection, str):
            connection = json.loads(connection)

        log_info("task", "initialize", "building_client",
                 f"region={connection.get('region', 'us-east-1')}")

        client = _build_emr_client(connection)
        client.list_clusters(ClusterStates=["WAITING"])
        log_info("task", "initialize", "connectivity_ok", "EMR client initialized and verified")
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

        job_flow_id = payload.get("job_flow_id")
        steps = payload.get("steps")

        if not job_flow_id or not steps:
            msg = "Missing required payload fields: job_flow_id, steps"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        log_info("task", "run", "adding_steps",
                 f"Adding {len(steps)} step(s) to cluster: {job_flow_id}")

        response = client.add_job_flow_steps(JobFlowId=job_flow_id, Steps=steps)
        step_ids = response.get("StepIds", [])

        log_info("task", "run", "steps_submitted",
                 f"Step IDs submitted: {step_ids}, waiting for all steps to complete...")

        waiter = client.get_waiter("step_complete")
        for step_id in step_ids:
            waiter.wait(ClusterId=job_flow_id, StepId=step_id)
            log_info("task", "run", "step_complete", f"Step {step_id} completed")

        log_info("task", "run", "all_steps_complete",
                 f"All {len(step_ids)} step(s) completed on cluster {job_flow_id}")

        return {
            "execution_type": "sync",
            "status": "success",
            "result": {
                "job_flow_id": job_flow_id,
                "step_ids": step_ids,
                "steps_completed": len(step_ids)
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
             "EMR AddSteps is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "EMR steps completed",
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
            log_info("task", "finish", "steps_summary",
                     f"Cluster {output.get('job_flow_id')}: {output.get('steps_completed')} step(s) "
                     f"completed. IDs: {output.get('step_ids')}")
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
    "job_flow_id": "j-XXXXXXXXXX",
    "steps": [
        {
            "Name": "my-spark-step",
            "ActionOnFailure": "CONTINUE",
            "HadoopJarStep": {
                "Jar": "command-runner.jar",
                "Args": ["spark-submit", "--class", "MyApp", "s3://my-bucket/app.jar"]
            }
        }
    ]
}

prompt = (
    "Create an operator that adds one or more steps to a running Amazon EMR cluster. "
    "Required payload fields: job_flow_id (cluster ID), steps (list of step dicts). "
    "Each step dict must have Name, ActionOnFailure, and HadoopJarStep with Jar and Args. "
    "Auth: try IAM role via STS first; if unavailable, fall back to access keys from connection. "
    "After submitting with add_job_flow_steps, use the step_complete waiter for each step_id sequentially. "
    "Return job_flow_id, step_ids, and steps_completed count on success. "
    "Catch all AWS errors and return them as status:failed - never raise."
)

install_docs = """# AWSEMRAddSteps - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "elasticmapreduce:AddJobFlowSteps",
        "elasticmapreduce:DescribeStep",
        "elasticmapreduce:ListClusters"
      ],
      "Resource": "*"
    }

## Prerequisites

The target EMR cluster must already exist and be in WAITING or RUNNING state.
Use AWSEMRCreateJobFlow to launch a cluster first.

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance - no connection keys needed       |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
| Session token | Optionally add aws_session_token in connection                |
"""

guide_docs = """# AWSEMRAddSteps - Operator Guide

## What it does

Adds one or more steps (e.g. Spark jobs, Hive queries, shell scripts) to a running Amazon EMR
cluster and waits synchronously until every submitted step reaches a terminal state.
Steps are waited on sequentially in submission order.

---

## Auth

1. IAM role - tried first via STS. Used automatically if available. No keys needed in connection.
2. Access keys - fallback to aws_access_key_id + aws_secret_access_key from connection.

---

## Connection

    {
      "region": "us-east-1",
      "aws_access_key_id": "AKIA...",//optional - omit to use IAM role
      "aws_secret_access_key": "...",//optional - omit to use IAM role
      "aws_session_token": ""//optional - omit to use IAM role
    }

---

## Payload

    {
      "job_flow_id": "j-XXXXXXXXXX",
      "steps": [
        {
          "Name": "my-spark-step",
          "ActionOnFailure": "CONTINUE",
          "HadoopJarStep": {
            "Jar": "command-runner.jar",
            "Args": ["spark-submit", "--class", "MyApp", "s3://my-bucket/app.jar"]
          }
        }
      ]
    }

| Field        | Required | Description                                           |
|--------------|----------|-------------------------------------------------------|
| job_flow_id  | Yes      | ID of the running EMR cluster (e.g. j-XXXXXXXXXX)    |
| steps        | Yes      | List of step dicts to submit                          |

### ActionOnFailure values

| Value             | Behavior                                        |
|-------------------|-------------------------------------------------|
| CONTINUE          | Cluster keeps running if this step fails        |
| TERMINATE_CLUSTER | Cluster terminates if this step fails           |
| CANCEL_AND_WAIT   | Cancel remaining steps, leave cluster running   |

---

## Output (on success)

    {
      "job_flow_id": "j-XXXXXXXXXX",
      "step_ids": ["s-XXXX", "s-YYYY"],
      "steps_completed": 2
    }

---

## What this operator does NOT do

- Does not launch or terminate the cluster
- Does not run steps in parallel - waits on each step sequentially
- Does not retry failed steps
"""

description = """
Adds one or more steps to a running Amazon EMR cluster and waits synchronously until all
submitted steps complete. Steps can be Spark jobs, Hive queries, shell scripts, or any
Hadoop-compatible workload expressed as a HadoopJarStep. Each step is waited on sequentially
using the step_complete waiter. Auth: IAM role via STS first, fallback to access keys.
Returns job_flow_id, step_ids, and steps_completed count on success.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "EMR",
    "category": "BigData",
    "tags": ["emr", "steps", "spark", "hive", "aws"],
    "airflow_equivalent": "EmrAddStepsOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

Steps run sequentially on the cluster. Each step is polled to completion using the `step_complete` waiter before moving to the next. `ActionOnFailure` in each step dict controls behavior on failure: CONTINUE, CANCEL_AND_WAIT, or TERMINATE_CLUSTER. The cluster must be in WAITING state to accept new steps.
"""

