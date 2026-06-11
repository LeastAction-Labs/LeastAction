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
AWS EC2 Terminate Instance Operator

Permanently terminates one or more EC2 instances. This is irreversible — EBS volumes
with delete_on_termination=true (the default) are permanently deleted.
Auth priority: explicit keys → assume IAM role → default credential chain.
Execution is async — run() triggers termination; check_completion() polls for terminated state.
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
            f"Initializing EC2 terminate operator for task: {task_laui}"
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
    Terminate one or more EC2 instances using terminate_instances.

    WARNING: Termination is irreversible. EBS volumes with delete_on_termination=true
    (the default) are permanently deleted along with the instance.

    Payload fields:
        instance_ids  (list[str], required)  -- list of instance IDs to terminate
        instance_id   (str)                  -- single instance ID, auto-wrapped in list
        dry_run       (bool, default False)  -- validate permissions without terminating

    Returns:
        dict with status, execution_type="async", result, instance_ids
    """
    try:
        task_laui = least_action_task_object.get("laui")
        payload = least_action_task_object.get("payload", {})

        log_info(
            "task", "run", "extracting_payload",
            f"Extracting terminate configuration for task: {task_laui}"
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
            "task", "run", "terminating_instances",
            f"Terminating {len(instance_ids)} instance(s): {instance_ids} | dry_run={dry_run} | "
            f"WARNING: this is irreversible — EBS volumes with delete_on_termination=true will be permanently deleted"
        )

        terminate_params = {"InstanceIds": instance_ids}
        if dry_run:
            terminate_params["DryRun"] = True
            log_info("task", "run", "dry_run", "Dry run mode — no instance will actually be terminated")

        try:
            response = client.terminate_instances(**terminate_params)
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

        terminating = response.get("TerminatingInstances", [])
        for item in terminating:
            log_info(
                "task", "run", "instance_state_transition",
                f"Instance {item['InstanceId']}: "
                f"{item.get('PreviousState', {}).get('Name')} → {item.get('CurrentState', {}).get('Name')}"
            )

        log_info(
            "task", "run", "terminate_issued",
            f"terminate_instances succeeded — {len(instance_ids)} instance(s) shutting down: {instance_ids}"
        )

        return {
            "status": "pending",
            "execution_type": "async",
            "result": {
                "instance_ids": instance_ids,
                "terminating_instances": terminating,
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
    Poll describe_instances to determine whether all instances have terminated.

    Instances that no longer appear in describe_instances (fully cycled through terminated)
    are treated as successfully terminated.

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
                "message": f"Terminate failed in run phase: {run_details.get('error')}",
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
        returned_ids = set()

        for reservation in response.get("Reservations", []):
            for inst in reservation.get("Instances", []):
                instance_id = inst.get("InstanceId")
                state = inst.get("State", {}).get("Name")
                state_code = inst.get("State", {}).get("Code")
                returned_ids.add(instance_id)

                status_entry = {
                    "instance_id": instance_id,
                    "state": state,
                    "state_code": state_code,
                    "instance_type": inst.get("InstanceType"),
                    "availability_zone": inst.get("Placement", {}).get("AvailabilityZone"),
                }
                instance_statuses.append(status_entry)

                log_info(
                    "task", "check_completion", "instance_state",
                    f"Instance {instance_id}: state={state} (code={state_code})"
                )

        # Instances no longer visible in describe_instances have fully completed termination
        missing_ids = [iid for iid in instance_ids if iid not in returned_ids]
        if missing_ids:
            log_info(
                "task", "check_completion", "instances_fully_terminated",
                f"Instances no longer visible in describe_instances (fully terminated): {missing_ids}"
            )
            for iid in missing_ids:
                instance_statuses.append({"instance_id": iid, "state": "terminated", "state_code": 48})

        all_terminated = all(s.get("state") == "terminated" for s in instance_statuses)

        if all_terminated:
            log_info(
                "task", "check_completion", "all_instances_terminated",
                f"All {len(instance_ids)} instance(s) are in terminated state"
            )
            return {
                "status": "success",
                "message": f"All {len(instance_ids)} instance(s) are terminated",
                "output": {"instance_statuses": instance_statuses},
            }
        else:
            still_active = [s["instance_id"] for s in instance_statuses if s.get("state") != "terminated"]
            log_info(
                "task", "check_completion", "instances_still_terminating",
                f"{len(still_active)} instance(s) still shutting down: {still_active}"
            )
            return {
                "status": "pending",
                "message": f"{len(still_active)} instance(s) still shutting down",
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
            terminated_ids = [s["instance_id"] for s in instance_statuses if s.get("state") == "terminated"]
            log_info(
                "task", "finish", "operation_summary",
                f"Successfully terminated: {len(terminated_ids)} instance(s) — {terminated_ids}"
            )
        elif final_status == "failed":
            log_error(
                "task", "finish", "operation_failed",
                f"Terminate operation failed: {completion_details.get('message')}"
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
    "Terminate one or more EC2 instances. Payload: instance_ids (list) or instance_id (string) in payload.data. "
    "Termination is irreversible — EBS volumes with delete_on_termination=true are permanently deleted. "
    "Call terminate_instances and return immediately with status:pending (async). "
    "check_completion polls describe_instances until all instances reach terminated state. "
    "Instances no longer visible in describe_instances are treated as fully terminated. "
    "Auth: access keys first, then assume_iam_role via STS, then default credential chain. "
    "finish() must close the boto3 client without re-raising exceptions."
)

install_docs = """# AWSEC2TerminateInstance — Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {"Effect": "Allow", "Action": ["ec2:TerminateInstances", "ec2:DescribeInstances", "ec2:DescribeRegions"], "Resource": "*"}
"""

guide_docs = """# AWSEC2TerminateInstance — Operator Guide

## What it does

Permanently terminates one or more EC2 instances and returns immediately with status:pending (async).
check_completion polls describe_instances until all instances reach terminated state. Instances no
longer visible in describe_instances (fully cycled through terminated) are treated as done.

**Termination is irreversible.** EBS volumes with delete_on_termination=true (the default) are
permanently deleted. Volumes with delete_on_termination=false are detached but preserved.

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

| Field        | Required | Description                                               |
|--------------|----------|-----------------------------------------------------------|
| instance_ids | Yes*     | List of EC2 instance IDs to terminate                     |
| instance_id  | Yes*     | Single instance ID — auto-wrapped in list                 |
| dry_run      | No       | Validate permissions without terminating (default: false) |

---

## Output (on success)

    {"instance_statuses": [{"instance_id": "i-...", "state": "terminated", ...}]}
"""

description = """
Permanently terminates one or more EC2 instances (async). Calls terminate_instances and returns
immediately with status:pending. check_completion polls describe_instances until all instances
reach terminated state. Termination is irreversible — EBS volumes with delete_on_termination=true
are permanently deleted. Accepts instance_ids list or single instance_id string.
Auth: access keys first, then assume_iam_role via STS, then default credential chain.
finish() closes the boto3 client without re-raising exceptions.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "EC2",
    "category": "Compute",
    "tags": ["ec2", "instance", "terminate", "aws"],
    "airflow_equivalent": "EC2TerminateInstanceOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

**Irreversibility**: Termination is permanent — there is no undo. All EBS volumes with
`delete_on_termination=true` (the default for the root volume) are permanently deleted.
Volumes with `delete_on_termination=false` are detached but preserved. Always verify
volume retention settings before calling this operator on production instances.

**Termination protection**: If termination protection is enabled on the instance, AWS
returns `OperationNotPermitted`. Disable it first via `ec2:ModifyInstanceAttribute`.
This operator does NOT disable termination protection automatically.

**Already-terminated instances**: Recently terminated instances still appear in
`describe_instances` with state `terminated` — this operator handles them correctly.
Older terminated instances may no longer be visible in describe results; `check_completion()`
treats missing instances as successfully terminated.

**Spot instances with persistent requests**: Terminating a spot instance does NOT cancel
the spot request. If the spot request is persistent, AWS will relaunch the instance.
Cancel the spot request separately via `ec2:CancelSpotInstanceRequests` to prevent relaunch.

**EBS snapshot retention**: If you need a final snapshot before termination, create it
manually using AWSBedrockCreateDBSnapshot (for RDS) or EC2 snapshot APIs before running
this operator.
"""
