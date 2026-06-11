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
AWS EC2 Stop Instance Operator

Stops one or more running EC2 instances. Supports graceful shutdown, force stop, and hibernate.
Auth priority: explicit keys → assume IAM role → default credential chain.
Execution is async — run() triggers the stop; check_completion() polls for stopped state.
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
            f"Initializing EC2 stop operator for task: {task_laui}"
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
    Stop one or more EC2 instances using stop_instances.

    Payload fields:
        instance_ids  (list[str], required)  -- list of instance IDs to stop
        instance_id   (str)                  -- single instance ID, auto-wrapped in list
        force         (bool, default False)  -- hard power-off without OS shutdown; risks data loss
        hibernate     (bool, default False)  -- stop with Hibernate=True; saves RAM to EBS root
        dry_run       (bool, default False)  -- validate permissions without stopping

    Note: force and hibernate are mutually exclusive. If both are True, hibernate takes precedence.

    Returns:
        dict with status, execution_type="async", result, instance_ids
    """
    try:
        task_laui = least_action_task_object.get("laui")
        payload = least_action_task_object.get("payload", {})

        log_info(
            "task", "run", "extracting_payload",
            f"Extracting stop configuration for task: {task_laui}"
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

        force = bool(payload_data.get("force", False))
        hibernate = bool(payload_data.get("hibernate", False))
        dry_run = bool(payload_data.get("dry_run", False))

        stop_params = {"InstanceIds": instance_ids}
        if dry_run:
            stop_params["DryRun"] = True

        if hibernate:
            stop_params["Hibernate"] = True
            log_info(
                "task", "run", "stopping_instances",
                f"Stopping {len(instance_ids)} instance(s) with Hibernate=True: {instance_ids} | "
                f"RAM contents will be saved to encrypted EBS root volume"
            )
        elif force:
            stop_params["Force"] = True
            log_info(
                "task", "run", "stopping_instances",
                f"Force-stopping {len(instance_ids)} instance(s): {instance_ids} | "
                f"WARNING: hard power-off — OS shutdown scripts will not run, data loss possible"
            )
        else:
            log_info(
                "task", "run", "stopping_instances",
                f"Gracefully stopping {len(instance_ids)} instance(s): {instance_ids}"
            )

        try:
            response = client.stop_instances(**stop_params)
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

        stopping = response.get("StoppingInstances", [])
        for item in stopping:
            log_info(
                "task", "run", "instance_state_transition",
                f"Instance {item['InstanceId']}: "
                f"{item.get('PreviousState', {}).get('Name')} → {item.get('CurrentState', {}).get('Name')}"
            )

        log_info(
            "task", "run", "stop_issued",
            f"stop_instances succeeded — {len(instance_ids)} instance(s) transitioning to stopped: {instance_ids}"
        )

        return {
            "status": "pending",
            "execution_type": "async",
            "result": {
                "instance_ids": instance_ids,
                "stopping_instances": stopping,
                "force": force,
                "hibernate": hibernate,
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
    Poll describe_instances to determine whether all instances have stopped.

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
                "message": f"Stop failed in run phase: {run_details.get('error')}",
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
        all_stopped = True

        for reservation in response.get("Reservations", []):
            for inst in reservation.get("Instances", []):
                instance_id = inst.get("InstanceId")
                state = inst.get("State", {}).get("Name")
                state_code = inst.get("State", {}).get("Code")

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

                if state != "stopped":
                    all_stopped = False

        if all_stopped:
            result = run_details.get("result", {})
            log_info(
                "task", "check_completion", "all_instances_stopped",
                f"All {len(instance_statuses)} instance(s) are in stopped state"
            )
            return {
                "status": "success",
                "message": f"All {len(instance_statuses)} instance(s) are stopped",
                "output": {
                    "instance_statuses": instance_statuses,
                    "force": result.get("force", False),
                    "hibernate": result.get("hibernate", False),
                },
            }
        else:
            log_info(
                "task", "check_completion", "instances_still_stopping",
                f"Instances still stopping — {len(instance_statuses)} total, not all stopped yet"
            )
            return {
                "status": "pending",
                "message": "Instances are still stopping",
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
            stopped_ids = [s["instance_id"] for s in instance_statuses if s.get("state") == "stopped"]
            log_info(
                "task", "finish", "operation_summary",
                f"Successfully stopped: {len(stopped_ids)} instance(s) — {stopped_ids} | "
                f"force={output.get('force', False)}, hibernate={output.get('hibernate', False)}"
            )
        elif final_status == "failed":
            log_error(
                "task", "finish", "operation_failed",
                f"Stop operation failed: {completion_details.get('message')}"
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

payload = {"instance_ids": ["i-0abc123def456789"], "force": False, "hibernate": False}

prompt = (
    "Stop one or more EC2 instances. Payload: instance_ids (list) or instance_id (string) in payload.data. "
    "Optional: force (hard power-off), hibernate (save RAM to EBS), dry_run. "
    "Call stop_instances and return immediately with status:pending (async). "
    "check_completion polls describe_instances until all instances reach stopped state. "
    "Auth: access keys first, then assume_iam_role via STS, then default credential chain. "
    "finish() must close the boto3 client without re-raising exceptions."
)

install_docs = """# AWSEC2StopInstance — Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {"Effect": "Allow", "Action": ["ec2:StopInstances", "ec2:DescribeInstances", "ec2:DescribeRegions"], "Resource": "*"}
"""

guide_docs = """# AWSEC2StopInstance — Operator Guide

## What it does

Stops one or more EC2 instances and returns immediately with status:pending (async).
check_completion polls describe_instances until all instances reach stopped state.

Supports three modes via payload flags:
- Default (force=false, hibernate=false): graceful OS shutdown
- force=true: immediate power-off — use when instance is unresponsive; risks data loss
- hibernate=true: stop_instances with Hibernate=True — saves RAM to encrypted EBS root volume

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

| Field        | Required | Description                                                              |
|--------------|----------|--------------------------------------------------------------------------|
| instance_ids | Yes*     | List of EC2 instance IDs to stop                                         |
| instance_id  | Yes*     | Single instance ID — auto-wrapped in list                                |
| force        | No       | Hard power-off without OS shutdown — risks data loss (default: false)    |
| hibernate    | No       | Stop with hibernate — saves RAM to EBS root volume (default: false)      |
| dry_run      | No       | Validate permissions without stopping (default: false)                   |

---

## Output (on success)

    {"instance_statuses": [{"instance_id": "i-...", "state": "stopped", ...}], "force": false, "hibernate": false}
"""

description = """
Stops one or more EC2 instances (async). Calls stop_instances and returns immediately with
status:pending. check_completion polls describe_instances until all instances reach stopped state.
Supports force=true (hard power-off) and hibernate=true (RAM saved to encrypted EBS).
Auth: access keys first, then assume_iam_role via STS, then default credential chain.
finish() closes the boto3 client without re-raising exceptions.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "EC2",
    "category": "Compute",
    "tags": ["ec2", "instance", "stop", "hibernate", "aws"],
    "airflow_equivalent": "EC2StopInstanceOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

**force=true risks**: Hard power-off (`force=true`) is equivalent to pulling the power cord.
The OS does not get a chance to flush disk buffers or run shutdown scripts. Use only when
a graceful stop is not possible (unresponsive instance). Data in memory is permanently lost.

**hibernate prerequisite**: Hibernation must have been enabled at launch time and the EBS
root volume must be encrypted. Calling stop with `hibernate=true` on an instance not
configured for hibernation returns `UnsupportedHibernationConfiguration` — caught and
returned as `status:failed`, the instance is unaffected.

**Spot instances**: Spot instances cannot be stopped — only terminated. AWS returns an
`UnsupportedOperation` error. Caught and returned as `status:failed`.

**7-day auto-restart**: AWS automatically starts stopped (non-hibernated) instances after
7 days. This is an AWS platform behaviour — plan for it in long-running stop scenarios.

**Already-stopped instances**: AWS silently accepts stop on an already-stopped instance.
The instance will not appear in the `stopping` list but will be confirmed stopped in
`check_completion()`.
"""
