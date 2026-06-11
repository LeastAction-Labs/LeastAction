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

        name = payload.get("name")
        eks_cluster_name = payload.get("eks_cluster_name")
        eks_namespace = payload.get("eks_namespace")

        if not all([name, eks_cluster_name, eks_namespace]):
            msg = "Missing required payload fields: name, eks_cluster_name, eks_namespace"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        params = {
            "name": name,
            "containerProvider": {
                "type": "EKS",
                "id": eks_cluster_name,
                "info": {"eksInfo": {"namespace": eks_namespace}}
            }
        }
        if "client_token" in payload:
            params["clientToken"] = payload["client_token"]
        if "tags" in payload and isinstance(payload["tags"], dict):
            params["tags"] = payload["tags"]

        log_info("task", "run", "creating_virtual_cluster",
                 f"Creating EMR on EKS virtual cluster '{name}' "
                 f"linked to EKS cluster '{eks_cluster_name}', namespace '{eks_namespace}'")

        response = client.create_virtual_cluster(**params)
        virtual_cluster_id = response.get("id")
        arn = response.get("arn")

        log_info("task", "run", "virtual_cluster_created",
                 f"Virtual cluster created: id={virtual_cluster_id}, arn={arn}")

        return {
            "execution_type": "sync",
            "status": "success",
            "result": {
                "virtual_cluster_id": virtual_cluster_id,
                "name": response.get("name"),
                "arn": arn
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
             "EMR EksCreateCluster is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "EMR on EKS virtual cluster creation completed",
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
            log_info("task", "finish", "cluster_summary",
                     f"Virtual cluster '{output.get('name')}' created: "
                     f"id={output.get('virtual_cluster_id')}, arn={output.get('arn')}")
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
    "name": "my-emr-eks-cluster",
    "eks_cluster_name": "my-eks-cluster",
    "eks_namespace": "emr-jobs"
}

prompt = (
    "Create an operator that creates an Amazon EMR on EKS virtual cluster. "
    "Required payload fields: name, eks_cluster_name (the EKS cluster ID), eks_namespace. "
    "Optional: client_token, tags (dict). "
    "Auth: try IAM role via STS first; if unavailable, fall back to access keys from connection. "
    "Use the emr-containers boto3 client with create_virtual_cluster. "
    "This is a synchronous API - no polling needed. "
    "Return virtual_cluster_id, name, and arn on success. "
    "Catch all AWS errors and return them as status:failed - never raise."
)

install_docs = """# AWSEMREksCreateCluster - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "emr-containers:CreateVirtualCluster",
        "emr-containers:ListVirtualClusters"
      ],
      "Resource": "*"
    }

## Prerequisites

- An existing Amazon EKS cluster
- The target EKS namespace must already exist
- EMR on EKS service-linked role must be enabled in the account

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance - no connection keys needed       |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
| Session token | Optionally add aws_session_token in connection                |
"""

guide_docs = """# AWSEMREksCreateCluster - Operator Guide

## What it does

Creates an Amazon EMR on EKS virtual cluster by linking an EMR namespace to an existing
Amazon EKS cluster and namespace. The virtual cluster is the logical entity that represents
the EMR workload running on Kubernetes. This is a synchronous API call.

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
      "name": "my-emr-eks-cluster",
      "eks_cluster_name": "my-eks-cluster",
      "eks_namespace": "emr-jobs"
    }

| Field            | Required | Description                                           |
|------------------|----------|-------------------------------------------------------|
| name             | Yes      | Display name for the EMR virtual cluster              |
| eks_cluster_name | Yes      | Name/ID of the existing Amazon EKS cluster            |
| eks_namespace    | Yes      | Kubernetes namespace to link EMR to                   |
| client_token     | No       | Idempotency token for the request                     |
| tags             | No       | Dict of tag key-value pairs                           |

---

## Output (on success)

    {
      "virtual_cluster_id": "abc123xyz",
      "name": "my-emr-eks-cluster",
      "arn": "arn:aws:emr-containers:us-east-1:123456789012:/virtualclusters/abc123xyz"
    }

---

## What this operator does NOT do

- Does not create the EKS cluster or namespace (they must exist beforehand)
- Does not submit jobs (use AWSEMRContainerSubmitJob for that)
- Does not delete the virtual cluster
"""

description = """
Creates an Amazon EMR on EKS virtual cluster by linking an EMR namespace to an existing
Amazon EKS cluster and Kubernetes namespace. Uses the emr-containers boto3 client with the
CreateVirtualCluster API. This is a synchronous call with no polling required. Auth: IAM role
via STS first, fallback to access keys. Returns virtual_cluster_id, name, and ARN on success.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "EMR",
    "category": "BigData",
    "tags": ["emr", "eks", "kubernetes", "containers", "aws"],
    "airflow_equivalent": "EmrEksCreateClusterOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

Creates an EMR on EKS virtual cluster backed by an existing EKS cluster namespace. The EKS cluster must exist first. After creation, configure RBAC using `kubectl` to allow EMR to create and manage pods in the specified namespace. No polling needed — creation is synchronous.
"""

