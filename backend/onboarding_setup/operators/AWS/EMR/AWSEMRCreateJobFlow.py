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

        name = payload.get("name")
        release_label = payload.get("release_label")
        instances = payload.get("instances")

        if not all([name, release_label, instances]):
            msg = "Missing required payload fields: name, release_label, instances"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        params = {"Name": name, "ReleaseLabel": release_label, "Instances": instances}
        for src, dst in {
            "log_uri": "LogUri",
            "steps": "Steps",
            "bootstrap_actions": "BootstrapActions",
            "applications": "Applications",
            "configurations": "Configurations",
            "job_flow_role": "JobFlowRole",
            "service_role": "ServiceRole",
            "auto_scaling_role": "AutoScalingRole",
            "security_configuration": "SecurityConfiguration",
            "managed_scaling_policy": "ManagedScalingPolicy",
        }.items():
            if src in payload:
                params[dst] = payload[src]

        if "tags" in payload and isinstance(payload["tags"], dict):
            params["Tags"] = [{"Key": k, "Value": v} for k, v in payload["tags"].items()]

        log_info("task", "run", "creating_cluster",
                 f"Creating EMR cluster '{name}', release: {release_label}")

        response = client.run_job_flow(**params)
        job_flow_id = response["JobFlowId"]

        log_info("task", "run", "cluster_launched",
                 f"Cluster launched: {job_flow_id}, waiting for WAITING/RUNNING state...")

        waiter = client.get_waiter("cluster_running")
        waiter.wait(ClusterId=job_flow_id)

        desc = client.describe_cluster(ClusterId=job_flow_id)
        state = desc["Cluster"]["Status"]["State"]
        log_info("task", "run", "cluster_ready", f"Cluster {job_flow_id} is {state}")

        return {
            "execution_type": "sync",
            "status": "success",
            "result": {
                "job_flow_id": job_flow_id,
                "name": name,
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
             "EMR CreateJobFlow is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "EMR cluster creation completed",
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
                     f"Cluster {output.get('job_flow_id')} ({output.get('name')}) state={output.get('state')}")
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
    "name": "my-emr-cluster",
    "release_label": "emr-6.15.0",
    "instances": {
        "MasterInstanceType": "m5.xlarge",
        "SlaveInstanceType": "m5.xlarge",
        "InstanceCount": 2,
        "KeepJobFlowAliveWhenNoSteps": True,
        "Ec2SubnetId": "subnet-xxxxxxxx"
    },
    "job_flow_role": "EMR_EC2_DefaultRole",
    "service_role": "EMR_DefaultRole",
    "applications": [{"Name": "Spark"}],
    "tags": {"Project": "my-project", "Env": "dev"}
}

prompt = (
    "Create an operator that launches a new Amazon EMR cluster using the RunJobFlow API. "
    "Required payload fields: name, release_label, instances (dict with MasterInstanceType, SlaveInstanceType, InstanceCount, etc). "
    "Optional fields: log_uri, steps, bootstrap_actions, applications, configurations, job_flow_role, service_role, "
    "auto_scaling_role, security_configuration, managed_scaling_policy, tags (dict). "
    "Auth: try IAM role via STS first; if unavailable, fall back to aws_access_key_id and aws_secret_access_key from connection. "
    "After launching, use the cluster_running waiter to wait until the cluster reaches WAITING or RUNNING state. "
    "Return job_flow_id, name, and state on success. "
    "Catch all AWS errors and return them as status:failed - never raise."
)

install_docs = """# AWSEMRCreateJobFlow - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "elasticmapreduce:RunJobFlow",
        "elasticmapreduce:DescribeCluster",
        "elasticmapreduce:ListClusters",
        "iam:PassRole"
      ],
      "Resource": "*"
    }

## IAM Roles Required

Two EMR service roles must exist before running:

- **EMR_DefaultRole** — the EMR service role
- **EMR_EC2_DefaultRole** — the EC2 instance profile for cluster nodes

Create them with:

    aws emr create-default-roles

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance - no connection keys needed       |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
| Session token | Optionally add aws_session_token in connection                |
"""

guide_docs = """# AWSEMRCreateJobFlow - Operator Guide

## What it does

Launches a new Amazon EMR cluster using the RunJobFlow API and waits synchronously until the
cluster reaches WAITING or RUNNING state. Suitable for Spark, Hive, Hadoop, and other
distributed workloads that require a long-lived cluster.

---

## Auth

1. IAM role - tried first via STS. Used automatically if available. No keys needed in connection.
2. Access keys - fallback to aws_access_key_id + aws_secret_access_key from connection.

If neither is available, initialize() raises RuntimeError before run() is called.

---

## Connection

    {
      "region": "us-east-1",
      "aws_access_key_id": "AKIA...",    //optional - omit to use IAM role
      "aws_secret_access_key": "...",    //optional - omit to use IAM role
      "aws_session_token": ""            //optional - for temporary credentials
    }

| Field                 | Required | Description                                    |
|-----------------------|----------|------------------------------------------------|
| region                | Yes      | AWS region to launch the cluster in            |
| aws_access_key_id     | No       | Only needed if IAM role is not available        |
| aws_secret_access_key | No       | Only needed if IAM role is not available        |
| aws_session_token     | No       | For temporary/assumed-role credentials          |

---

## Payload

    {
      "name": "my-emr-cluster",
      "release_label": "emr-6.15.0",
      "instances": {
        "MasterInstanceType": "m5.xlarge",
        "SlaveInstanceType": "m5.xlarge",
        "InstanceCount": 2,
        "KeepJobFlowAliveWhenNoSteps": true,
        "Ec2SubnetId": "subnet-xxxxxxxx"
      },
      "job_flow_role": "EMR_EC2_DefaultRole",
      "service_role": "EMR_DefaultRole",
      "applications": [{"Name": "Spark"}],
      "tags": {"Project": "my-project"}
    }

| Field                   | Required | Description                                          |
|-------------------------|----------|------------------------------------------------------|
| name                    | Yes      | Display name for the cluster                         |
| release_label           | Yes      | EMR release version (e.g. emr-6.15.0)               |
| instances               | Yes      | Instance configuration dict                          |
| job_flow_role           | No       | EC2 instance profile (default: EMR_EC2_DefaultRole)  |
| service_role            | No       | EMR service role (default: EMR_DefaultRole)          |
| applications            | No       | List of apps to install (Spark, Hive, etc.)          |
| log_uri                 | No       | S3 URI for cluster logs                              |
| steps                   | No       | Steps to run at launch                               |
| bootstrap_actions       | No       | Bootstrap scripts to run on nodes                    |
| tags                    | No       | Dict of tag key-value pairs                          |

---

## Output (on success)

    {
      "job_flow_id": "j-XXXXXXXXXX",
      "name": "my-emr-cluster",
      "state": "WAITING"
    }

---

## What this operator does NOT do

- Does not add steps after launch (use AWSEMRAddSteps for that)
- Does not terminate the cluster (use AWSEMRTerminateJobFlow)
- Does not wait for steps — only waits for cluster to reach ready state
"""

description = """
Launches a new Amazon EMR cluster using the RunJobFlow API and waits synchronously until the
cluster reaches WAITING or RUNNING state. Supports full cluster configuration including
instance types, EMR release version, Spark/Hive/Hadoop applications, bootstrap actions,
IAM roles, S3 log URI, and tags. Auth: IAM role via STS first, fallback to access keys
in connection. Returns job_flow_id, name, and state on success.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "EMR",
    "category": "BigData",
    "tags": ["emr", "cluster", "create", "spark", "aws"],
    "airflow_equivalent": "EmrCreateJobFlowOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

`job_flow_role` is the EC2 instance profile (e.g. `EMR_EC2_DefaultRole`) and `service_role` is the EMR service role (e.g. `EMR_DefaultRole`) — both must exist before creating the cluster. Tags dict is auto-converted to `[{"Key":k,"Value":v}]` format. Cluster creation takes 5-10 minutes. `instances.MasterInstanceType` and either `instances.SlaveInstanceType` or `instances.InstanceGroups` are required inside the `instances` dict.
"""

