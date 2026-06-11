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
AWS EC2 Reboot Instance Operator

Sends a graceful reboot signal to an EC2 instance via reboot_instances. Unlike a stop+start
cycle, a reboot preserves the instance's public and private IP addresses and does not release
EBS-backed volumes. The OS receives a graceful shutdown-and-restart signal (typically 1-3 min).
Auth priority: explicit keys → assume IAM role → default credential chain.
Execution is async — run() triggers the reboot; check_completion() polls for running state.
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
            f"Initializing EC2 reboot operator for task: {task_laui}"
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
    Reboot an EC2 instance using reboot_instances.

    A reboot preserves the instance's public and private IP addresses, EBS volumes, and
    instance store data. The OS receives a graceful shutdown-and-restart signal.
    Typically completes within 1-3 minutes.

    Payload fields:
        instance_id  (str, required)         -- instance ID to reboot
        dry_run      (bool, default False)   -- validate permissions without rebooting

    Returns:
        dict with status, execution_type="async", result, instance_ids
    """
    try:
        task_laui = least_action_task_object.get("laui")
        payload = least_action_task_object.get("payload", {})

        log_info(
            "task", "run", "extracting_payload",
            f"Extracting reboot configuration for task: {task_laui}"
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

        instance_id = payload_data.get("instance_id")
        if not instance_id:
            log_error(
                "task", "run", "missing_instance_id",
                "instance_id is required in payload.data"
            )
            return {
                "status": "failed",
                "execution_type": "async",
                "result": None,
                "error": "instance_id is required in payload.data",
            }

        dry_run = bool(payload_data.get("dry_run", False))

        log_info(
            "task", "run", "rebooting_instance",
            f"Sending reboot signal to instance: {instance_id} | dry_run={dry_run} | "
            f"Reboot preserves IP addresses and EBS volumes — OS performs graceful restart"
        )

        reboot_params = {"InstanceIds": [instance_id]}
        if dry_run:
            reboot_params["DryRun"] = True
            log_info("task", "run", "dry_run", "Dry run mode — no instance will actually be rebooted")

        try:
            client.reboot_instances(**reboot_params)
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

        log_info(
            "task", "run", "reboot_issued",
            f"reboot_instances succeeded for {instance_id} — instance will cycle through reboot "
            f"asynchronously and return to running state (typically 1-3 minutes)"
        )

        return {
            "status": "pending",
            "execution_type": "async",
            "result": {
                "instance_id": instance_id,
                "action": "reboot",
            },
            "instance_ids": [instance_id],
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
    Poll describe_instances to determine whether the instance has returned to running state.

    During a reboot the instance may briefly appear as stopping/stopped before returning to
    running. Any state other than running means the reboot cycle is still in progress.

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
                "message": f"Reboot failed in run phase: {run_details.get('error')}",
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

        instance_id = instance_ids[0]

        log_info(
            "task", "check_completion", "polling_instance_status",
            f"Describing instance: {instance_id}"
        )

        response = client.describe_instances(InstanceIds=[instance_id])
        reservations = response.get("Reservations", [])

        if not reservations:
            return {
                "status": "failed",
                "message": f"Instance {instance_id} not found in describe_instances",
                "output": None,
            }

        inst = reservations[0]["Instances"][0]
        state = inst.get("State", {}).get("Name")
        state_code = inst.get("State", {}).get("Code")
        private_ip = inst.get("PrivateIpAddress")
        public_ip = inst.get("PublicIpAddress")

        log_info(
            "task", "check_completion", "instance_state",
            f"Instance {instance_id}: state={state} (code={state_code}) | "
            f"private_ip={private_ip} | public_ip={public_ip}"
        )

        if state == "running":
            log_info(
                "task", "check_completion", "reboot_complete",
                f"Instance {instance_id} is back in running state — reboot cycle complete"
            )
            return {
                "status": "success",
                "message": f"Instance {instance_id} has completed its reboot and is running",
                "output": {
                    "instance_id": instance_id,
                    "action": "reboot",
                    "state": state,
                    "state_code": state_code,
                    "instance_type": inst.get("InstanceType"),
                    "private_ip": private_ip,
                    "public_ip": public_ip,
                    "availability_zone": inst.get("Placement", {}).get("AvailabilityZone"),
                },
            }

        # Instance may briefly be in stopping/stopped/pending during reboot cycle
        log_info(
            "task", "check_completion", "instance_still_rebooting",
            f"Instance {instance_id} still in reboot cycle — current state: {state}"
        )
        return {
            "status": "pending",
            "message": f"Instance {instance_id} still rebooting (state={state})",
            "output": {"instance_id": instance_id, "state": state},
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
            log_info(
                "task", "finish", "operation_summary",
                f"Instance {output.get('instance_id')} reboot complete — "
                f"state={output.get('state')}, private_ip={output.get('private_ip')}, "
                f"public_ip={output.get('public_ip')}"
            )
        elif final_status == "failed":
            log_error(
                "task", "finish", "operation_failed",
                f"Reboot operation failed: {completion_details.get('message')}"
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

payload = {"instance_id": "i-0abc123def456789"}

prompt = (
    "Reboot an EC2 instance by calling reboot_instances. Payload: instance_id (string) in payload.data. "
    "A reboot preserves IP addresses and EBS volumes — OS performs graceful restart. "
    "Return immediately with status:pending (async). "
    "check_completion polls describe_instances until the instance returns to running state. "
    "Auth: access keys first, then assume_iam_role via STS, then default credential chain. "
    "finish() must close the boto3 client without re-raising exceptions."
)

install_docs = """# AWSEC2RebootInstance — Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {"Effect": "Allow", "Action": ["ec2:RebootInstances", "ec2:DescribeInstances", "ec2:DescribeRegions"], "Resource": "*"}
"""

guide_docs = """# AWSEC2RebootInstance — Operator Guide

## What it does

Sends a graceful reboot signal to an EC2 instance and returns immediately with status:pending
(async). check_completion polls describe_instances until the instance returns to running state
(typically 1-3 minutes). Unlike a stop+start cycle, a reboot preserves the instance's public
and private IP addresses and does not release EBS-backed volumes.

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

| Field       | Required | Description                                              |
|-------------|----------|----------------------------------------------------------|
| instance_id | Yes      | EC2 instance ID to reboot                                |
| dry_run     | No       | Validate permissions without rebooting (default: false)  |

---

## Output (on success)

    {"instance_id": "i-...", "action": "reboot", "state": "running", "private_ip": "10.0.0.1", ...}
"""

description = """
Sends a graceful reboot signal to an EC2 instance via reboot_instances (async). Returns
immediately with status:pending. check_completion polls describe_instances until the instance
returns to running state. Unlike stop+start, a reboot preserves IP addresses and EBS volumes.
Auth: access keys first, then assume_iam_role via STS, then default credential chain.
finish() closes the boto3 client without re-raising exceptions.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "EC2",
    "category": "Compute",
    "tags": ["ec2", "instance", "reboot", "aws"],
    "airflow_equivalent": "EC2RebootInstanceOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

**Fire-and-forget API, async polling**: `reboot_instances` returns immediately — AWS sends
the reboot signal to the instance's hypervisor. The instance cycles through stopping→pending
→running states asynchronously. `check_completion()` polls `describe_instances` and waits
for `running` state to confirm the reboot completed.

**IP and EBS preservation**: Unlike a stop+start cycle, a reboot does NOT release or change
the instance's public/private IP addresses and does NOT detach EBS volumes. Instance store
data is also preserved across a reboot (unlike stop+start where instance store is wiped).

**Unresponsive instances**: If the OS is hung and does not respond to the reboot signal,
the instance may stay in a non-running state. In this case use AWSEC2StopInstance with
`force=true` (hard power-off) followed by AWSEC2StartInstance.

**Stopped instance**: AWS returns `IncorrectInstanceState` if you attempt to reboot a
stopped instance. A stopped instance must be started, not rebooted.

**Multiple reboots**: Calling reboot on an already-rebooting instance sends a second signal
which may cause the instance to reboot twice. `check_completion()` will confirm running
state after the full cycle completes.
"""
