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
AWS EC2 Hibernate Instance Operator

Hibernates an EC2 instance by calling stop_instances with Hibernate=True.
Hibernation saves the in-memory RAM contents to the encrypted EBS root volume.
On next start, the instance resumes from exactly where it left off.
Auth priority: explicit keys → assume IAM role → default credential chain.
Execution is async — run() triggers the hibernate-stop; check_completion() polls for stopped state.
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
            f"Initializing EC2 hibernate operator for task: {task_laui}"
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
    Hibernate an EC2 instance using stop_instances with Hibernate=True.

    Prerequisites (must have been configured at launch time — cannot be added retroactively):
        - Hibernation enabled on the instance
        - Encrypted EBS root volume
        - Supported instance type and OS
        - RAM < 150 GB

    Payload fields:
        instance_id  (str, required)         -- instance ID to hibernate
        dry_run      (bool, default False)   -- validate permissions without hibernating

    Returns:
        dict with status, execution_type="async", result, instance_ids
    """
    try:
        task_laui = least_action_task_object.get("laui")
        payload = least_action_task_object.get("payload", {})

        log_info(
            "task", "run", "extracting_payload",
            f"Extracting hibernate configuration for task: {task_laui}"
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
            "task", "run", "hibernating_instance",
            f"Hibernating instance: {instance_id} | dry_run={dry_run} | "
            f"RAM contents will be written to the encrypted EBS root volume. "
            f"Instance must have been launched with hibernation enabled."
        )

        stop_params = {
            "InstanceIds": [instance_id],
            "Hibernate": True,
        }
        if dry_run:
            stop_params["DryRun"] = True
            log_info("task", "run", "dry_run", "Dry run mode — no instance will actually be hibernated")

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
            "task", "run", "hibernate_issued",
            f"Hibernate-stop issued for {instance_id} — RAM is being written to EBS asynchronously"
        )

        return {
            "status": "pending",
            "execution_type": "async",
            "result": {
                "instance_id": instance_id,
                "action": "hibernate",
                "stopping_instances": stopping,
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
    Poll describe_instances to determine whether the instance has reached stopped (hibernated) state.

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
                "message": f"Hibernate failed in run phase: {run_details.get('error')}",
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

        log_info(
            "task", "check_completion", "instance_state",
            f"Instance {instance_id}: state={state} (code={state_code})"
        )

        if state == "stopped":
            log_info(
                "task", "check_completion", "hibernate_complete",
                f"Instance {instance_id} reached stopped (hibernated) state — "
                f"RAM has been saved to EBS. Resume with start_instances to restore."
            )
            return {
                "status": "success",
                "message": f"Instance {instance_id} is hibernated (stopped with RAM preserved on EBS)",
                "output": {
                    "instance_id": instance_id,
                    "action": "hibernate",
                    "state": state,
                    "state_code": state_code,
                    "instance_type": inst.get("InstanceType"),
                    "availability_zone": inst.get("Placement", {}).get("AvailabilityZone"),
                },
            }

        log_info(
            "task", "check_completion", "instance_still_stopping",
            f"Instance {instance_id} still hibernating — current state: {state}"
        )
        return {
            "status": "pending",
            "message": f"Instance {instance_id} still stopping (state={state})",
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
                f"Instance {output.get('instance_id')} hibernated successfully — "
                f"state={output.get('state')}. Resume with start_instances to restore from RAM."
            )
        elif final_status == "failed":
            log_error(
                "task", "finish", "operation_failed",
                f"Hibernate operation failed: {completion_details.get('message')}"
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
    "Hibernate an EC2 instance by calling stop_instances with Hibernate=True. "
    "Payload: instance_id (string) in payload.data. "
    "Return immediately with status:pending (async). "
    "check_completion polls describe_instances until the instance reaches stopped state. "
    "Auth: access keys first, then assume_iam_role via STS, then default credential chain. "
    "finish() must close the boto3 client without re-raising exceptions."
)

install_docs = """# AWSEC2HibernateInstance — Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {"Effect": "Allow", "Action": ["ec2:StopInstances", "ec2:DescribeInstances", "ec2:DescribeRegions"], "Resource": "*"}

## EC2 Instance Requirements

- Hibernation must be enabled at launch time
- EBS root volume must be encrypted
- Supported instance type and OS (Amazon Linux 2, Ubuntu 20.04+, Windows with agent)
- RAM < 150 GB
"""

guide_docs = """# AWSEC2HibernateInstance — Operator Guide

## What it does

Hibernates an EC2 instance by calling stop_instances with Hibernate=True and returns immediately
with status:pending (async). check_completion polls describe_instances until the instance reaches
stopped state. Hibernation saves RAM to the encrypted EBS root volume — on next start the instance
resumes from where it left off. The instance must have been launched with hibernation enabled.

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

| Field       | Required | Description                                               |
|-------------|----------|-----------------------------------------------------------|
| instance_id | Yes      | EC2 instance ID to hibernate                              |
| dry_run     | No       | Validate permissions without hibernating (default: false) |

---

## Output (on success)

    {"instance_id": "i-...", "action": "hibernate", "state": "stopped", "instance_type": "t3.micro", ...}
"""

description = """
Hibernates an EC2 instance by calling stop_instances with Hibernate=True (async). Returns
immediately with status:pending. check_completion polls describe_instances until the instance
reaches stopped state. RAM is saved to the encrypted EBS root volume — on next start the
instance resumes from where it left off. The instance must have been launched with hibernation
enabled. Auth: access keys first, then assume_iam_role via STS, then default credential chain.
finish() closes the boto3 client without re-raising exceptions.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "EC2",
    "category": "Compute",
    "tags": ["ec2", "instance", "hibernate", "aws"],
    "airflow_equivalent": "EC2HibernateInstanceOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

**Launch-time prerequisite**: Hibernation must be enabled at instance launch — it cannot
be retroactively enabled on an existing instance. Check `HibernationOptions.Configured`
via `describe_instances` before calling this operator. If hibernation was not configured
at launch, AWS returns `UnsupportedHibernationConfiguration` and the instance is unaffected.

**Encrypted root volume required**: The EBS root volume must be encrypted (using CMK or
AWS managed key). Unencrypted root volumes cause an `UnsupportedHibernationConfiguration`
error.

**RAM size limit**: Instances with more than 150 GB of RAM cannot be hibernated — AWS
imposes this limit because the RAM contents must fit on the EBS root volume.

**Supported instance families**: Not all instance types support hibernation. Check the
current AWS documentation for the supported list — it includes most general-purpose and
compute-optimized types but excludes bare metal and some older families.

**Resuming**: Start the instance using `AWSSageMakerStartNotebookInstance` (or the EC2
Start operator) with the same `instance_id` — AWS detects the hibernate state and restores
RAM automatically. Resume typically takes 20-30 seconds longer than a normal cold start.
"""
