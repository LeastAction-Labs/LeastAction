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

codeblock = {"main.py": '''"""
AWS EC2 Start Instance Operator

Starts one or more stopped EC2 instances.
Auth priority: explicit keys → assume IAM role → default credential chain.
Execution is async — run() triggers the start; check_completion() polls for running state.
"""

import json

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from src.common.logger.logger import log_error, log_info


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_ec2_client(connection: dict):
    region = connection.get("region", "us-east-1")
    access_key = connection.get("aws_access_key_id")
    secret_key = connection.get("aws_secret_access_key")
    session_token = connection.get("aws_session_token")
    assume_role_arn = connection.get("assume_iam_role")

    # Case 1: Explicit credentials
    if access_key and secret_key:
        log_info(
            "task", "initialize", "auth_keys",
            f"Using explicit access key ending ...{access_key[-4:]}"
        )
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token,
            region_name=region,
        )
        return session.client("ec2")

    # Case 2: Assume IAM role via STS
    if assume_role_arn:
        log_info(
            "task", "initialize", "auth_assume_role",
            f"Assuming IAM role: {assume_role_arn}"
        )
        sts = boto3.client("sts", region_name=region)
        assumed = sts.assume_role(
            RoleArn=assume_role_arn,
            RoleSessionName="leastaction_session",
        )
        creds = assumed["Credentials"]
        session = boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region,
        )
        return session.client("ec2")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info(
        "task", "initialize", "auth_default",
        "Using default AWS credential chain (instance profile / ECS task role / env / config)"
    )
    session = boto3.Session(region_name=region)
    return session.client("ec2")


# ---------------------------------------------------------------------------
# Operator methods
# ---------------------------------------------------------------------------

def initialize(least_action_task_object):
    """
    Build and verify the EC2 boto3 client.

    Returns:
        boto3 EC2 client
    """
    try:
        connection = least_action_task_object.get("connection", {})
        task_laui = least_action_task_object.get("laui")

        log_info(
            "task", "initialize", "start",
            f"Initializing EC2 start operator for task: {task_laui}"
        )

        ec2_client = _build_ec2_client(connection)

        region = connection.get("region", "us-east-1")
        log_info(
            "task", "initialize", "verify_connection",
            f"Verifying EC2 connectivity in region: {region}"
        )
        ec2_client.describe_regions(RegionNames=[region])

        log_info(
            "task", "initialize", "connection_established",
            f"EC2 client ready for region: {region}"
        )
        return ec2_client

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error(
            "task", "initialize", "client_error",
            f"AWS ClientError ({error_code}): {error_msg}"
        )
        raise
    except BotoCoreError as e:
        log_error(
            "task", "initialize", "botocore_error",
            f"BotoCoreError during initialization: {str(e)}"
        )
        raise
    except Exception as e:
        log_error(
            "task", "initialize", "unexpected_error",
            f"Unexpected error during initialization: {str(e)}"
        )
        raise


def run(least_action_task_object, client):
    """
    Start one or more EC2 instances using start_instances.

    Payload fields:
        instance_ids  (list[str], required)  -- list of instance IDs to start
        instance_id   (str)                  -- single instance ID, auto-wrapped in list
        dry_run       (bool, default False)  -- validate permissions without starting

    Returns:
        dict with status, execution_type="async", result, instance_ids
    """
    try:
        task_laui = least_action_task_object.get("laui")
        payload = least_action_task_object.get("payload", {})

        log_info(
            "task", "run", "extracting_payload",
            f"Extracting start configuration for task: {task_laui}"
        )

        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                log_error(
                    "task", "run", "payload_parse_error",
                    "Failed to parse payload as JSON"
                )
                return {
                    "status": "failed",
                    "execution_type": "async",
                    "result": None,
                    "error": "Invalid payload format — expected flat JSON object",
                }

        payload_data = payload

        # ---- Instance IDs ----
        instance_ids = payload_data.get("instance_ids")
        if not instance_ids:
            single = payload_data.get("instance_id")
            if not single:
                log_error(
                    "task", "run", "missing_instance_ids",
                    "instance_ids (or instance_id) is required in payload.data"
                )
                return {
                    "status": "failed",
                    "execution_type": "async",
                    "result": None,
                    "error": "instance_ids (or instance_id) is required in payload.data",
                }
            instance_ids = [single]

        if isinstance(instance_ids, str):
            instance_ids = [instance_ids]

        dry_run = bool(payload_data.get("dry_run", False))

        log_info(
            "task", "run", "starting_instances",
            f"Starting {len(instance_ids)} instance(s): {instance_ids} | dry_run={dry_run}"
        )

        start_params = {"InstanceIds": instance_ids}
        if dry_run:
            start_params["DryRun"] = True
            log_info("task", "run", "dry_run", "Dry run mode — no instance will actually be started")

        try:
            response = client.start_instances(**start_params)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "DryRunOperation":
                log_info(
                    "task", "run", "dry_run_success",
                    "Dry run succeeded — IAM permissions are sufficient"
                )
                return {
                    "status": "success",
                    "execution_type": "sync",
                    "result": {"dry_run": True, "message": "Dry run succeeded — permissions OK"},
                }
            raise

        starting = response.get("StartingInstances", [])
        for item in starting:
            log_info(
                "task", "run", "instance_state_transition",
                f"Instance {item['InstanceId']}: "
                f"{item.get('PreviousState', {}).get('Name')} → {item.get('CurrentState', {}).get('Name')}"
            )

        log_info(
            "task", "run", "start_issued",
            f"start_instances succeeded — {len(instance_ids)} instance(s) transitioning to running: {instance_ids}"
        )

        return {
            "status": "pending",
            "execution_type": "async",
            "result": {
                "instance_ids": instance_ids,
                "starting_instances": starting,
            },
            "instance_ids": instance_ids,
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error(
            "task", "run", "client_error",
            f"AWS ClientError ({error_code}): {error_msg}"
        )
        return {
            "status": "failed",
            "execution_type": "async",
            "result": None,
            "error": f"{error_code}: {error_msg}",
        }
    except Exception as e:
        log_error(
            "task", "run", "unexpected_error",
            f"Unexpected error during run: {str(e)}"
        )
        return {
            "status": "failed",
            "execution_type": "async",
            "result": None,
            "error": str(e),
        }


def check_completion(least_action_task_object, client, run_details):
    """
    Poll describe_instances to determine whether all instances are running.

    Returns:
        dict with status (success | pending | failed), message, output
    """
    try:
        if run_details.get("status") == "failed":
            log_error(
                "task", "check_completion", "run_phase_failed",
                f"Run phase reported failure: {run_details.get('error')}"
            )
            return {
                "status": "failed",
                "message": f"Start failed in run phase: {run_details.get('error')}",
                "output": None,
            }

        instance_ids = run_details.get("instance_ids", [])
        if not instance_ids:
            log_error(
                "task", "check_completion", "missing_instance_ids",
                "No instance IDs found in run_details — cannot poll status"
            )
            return {
                "status": "failed",
                "message": "No instance IDs available in run_details",
                "output": None,
            }

        log_info(
            "task", "check_completion", "polling_instance_status",
            f"Describing {len(instance_ids)} instance(s): {instance_ids}"
        )

        response = client.describe_instances(InstanceIds=instance_ids)

        instance_statuses = []
        all_running = True
        any_failed = False

        for reservation in response.get("Reservations", []):
            for inst in reservation.get("Instances", []):
                instance_id = inst.get("InstanceId")
                state = inst.get("State", {}).get("Name")
                state_code = inst.get("State", {}).get("Code")
                private_ip = inst.get("PrivateIpAddress")
                public_ip = inst.get("PublicIpAddress")

                status_entry = {
                    "instance_id": instance_id,
                    "state": state,
                    "state_code": state_code,
                    "instance_type": inst.get("InstanceType"),
                    "private_ip": private_ip,
                    "public_ip": public_ip,
                    "availability_zone": inst.get("Placement", {}).get("AvailabilityZone"),
                }
                instance_statuses.append(status_entry)

                log_info(
                    "task", "check_completion", "instance_state",
                    f"Instance {instance_id}: state={state} (code={state_code}) | "
                    f"private_ip={private_ip} | public_ip={public_ip}"
                )

                if state != "running":
                    all_running = False

                if state in ("terminated", "shutting-down"):
                    any_failed = True
                    log_error(
                        "task", "check_completion", "instance_in_failure_state",
                        f"Instance {instance_id} entered unexpected terminal state: {state}"
                    )

        if any_failed:
            return {
                "status": "failed",
                "message": "One or more instances entered a terminal state unexpectedly",
                "output": {"instance_statuses": instance_statuses},
            }
        elif all_running:
            log_info(
                "task", "check_completion", "all_instances_running",
                f"All {len(instance_statuses)} instance(s) are in running state"
            )
            return {
                "status": "success",
                "message": f"All {len(instance_statuses)} instance(s) are running",
                "output": {"instance_statuses": instance_statuses},
            }
        else:
            log_info(
                "task", "check_completion", "instances_still_pending",
                f"Instances still starting — {len(instance_statuses)} total, not all running yet"
            )
            return {
                "status": "pending",
                "message": "Instances are still starting",
                "output": {"instance_statuses": instance_statuses},
            }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error(
            "task", "check_completion", "client_error",
            f"AWS ClientError ({error_code}): {error_msg}"
        )
        return {
            "status": "failed",
            "message": f"{error_code}: {error_msg}",
            "output": None,
        }
    except Exception as e:
        log_error(
            "task", "check_completion", "unexpected_error",
            f"Unexpected error during completion check: {str(e)}"
        )
        return {
            "status": "failed",
            "message": f"Completion check error: {str(e)}",
            "output": None,
        }


def finish(least_action_task_object, client, completion_details, run_details):
    """
    Log final outcome and release any held resources.

    Returns:
        None
    """
    try:
        task_laui = least_action_task_object.get("laui")

        log_info(
            "task", "finish", "starting_cleanup",
            f"Starting cleanup for task: {task_laui}"
        )

        final_status = completion_details.get("status", "unknown")
        log_info(
            "task", "finish", "final_status",
            f"Task ended with status: {final_status}"
        )

        if client:
            try:
                client.close()
                log_info(
                    "task", "finish", "client_closed",
                    "EC2 boto3 client connection closed successfully"
                )
            except Exception as close_error:
                log_error(
                    "task", "finish", "client_close_error",
                    f"Error closing EC2 client: {str(close_error)}"
                )

        if final_status == "success":
            output = completion_details.get("output", {})
            instance_statuses = output.get("instance_statuses", [])
            running_ids = [s["instance_id"] for s in instance_statuses if s.get("state") == "running"]
            log_info(
                "task", "finish", "operation_summary",
                f"Successfully started and confirmed running: {len(running_ids)} instance(s) — {running_ids}"
            )
        elif final_status == "failed":
            log_error(
                "task", "finish", "operation_failed",
                f"Start operation failed: {completion_details.get('message')}"
            )
        else:
            log_info(
                "task", "finish", "operation_status",
                f"Operation ended with status={final_status}, message={completion_details.get('message')}"
            )

        log_info(
            "task", "finish", "cleanup_complete",
            f"Cleanup complete for task: {task_laui}"
        )

    except Exception as e:
        log_error(
            "task", "finish", "cleanup_error",
            f"Error during finish/cleanup: {str(e)}"
        )
        # Never re-raise from finish — allow graceful task completion
'''}

bashblock = {"main.sh": """#!/bin/bash
set -e
pip install boto3>=1.28.0
pip install botocore>=1.31.0
echo "Dependencies installed successfully"
"""}

connection = {"region": "us-east-1"}

payload = {"instance_ids": ["i-0abc123def456789"]}

prompt = (
    "Start one or more EC2 instances. Payload: instance_ids (list) or instance_id (string) in payload.data. "
    "Call start_instances and return immediately with status:pending and instance_ids (async). "
    "check_completion polls describe_instances until all instances reach running state. "
    "Auth: access keys first, then assume_iam_role via STS, then default credential chain. "
    "finish() must close the boto3 client without re-raising exceptions."
)

install_docs = """# AWSEC2StartInstance — Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {"Effect": "Allow", "Action": ["ec2:StartInstances", "ec2:DescribeInstances", "ec2:DescribeRegions"], "Resource": "*"}
"""

guide_docs = """# AWSEC2StartInstance — Operator Guide

## What it does

Starts one or more stopped EC2 instances and returns immediately with status:pending (async).
check_completion polls describe_instances until all instances reach running state.

---

## Auth

1. **Access keys** — aws_access_key_id + aws_secret_access_key in connection
2. **Assume IAM role** — assume_iam_role (ARN) in connection, assumed via STS
3. **Default credential chain** — instance profile, ECS task role, env vars, ~/.aws/credentials

---

## Connection

**Scenario 1:** `{"region": "us-east-1", "aws_access_key_id": "AKIA...", "aws_secret_access_key": "..."}`
**Scenario 2:** `{"region": "us-east-1", "assume_iam_role": "arn:aws:iam::123456789012:role/MyRole"}`
**Scenario 3:** `{"region": "us-east-1"}`

---

## Payload (inside payload.data)

| Field        | Required | Description                                            |
|--------------|----------|--------------------------------------------------------|
| instance_ids | Yes*     | List of EC2 instance IDs to start                      |
| instance_id  | Yes*     | Single instance ID — auto-wrapped in list              |
| dry_run      | No       | Validate permissions without starting (default: false) |

---

## Output (on success)

    {"instance_statuses": [{"instance_id": "i-...", "state": "running", "private_ip": "10.0.0.1", ...}]}
"""

description = """
Starts one or more stopped EC2 instances (async). Calls start_instances and returns immediately
with status:pending. check_completion polls describe_instances until all instances reach running
state. Supports dry_run for permission validation.
Auth: access keys first, then assume_iam_role via STS, then default credential chain.
finish() closes the boto3 client without re-raising exceptions.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "EC2",
    "category": "Compute",
    "tags": ["ec2", "instance", "start", "aws"],
    "airflow_equivalent": "EC2StartInstanceOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

**Already-running instances**: AWS silently accepts `start_instances` on an already-running
instance — it does not appear in the `starting` list but is included in `instance_ids`.
`check_completion()` confirms running state for all IDs regardless.

**Instance store volumes**: Starting a stopped instance does NOT restore instance store data —
only EBS-backed data persists across stop/start cycles. If the instance had instance store
volumes, their data was lost at stop time.

**IP address changes**: A stopped instance may receive a new public IP on start if it uses
a dynamic public IP (not an Elastic IP). Private IPs within the VPC are preserved.

**Spot instances**: Spot instances cannot be stopped and started — only terminated. This
operator will return a ClientError for spot instances.

**Hibernated instances**: `start_instances` on a hibernated instance resumes from the saved
RAM state — processes, network connections, and open files are restored. The operator
correctly handles this case since it polls for `running` state regardless of how the instance
was previously stopped.
"""
