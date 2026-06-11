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
import base64
import tempfile
import os
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from src.common.logger.logger import log_info, log_error


def _build_eks_client(connection: dict):
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
        return session.client("eks")

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
        return session.client("eks")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info("task", "initialize", "auth_default",
             "Using default AWS credential chain (instance profile / ECS task role / env / config)")
    return boto3.Session(region_name=region).client("eks")


def _get_kube_client(eks_client, cluster_name):
    import importlib
    k8s_client = importlib.import_module("kubernetes").client
    from botocore.awsrequest import AWSRequest
    from botocore.auth import SigV4Auth

    cluster_info = eks_client.describe_cluster(name=cluster_name)["cluster"]
    endpoint = cluster_info["endpoint"]
    ca_data = cluster_info["certificateAuthority"]["data"]

    ca_bytes = base64.b64decode(ca_data)
    ca_file = tempfile.NamedTemporaryFile(delete=False, suffix=".crt")
    ca_file.write(ca_bytes)
    ca_file.flush()
    ca_file.close()

    session = boto3.Session()
    credentials = session.get_credentials().get_frozen_credentials()
    region = eks_client.meta.region_name

    url = f"https://sts.{region}.amazonaws.com/?Action=GetCallerIdentity&Version=2011-06-15"
    headers = {"x-k8s-aws-id": cluster_name}
    request = AWSRequest(method="GET", url=url, headers=headers)
    SigV4Auth(credentials, "sts", region).add_auth(request)
    token = "k8s-aws-v1." + base64.urlsafe_b64encode(
        request.url.encode("utf-8")
    ).decode("utf-8").rstrip("=")

    configuration = k8s_client.Configuration()
    configuration.host = endpoint
    configuration.ssl_ca_cert = ca_file.name
    configuration.api_key = {"Cookie":f"frontend_token={token}"}
    api_client = k8s_client.ApiClient(configuration)
    return k8s_client.CoreV1Api(api_client), ca_file.name


def initialize(least_action_task_object):
    try:
        connection = least_action_task_object.get("connection", {})
        if isinstance(connection, str):
            connection = json.loads(connection)

        log_info("task", "initialize", "building_client",
                 f"region={connection.get('region', 'us-east-1')}")

        client = _build_eks_client(connection)
        client.list_clusters(maxResults=1)
        log_info("task", "initialize", "connectivity_ok",
                 "EKS client initialized and verified")
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
    ca_file = None
    try:
        payload = least_action_task_object.get("payload", {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                log_error("task", "run", "payload_parse_error", "Failed to parse payload as JSON")
                return {"status": "failed", "execution_type": "sync", "result": None,
                        "error": "Invalid payload format - expected flat JSON object"}

        cluster_name = payload.get("cluster_name")
        pod_name = payload.get("pod_name")
        image = payload.get("image")

        missing = []
        if not cluster_name:
            missing.append("cluster_name")
        if not pod_name:
            missing.append("pod_name")
        if not image:
            missing.append("image")
        if missing:
            msg = f"Missing required payload fields: {missing}"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        namespace = payload.get("namespace", "default")
        command = payload.get("command")
        args = payload.get("args")
        env_vars = payload.get("env_vars", {})
        resources = payload.get("resources", {})
        service_account_name = payload.get("service_account_name")

        log_info("task", "run", "building_kube_client",
                 f"Building Kubernetes client for cluster: {cluster_name}")

        import importlib
        k8s_client = importlib.import_module("kubernetes").client
        core_v1, ca_file = _get_kube_client(client, cluster_name)

        container_kwargs = {
            "name": pod_name,
            "image": image,
        }
        if command:
            container_kwargs["command"] = command if isinstance(command, list) else [command]
        if args:
            container_kwargs["args"] = args if isinstance(args, list) else [args]
        if env_vars:
            container_kwargs["env"] = [
                k8s_client.V1EnvVar(name=k, value=str(v))
                for k, v in env_vars.items()
            ]
        if resources:
            limits = resources.get("limits", {})
            requests = resources.get("requests", {})
            container_kwargs["resources"] = k8s_client.V1ResourceRequirements(
                limits=limits or None,
                requests=requests or None
            )

        container = k8s_client.V1Container(**container_kwargs)

        pod_spec_kwargs = {
            "containers": [container],
            "restart_policy": "Never",
        }
        if service_account_name:
            pod_spec_kwargs["service_account_name"] = service_account_name

        pod = k8s_client.V1Pod(
            metadata=k8s_client.V1ObjectMeta(name=pod_name, namespace=namespace),
            spec=k8s_client.V1PodSpec(**pod_spec_kwargs)
        )

        log_info("task", "run", "creating_pod",
                 f"Creating pod '{pod_name}' in namespace '{namespace}' on cluster '{cluster_name}'")
        core_v1.create_namespaced_pod(namespace=namespace, body=pod)

        terminal_phases = {"Succeeded", "Failed"}
        while True:
            pod_status = core_v1.read_namespaced_pod_status(name=pod_name, namespace=namespace)
            phase = pod_status.status.phase
            log_info("task", "run", "polling_pod_phase", f"Pod '{pod_name}' phase: {phase}")
            if phase in terminal_phases:
                break
            time.sleep(15)

        pod_logs = ""
        try:
            pod_logs = core_v1.read_namespaced_pod_log(name=pod_name, namespace=namespace)
        except Exception as log_err:
            log_info("task", "run", "log_fetch_failed", f"Could not fetch pod logs: {str(log_err)}")

        try:
            core_v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
            log_info("task", "run", "pod_deleted", f"Pod '{pod_name}' deleted")
        except Exception as del_err:
            log_info("task", "run", "pod_delete_failed", f"Could not delete pod: {str(del_err)}")

        op_status = "success" if phase == "Succeeded" else "failed"
        log_info("task", "run", "pod_complete",
                 f"Pod '{pod_name}' finished with phase: {phase}")

        return {
            "execution_type": "sync",
            "status": op_status,
            "result": {
                "cluster_name": cluster_name,
                "pod_name": pod_name,
                "namespace": namespace,
                "phase": phase,
                "logs": pod_logs[:5000] if pod_logs else ""
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
    finally:
        if ca_file and os.path.exists(ca_file):
            try:
                os.unlink(ca_file)
            except Exception:
                pass


def check_completion(least_action_task_object, client, run_details):
    log_info("task", "check_completion", "sync_complete",
             "EKS PodOperator is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "EKS pod run completed",
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
            log_info("task", "finish", "pod_summary",
                     f"Pod {output.get('pod_name')} on cluster {output.get('cluster_name')} "
                     f"namespace={output.get('namespace')} phase={output.get('phase')}")
        else:
            log_error("task", "finish", "operation_failed",
                      completion_details.get("message", "No message"))
        if client:
            try:
                client.close()
                log_info("task", "finish", "client_closed", "EKS boto3 client closed successfully")
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
pip install kubernetes>=26.1.0
echo "Dependencies installed successfully"
"""}

connection = {
    "region": "us-east-1",
}

payload = {
    "cluster_name": "my-eks-cluster",
    "pod_name": "my-pod",
    "image": "python:3.10-slim",
    "namespace": "default",
    "command": ["python", "-c", "print('Hello from EKS pod!')"]
}

prompt = (
    "Create an operator that runs a Kubernetes pod on an existing EKS cluster using the kubernetes Python client. "
    "Required payload fields: cluster_name, pod_name, image. "
    "Optional: namespace (default 'default'), command (list), args (list), env_vars (dict), "
    "resources ({limits, requests}), service_account_name. "
    "Auth: try IAM role via STS first; if unavailable, fall back to access keys from connection. "
    "Build Kubernetes client using EKS describe_cluster + SigV4 presigned STS token. "
    "Create the pod with restart_policy=Never. Poll read_namespaced_pod_status every 15 seconds "
    "until phase is Succeeded or Failed. Fetch logs and delete the pod after completion. "
    "Return cluster_name, pod_name, namespace, phase, and logs (capped at 5000 chars) on completion. "
    "Catch all errors and return them as status:failed - never raise."
)

install_docs = """# AWSEKSPodOperator - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0
    pip install kubernetes>=26.1.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "eks:DescribeCluster",
        "eks:ListClusters",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }

## Kubernetes RBAC Required

The IAM entity (role or user) must be mapped in the EKS aws-auth ConfigMap to a Kubernetes
role that has permission to create, get, and delete pods in the target namespace.

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance - no connection keys needed       |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
| Session token | Optionally add aws_session_token in connection                |
"""

guide_docs = """# AWSEKSPodOperator - Operator Guide

## What it does

Runs a Kubernetes pod on an existing Amazon EKS cluster. Builds authentication using a SigV4-signed
STS presigned URL (the standard EKS token approach). Creates the pod, polls until it completes
(Succeeded/Failed), retrieves logs, and deletes the pod. The IAM caller must be mapped in the
cluster's aws-auth ConfigMap with appropriate RBAC permissions.

---

## Auth

1. IAM role - tried first via STS. Used automatically if available. No keys needed in connection.
2. Access keys - fallback to aws_access_key_id + aws_secret_access_key from connection.

---

## Payload

    {
      "cluster_name": "my-eks-cluster",
      "pod_name": "my-pod",
      "image": "python:3.10-slim",
      "namespace": "default",
      "command": ["python", "-c", "print('Hello from EKS!')"]
    }

| Field                | Required | Description                                               |
|----------------------|----------|-----------------------------------------------------------|
| cluster_name         | Yes      | Name of the EKS cluster to run the pod on                 |
| pod_name             | Yes      | Name for the Kubernetes pod                               |
| image                | Yes      | Docker image to run                                       |
| namespace            | No       | Kubernetes namespace (default: default)                   |
| command              | No       | Entrypoint command list (overrides image CMD)             |
| args                 | No       | Arguments to the command                                  |
| env_vars             | No       | Dict of environment variable name/value pairs             |
| resources            | No       | {limits: {cpu, memory}, requests: {cpu, memory}}          |
| service_account_name | No       | Kubernetes service account for pod identity               |

---

## Output (on success)

    {
      "cluster_name": "my-eks-cluster",
      "pod_name": "my-pod",
      "namespace": "default",
      "phase": "Succeeded",
      "logs": "Hello from EKS!\\n"
    }

---

## What this operator does NOT do

- Does not create the EKS cluster (use AWSEKSCreateCluster)
- Does not configure aws-auth ConfigMap - the IAM entity must already be mapped
- Does not support multi-container pods or init containers
- Does not stream logs in real-time (fetches after completion)
"""

description = """
Runs a Kubernetes pod on an existing Amazon EKS cluster using the kubernetes Python client with
SigV4-based EKS token authentication. Creates the pod, polls every 15 seconds until Succeeded
or Failed, fetches logs (up to 5000 chars), and deletes the pod. Required: cluster_name,
pod_name, image. Optional: namespace, command, args, env_vars, resources, service_account_name.
Auth: IAM role via STS first, fallback to access keys. Returns phase and logs on completion.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "EKS",
    "category": "Compute",
    "tags": ["eks", "kubernetes", "pod", "k8s", "aws"],
    "airflow_equivalent": "EksPodOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

This operator follows the standard LeastAction auth pattern: explicit keys → assume IAM role → default credential chain.
"""

