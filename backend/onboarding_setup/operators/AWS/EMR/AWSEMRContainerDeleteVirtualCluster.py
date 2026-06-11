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


def _build_emr_containers_client(connection: dict):
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
        return session.client("emr-containers")

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
        return session.client("emr-containers")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info("task", "initialize", "auth_default",
             "Using default AWS credential chain (instance profile / ECS task role / env / config)")
    return boto3.Session(region_name=region).client("emr-containers")


def initialize(least_action_task_object):
    try:
        connection = least_action_task_object.get("connection", {})
        if isinstance(connection, str):
            connection = json.loads(connection)

        log_info("task", "initialize", "building_client",
                 f"region={connection.get('region', 'us-east-1')}")

        client = _build_emr_containers_client(connection)
        client.list_virtual_clusters(maxResults=1)
        log_info("task", "initialize", "connectivity_ok",
                 "EMR Containers client initialized and verified")
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

        virtual_cluster_id = payload.get("virtual_cluster_id")
        if not virtual_cluster_id:
            msg = "Missing required payload field: virtual_cluster_id"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        log_info("task", "run", "deleting_virtual_cluster",
                 f"Deleting EMR virtual cluster {virtual_cluster_id}")

        client.delete_virtual_cluster(id=virtual_cluster_id)

        log_info("task", "run", "delete_initiated",
                 f"Delete initiated for virtual cluster {virtual_cluster_id}, polling for TERMINATED state...")

        while True:
            try:
                desc = client.describe_virtual_cluster(id=virtual_cluster_id)
                state = desc["virtualCluster"]["state"]
                log_info("task", "run", "polling_state",
                         f"Virtual cluster {virtual_cluster_id} state: {state}")
                if state == "TERMINATED":
                    break
                time.sleep(15)
            except ClientError as e:
                if e.response["Error"]["Code"] in ("ResourceNotFoundException", "ValidationException"):
                    log_info("task", "run", "cluster_gone",
                             f"Virtual cluster {virtual_cluster_id} no longer exists - deletion complete")
                    break
                raise

        log_info("task", "run", "delete_complete",
                 f"EMR virtual cluster {virtual_cluster_id} deleted")

        return {
            "execution_type": "sync",
            "status": "success",
            "result": {
                "virtual_cluster_id": virtual_cluster_id,
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
             "EMRContainerDeleteVirtualCluster is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "EMR on EKS virtual cluster deletion completed",
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
            log_info("task", "finish", "delete_summary",
                     f"Virtual cluster {output.get('virtual_cluster_id')} state={output.get('state')}")
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
    "virtual_cluster_id": "abc123xyz"
}

prompt = (
    "Create an operator that deletes an EMR on EKS virtual cluster and waits for it to reach TERMINATED state. "
    "Required payload field: virtual_cluster_id. "
    "Auth: try IAM role via STS first; if unavailable, fall back to access keys from connection. "
    "Use the emr-containers boto3 client. "
    "After calling delete_virtual_cluster, poll describe_virtual_cluster every 15 seconds. "
    "If the cluster reaches TERMINATED state or ResourceNotFoundException is raised, deletion is complete. "
    "Return virtual_cluster_id and state=TERMINATED on success. "
    "Catch all AWS errors and return them as status:failed - never raise."
)

install_docs = """# AWSEMRContainerDeleteVirtualCluster - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "emr-containers:DeleteVirtualCluster",
        "emr-containers:DescribeVirtualCluster",
        "emr-containers:ListVirtualClusters"
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

guide_docs = """# AWSEMRContainerDeleteVirtualCluster - Operator Guide

## What it does

Deletes an Amazon EMR on EKS virtual cluster and polls synchronously every 15 seconds until
the cluster reaches TERMINATED state or disappears. All job runs must complete before deletion.

---

## Auth

1. IAM role - tried first via STS. Used automatically if available. No keys needed in connection.
2. Access keys - fallback to aws_access_key_id + aws_secret_access_key from connection.

---

## Payload

    { "virtual_cluster_id": "abc123xyz" }

| Field              | Required | Description                                        |
|--------------------|----------|----------------------------------------------------|
| virtual_cluster_id | Yes      | ID of the EMR on EKS virtual cluster to delete     |

---

## Output (on success)

    {
      "virtual_cluster_id": "abc123xyz",
      "state": "TERMINATED"
    }

---

## What this operator does NOT do

- Does not cancel in-flight job runs (cancel those first)
- Does not delete the underlying EKS cluster or namespace
"""

description = """
Deletes an Amazon EMR on EKS virtual cluster and polls every 15 seconds until TERMINATED state
or ResourceNotFoundException confirms deletion is complete. Uses the emr-containers boto3 client.
Auth: IAM role via STS first, fallback to access keys. Returns virtual_cluster_id and
state=TERMINATED on success.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "EMR",
    "category": "BigData",
    "tags": ["emr", "eks", "kubernetes", "virtual-cluster", "delete", "aws"],
    "airflow_equivalent": "EmrEksDeleteClusterOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

The underlying EKS cluster and namespace are NOT deleted — only the EMR on EKS logical construct is removed. All running jobs must be cancelled before deletion. Deletion completes when the virtual cluster no longer exists (ResourceNotFoundException or ValidationException).
"""

