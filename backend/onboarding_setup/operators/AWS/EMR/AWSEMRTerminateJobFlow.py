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

        job_flow_ids = payload.get("job_flow_ids") or (
            [payload["job_flow_id"]] if payload.get("job_flow_id") else None
        )

        if not job_flow_ids:
            msg = "Missing required payload field: job_flow_ids (list) or job_flow_id (string)"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        log_info("task", "run", "terminating_clusters",
                 f"Terminating {len(job_flow_ids)} cluster(s): {job_flow_ids}")

        client.terminate_job_flows(JobFlowIds=job_flow_ids)

        log_info("task", "run", "waiting_for_termination",
                 "Termination signal sent, waiting for all clusters to reach TERMINATED state...")

        waiter = client.get_waiter("cluster_terminated")
        for cluster_id in job_flow_ids:
            waiter.wait(ClusterId=cluster_id)
            log_info("task", "run", "cluster_terminated", f"Cluster {cluster_id} terminated")

        log_info("task", "run", "all_terminated",
                 f"All {len(job_flow_ids)} cluster(s) terminated successfully")

        return {
            "execution_type": "sync",
            "status": "success",
            "result": {
                "job_flow_ids": job_flow_ids,
                "clusters_terminated": len(job_flow_ids),
                "state": "TERMINATED"
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
             "EMR TerminateJobFlow is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "EMR cluster termination completed",
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
            log_info("task", "finish", "termination_summary",
                     f"{output.get('clusters_terminated')} cluster(s) terminated: {output.get('job_flow_ids')}")
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
    "job_flow_ids": ["j-XXXXXXXXXX"]
}

prompt = (
    "Create an operator that terminates one or more Amazon EMR clusters. "
    "Payload: job_flow_ids (list of cluster IDs) or job_flow_id (single cluster ID string). "
    "Auth: try IAM role via STS first; if unavailable, fall back to access keys from connection. "
    "Call terminate_job_flows with all cluster IDs, then use the cluster_terminated waiter "
    "for each cluster ID sequentially until all reach TERMINATED state. "
    "Return job_flow_ids, clusters_terminated count, and state=TERMINATED on success. "
    "Catch all AWS errors and return them as status:failed - never raise."
)

install_docs = """# AWSEMRTerminateJobFlow - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "elasticmapreduce:TerminateJobFlows",
        "elasticmapreduce:DescribeCluster",
        "elasticmapreduce:ListClusters"
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

guide_docs = """# AWSEMRTerminateJobFlow - Operator Guide

## What it does

Terminates one or more Amazon EMR clusters by sending a single TerminateJobFlows API call,
then waits synchronously for each cluster to reach TERMINATED state. Supports terminating
multiple clusters in a single operation.

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

    { "job_flow_ids": ["j-XXXXXXXXXX", "j-YYYYYYYYYY"] }

or for a single cluster:

    { "job_flow_id": "j-XXXXXXXXXX" }

| Field        | Required | Description                                          |
|--------------|----------|------------------------------------------------------|
| job_flow_ids | Either   | List of cluster IDs to terminate                     |
| job_flow_id  | Either   | Single cluster ID to terminate (converted to list)   |

---

## Output (on success)

    {
      "job_flow_ids": ["j-XXXXXXXXXX"],
      "clusters_terminated": 1,
      "state": "TERMINATED"
    }

---

## What this operator does NOT do

- Does not cancel running steps before termination (AWS handles graceful shutdown)
- Does not check whether termination protection is enabled (will fail if it is)
- Does not delete cluster logs from S3
"""

description = """
Terminates one or more Amazon EMR clusters and waits synchronously until all reach TERMINATED
state. Accepts either job_flow_ids (list) or job_flow_id (single string). Sends a single
TerminateJobFlows API call for all clusters, then waits on each using the cluster_terminated
waiter. Auth: IAM role via STS first, fallback to access keys. Returns job_flow_ids,
clusters_terminated count, and state=TERMINATED on success.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "EMR",
    "category": "BigData",
    "tags": ["emr", "cluster", "terminate", "shutdown", "aws"],
    "airflow_equivalent": "EmrTerminateJobFlowOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

Accepts a single `job_flow_id` string or a `job_flow_ids` list. Termination is irreversible — HDFS data is lost unless written to S3. Each cluster is terminated sequentially using the `cluster_terminated` waiter. Termination protection must be disabled on the cluster first.
"""

