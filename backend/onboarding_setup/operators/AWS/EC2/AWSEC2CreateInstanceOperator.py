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
AWS EC2 Launch Instance Operator

Launches one or more EC2 instances with full customization support.
Auth priority: explicit keys → assume IAM role → default credential chain.
Execution is async — run() triggers the launch; check_completion() polls for running state.
"""

import base64
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
            f"Initializing EC2 launch operator for task: {task_laui}"
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
    Launch EC2 instance(s) using run_instances.

    Payload fields (all optional except ami_id):
        ami_id                               (str, required)
        instance_type                        (str, default "t3.micro")
        min_count                            (int, default 1)
        max_count                            (int, default 1)
        key_name                             (str)
        security_group_ids                   (list[str])
        security_group_names                 (list[str])  -- used only when no subnet/VPC
        subnet_id                            (str)
        iam_instance_profile                 (str)  -- name or ARN
        user_data                            (str)  -- plain text or base64
        tags                                 (list[{"Key": str, "Value": str}])
        block_device_mappings                (list[dict])
        monitoring_enabled                   (bool, default False)
        ebs_optimized                        (bool, default False)
        availability_zone                    (str)
        tenancy                              (str)  -- default | dedicated | host
        placement_group                      (str)
        host_id                              (str)
        instance_initiated_shutdown_behavior (str)  -- stop | terminate
        disable_api_termination              (bool, default False)
        hibernation_configured               (bool, default False)
        network_interfaces                   (list[dict])  -- advanced; replaces subnet/SG
        private_ip_address                   (str)  -- ignored when network_interfaces present
        cpu_options                          (dict)  -- {"CoreCount": int, "ThreadsPerCore": int}
        metadata_options                     (dict)  -- IMDSv2 config
        client_token                         (str)  -- idempotency token
        dry_run                              (bool, default False)

    Returns:
        dict with status, execution_type="async", result, instance_ids
    """
    try:
        task_laui = least_action_task_object.get("laui")
        payload = least_action_task_object.get("payload", {})

        log_info(
            "task", "run", "extracting_payload",
            f"Extracting EC2 launch configuration for task: {task_laui}"
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

        # ---- Required ----
        ami_id = payload_data.get("ami_id")
        if not ami_id:
            log_error("task", "run", "missing_ami_id", "ami_id is required in payload.data")
            return {
                "status": "failed",
                "execution_type": "async",
                "result": None,
                "error": "ami_id is required in payload.data",
            }

        instance_type = payload_data.get("instance_type", "t3.micro")
        min_count = int(payload_data.get("min_count", 1))
        max_count = int(payload_data.get("max_count", 1))

        log_info(
            "task", "run", "building_launch_params",
            f"AMI: {ami_id} | type: {instance_type} | count: {min_count}-{max_count}"
        )

        launch_params = {
            "ImageId": ami_id,
            "InstanceType": instance_type,
            "MinCount": min_count,
            "MaxCount": max_count,
        }

        # ---- Key pair ----
        key_name = payload_data.get("key_name")
        if key_name:
            launch_params["KeyName"] = key_name
            log_info("task", "run", "key_pair", f"Key pair: {key_name}")

        # ---- Security groups (IDs preferred over names) ----
        security_group_ids = payload_data.get("security_group_ids", [])
        security_group_names = payload_data.get("security_group_names", [])
        if security_group_ids:
            launch_params["SecurityGroupIds"] = security_group_ids
            log_info("task", "run", "security_group_ids", f"Security group IDs: {security_group_ids}")
        elif security_group_names:
            launch_params["SecurityGroups"] = security_group_names
            log_info("task", "run", "security_group_names", f"Security group names: {security_group_names}")

        # ---- Subnet ----
        subnet_id = payload_data.get("subnet_id")
        if subnet_id:
            launch_params["SubnetId"] = subnet_id
            log_info("task", "run", "subnet", f"Subnet: {subnet_id}")

        # ---- IAM instance profile (name or ARN) ----
        iam_instance_profile = payload_data.get("iam_instance_profile")
        if iam_instance_profile:
            if iam_instance_profile.startswith("arn:"):
                launch_params["IamInstanceProfile"] = {"Arn": iam_instance_profile}
            else:
                launch_params["IamInstanceProfile"] = {"Name": iam_instance_profile}
            log_info("task", "run", "iam_instance_profile", f"IAM profile: {iam_instance_profile}")

        # ---- User data (plain text auto-encoded to base64) ----
        user_data = payload_data.get("user_data")
        if user_data:
            launch_params["UserData"] = base64.b64encode(user_data.encode("utf-8")).decode("utf-8")
            log_info("task", "run", "user_data", "User data attached and base64-encoded")

        # ---- Tags (applied to instance and root volume) ----
        tags = payload_data.get("tags", [])
        if tags:
            launch_params["TagSpecifications"] = [
                {"ResourceType": "instance", "Tags": tags},
                {"ResourceType": "volume", "Tags": tags},
            ]
            log_info("task", "run", "tags", f"Applying {len(tags)} tag(s): {tags}")

        # ---- Block device mappings (EBS volumes) ----
        block_device_mappings = payload_data.get("block_device_mappings", [])
        if block_device_mappings:
            launch_params["BlockDeviceMappings"] = block_device_mappings
            log_info(
                "task", "run", "block_device_mappings",
                f"{len(block_device_mappings)} block device mapping(s) specified"
            )

        # ---- Monitoring ----
        monitoring_enabled = bool(payload_data.get("monitoring_enabled", False))
        launch_params["Monitoring"] = {"Enabled": monitoring_enabled}
        log_info("task", "run", "monitoring", f"Detailed CloudWatch monitoring: {monitoring_enabled}")

        # ---- EBS optimized ----
        ebs_optimized = bool(payload_data.get("ebs_optimized", False))
        if ebs_optimized:
            launch_params["EbsOptimized"] = True
            log_info("task", "run", "ebs_optimized", "EBS optimized I/O enabled")

        # ---- Placement ----
        placement = {}
        availability_zone = payload_data.get("availability_zone")
        tenancy = payload_data.get("tenancy")
        placement_group = payload_data.get("placement_group")
        host_id = payload_data.get("host_id")

        if availability_zone:
            placement["AvailabilityZone"] = availability_zone
        if tenancy:
            placement["Tenancy"] = tenancy
        if placement_group:
            placement["GroupName"] = placement_group
        if host_id:
            placement["HostId"] = host_id

        if placement:
            launch_params["Placement"] = placement
            log_info("task", "run", "placement", f"Placement config: {placement}")

        # ---- Shutdown / termination behaviour ----
        shutdown_behavior = payload_data.get("instance_initiated_shutdown_behavior")
        if shutdown_behavior in ("stop", "terminate"):
            launch_params["InstanceInitiatedShutdownBehavior"] = shutdown_behavior
            log_info("task", "run", "shutdown_behavior", f"Shutdown behavior: {shutdown_behavior}")

        disable_api_termination = bool(payload_data.get("disable_api_termination", False))
        if disable_api_termination:
            launch_params["DisableApiTermination"] = True
            log_info("task", "run", "termination_protection", "API termination protection enabled")

        # ---- Hibernation ----
        hibernation_configured = bool(payload_data.get("hibernation_configured", False))
        if hibernation_configured:
            launch_params["HibernationOptions"] = {"Configured": True}
            log_info("task", "run", "hibernation", "Hibernation configured on instance")

        # ---- Network interfaces (advanced — replaces top-level SubnetId / SecurityGroupIds) ----
        network_interfaces = payload_data.get("network_interfaces", [])
        if network_interfaces:
            launch_params.pop("SubnetId", None)
            launch_params.pop("SecurityGroupIds", None)
            launch_params.pop("SecurityGroups", None)
            launch_params["NetworkInterfaces"] = network_interfaces
            log_info(
                "task", "run", "network_interfaces",
                f"Using {len(network_interfaces)} custom network interface(s) — SubnetId/SGs removed from top level"
            )

        # ---- Private IP (ignored when using custom network_interfaces) ----
        private_ip_address = payload_data.get("private_ip_address")
        if private_ip_address and not network_interfaces:
            launch_params["PrivateIpAddress"] = private_ip_address
            log_info("task", "run", "private_ip", f"Private IP address: {private_ip_address}")

        # ---- CPU options ----
        cpu_options = payload_data.get("cpu_options", {})
        if cpu_options:
            launch_params["CpuOptions"] = cpu_options
            log_info("task", "run", "cpu_options", f"CPU options: {cpu_options}")

        # ---- Instance metadata options (IMDSv2) ----
        metadata_options = payload_data.get("metadata_options", {})
        if metadata_options:
            launch_params["MetadataOptions"] = metadata_options
            log_info("task", "run", "metadata_options", f"Metadata service options: {metadata_options}")

        # ---- Idempotency token ----
        client_token = payload_data.get("client_token")
        if client_token:
            launch_params["ClientToken"] = client_token
            log_info("task", "run", "client_token", f"Idempotency client token: {client_token}")

        # ---- Dry run ----
        dry_run = bool(payload_data.get("dry_run", False))
        if dry_run:
            launch_params["DryRun"] = True
            log_info("task", "run", "dry_run", "Dry run mode — no instance will actually be launched")

        log_info(
            "task", "run", "calling_run_instances",
            f"Calling run_instances: AMI={ami_id}, type={instance_type}, count={min_count}-{max_count}"
        )

        try:
            response = client.run_instances(**launch_params)
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

        instances = response.get("Instances", [])
        instance_ids = [inst["InstanceId"] for inst in instances]

        log_info(
            "task", "run", "instances_launched",
            f"run_instances succeeded — {len(instance_ids)} instance(s) initializing: {instance_ids}"
        )

        for inst in instances:
            log_info(
                "task", "run", "instance_detail",
                f"Instance {inst['InstanceId']}: type={inst.get('InstanceType')} | "
                f"state={inst.get('State', {}).get('Name')} | "
                f"AZ={inst.get('Placement', {}).get('AvailabilityZone')} | "
                f"private_ip={inst.get('PrivateIpAddress')}"
            )

        return {
            "status": "pending",
            "execution_type": "async",
            "result": {
                "instance_ids": instance_ids,
                "reservation_id": response.get("ReservationId"),
                "launched_count": len(instance_ids),
                "response_metadata": response.get("ResponseMetadata", {}),
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
    Poll describe_instances to determine whether all launched instances are running.

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
                "message": f"Launch failed in run phase: {run_details.get('error')}",
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
                az = inst.get("Placement", {}).get("AvailabilityZone")

                status_entry = {
                    "instance_id": instance_id,
                    "state": state,
                    "state_code": state_code,
                    "instance_type": inst.get("InstanceType"),
                    "private_ip": private_ip,
                    "public_ip": public_ip,
                    "availability_zone": az,
                    "launch_time": str(inst.get("LaunchTime", "")),
                }
                instance_statuses.append(status_entry)

                log_info(
                    "task", "check_completion", "instance_state",
                    f"Instance {instance_id}: state={state} (code={state_code}) | "
                    f"private_ip={private_ip} | public_ip={public_ip} | AZ={az}"
                )

                if state != "running":
                    all_running = False

                if state in ("terminated", "shutting-down"):
                    any_failed = True
                    log_error(
                        "task", "check_completion", "instance_in_failure_state",
                        f"Instance {instance_id} entered terminal failure state: {state}"
                    )

        if any_failed:
            log_error(
                "task", "check_completion", "launch_failed",
                "One or more instances entered a terminal failure state"
            )
            return {
                "status": "failed",
                "message": "One or more instances failed to launch (terminated or shutting-down)",
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
                f"Instances still initializing — {len(instance_statuses)} total, not all running yet"
            )
            return {
                "status": "pending",
                "message": "Instances are still initializing",
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
                f"Successfully launched and confirmed running: {len(running_ids)} instance(s) — {running_ids}"
            )
        elif final_status == "failed":
            log_error(
                "task", "finish", "operation_failed",
                f"Launch operation failed: {completion_details.get('message')}"
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

payload = {
    "ami_id": "ami-0abcdef1234567890",
    "instance_type": "t3.micro",
    "min_count": 1,
    "max_count": 1,
    "key_name": "my-key-pair",
    "security_group_ids": ["sg-12345678"],
    "subnet_id": "subnet-12345678",
    "iam_instance_profile": "my-instance-profile",
    "user_data": "#!/bin/bash\necho hello",
    "tags": [{"Key": "Name", "Value": "my-ec2"}, {"Key": "Env", "Value": "prod"}],
    "monitoring_enabled": False,
    "ebs_optimized": False,
    "availability_zone": "us-east-1a",
    "disable_api_termination": False,
    "instance_initiated_shutdown_behavior": "stop",
    "hibernation_configured": False,
    "cpu_options": {"CoreCount": 1, "ThreadsPerCore": 1},
    "metadata_options": {"HttpTokens": "optional", "HttpEndpoint": "enabled"},
    "dry_run": False
}

prompt = (
    "Launch one or more EC2 instances via run_instances. Required: ami_id in payload.data. "
    "All other run_instances parameters are optional and passed through from payload.data. "
    "Return immediately with status:pending and instance_ids (async). "
    "check_completion polls describe_instances until all instances reach running state. "
    "Auth: access keys first, then assume_iam_role via STS, then default credential chain. "
    "finish() must close the boto3 client without re-raising exceptions."
)

install_docs = """# AWSEC2CreateInstance — Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": ["ec2:RunInstances", "ec2:DescribeInstances", "ec2:CreateTags", "ec2:DescribeRegions"],
      "Resource": "*"
    }

## Auth Setup

| Method             | How                                                                    |
|--------------------|------------------------------------------------------------------------|
| Access keys        | Set aws_access_key_id and aws_secret_access_key in connection          |
| Assume IAM role    | Set assume_iam_role (ARN) in connection — runner assumes it via STS    |
| Default chain      | Omit all auth fields — boto3 uses instance profile / ECS task role etc |
"""

guide_docs = """# AWSEC2CreateInstance — Operator Guide

## What it does

Launches one or more EC2 instances via run_instances and returns immediately with
status:pending and the instance IDs. This operator is **async** — check_completion
polls describe_instances until all instances reach running state.

Supports the full run_instances parameter surface: AMI, instance type, key pair,
security groups, subnet, IAM profile, user data, tags, block device mappings,
monitoring, EBS optimisation, placement, shutdown behaviour, termination protection,
hibernation, network interfaces, CPU options, metadata options, and more.

---

## Auth

Three methods are supported, evaluated in this priority order:

1. **Access keys** — if `aws_access_key_id` + `aws_secret_access_key` are present in the
   connection, they are used immediately.
2. **Assume IAM role** — if `assume_iam_role` (role ARN) is present and access keys are
   absent, the operator assumes the specified role via STS.
3. **Default credential chain** — boto3 falls back to EC2 instance profile, ECS task role,
   Lambda execution role, environment variables, or `~/.aws/credentials`.

---

## Connection

**Scenario 1 — Access keys:**

    {
      "region": "us-east-1",
      "aws_access_key_id": "AKIA...",          // IAM user access key
      "aws_secret_access_key": "...",           // IAM user secret key
      "aws_session_token": "..."                // only needed for temporary STS credentials
    }

**Scenario 2 — Assume IAM role:**

    {
      "region": "us-east-1",
      "assume_iam_role": "arn:aws:iam::123456789012:role/MyRole"
    }

**Scenario 3 — Default credential chain:**

    {"region": "us-east-1"}

| Field                 | Required   | Description                                              |
|-----------------------|------------|----------------------------------------------------------|
| region                | Yes        | AWS region to launch instances in                        |
| aws_access_key_id     | Scenario 1 | IAM user access key                                      |
| aws_secret_access_key | Scenario 1 | IAM user secret key                                      |
| aws_session_token     | No         | Temporary session token for STS-issued credentials       |
| assume_iam_role       | Scenario 2 | Role ARN to assume via STS                               |

---

## Payload

All fields go inside `payload.data`:

| Field                                  | Required | Description                                                        |
|----------------------------------------|----------|--------------------------------------------------------------------|
| ami_id                                 | Yes      | AMI ID to launch                                                   |
| instance_type                          | No       | EC2 instance type (default: t3.micro)                              |
| min_count                              | No       | Minimum instances to launch (default: 1)                           |
| max_count                              | No       | Maximum instances to launch (default: 1)                           |
| key_name                               | No       | EC2 key pair name for SSH access                                   |
| security_group_ids                     | No       | List of security group IDs (VPC)                                   |
| security_group_names                   | No       | List of security group names (EC2-Classic / default VPC)           |
| subnet_id                              | No       | Subnet ID to launch into                                           |
| iam_instance_profile                   | No       | IAM profile name or ARN                                            |
| user_data                              | No       | Cloud-init script — plain text, auto-encoded to base64             |
| tags                                   | No       | List of {"Key": str, "Value": str} applied to instance and volumes |
| block_device_mappings                  | No       | List of block device mapping dicts                                 |
| monitoring_enabled                     | No       | Boolean — enable detailed CloudWatch monitoring (default: false)   |
| ebs_optimized                          | No       | Boolean — enable EBS-optimized I/O                                 |
| availability_zone                      | No       | AZ to launch into                                                  |
| tenancy                                | No       | default / dedicated / host                                         |
| placement_group                        | No       | Placement group name                                               |
| host_id                                | No       | Dedicated host ID                                                  |
| instance_initiated_shutdown_behavior   | No       | stop or terminate on OS shutdown                                   |
| disable_api_termination                | No       | Boolean — enable termination protection                            |
| hibernation_configured                 | No       | Boolean — configure hibernation at launch                          |
| network_interfaces                     | No       | Advanced network interface dicts — replaces subnet_id/SGs          |
| private_ip_address                     | No       | Primary private IP (ignored when network_interfaces used)          |
| cpu_options                            | No       | {"CoreCount": int, "ThreadsPerCore": int}                          |
| metadata_options                       | No       | IMDSv2 config dict                                                 |
| client_token                           | No       | Idempotency token                                                  |
| dry_run                                | No       | Boolean — validate permissions without launching                   |

---

## Output (on success)

    {
      "instance_statuses": [
        {
          "instance_id": "i-0abc123def456789",
          "state": "running",
          "state_code": 16,
          "instance_type": "t3.micro",
          "private_ip": "10.0.1.5",
          "public_ip": "54.1.2.3",
          "availability_zone": "us-east-1a",
          "launch_time": "2024-01-01 00:00:00+00:00"
        }
      ]
    }
"""

description = """
Launches one or more EC2 instances via run_instances and returns immediately with
status:pending and instance_ids (async). check_completion polls describe_instances until all
instances reach running state. Supports the full run_instances parameter surface: AMI, instance
type, key pair, security groups, subnet, IAM profile, user data, tags, block device mappings,
monitoring, EBS optimisation, placement, shutdown behaviour, termination protection, hibernation,
network interfaces, CPU options, metadata options, dry_run, and more.
Auth: access keys first, then assume_iam_role via STS, then default credential chain.
finish() closes the boto3 client without re-raising exceptions.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "EC2",
    "category": "Compute",
    "tags": ["ec2", "instance", "create", "launch", "aws"],
    "airflow_equivalent": "EC2CreateInstanceOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

**AMI region binding**: AMI IDs are region-specific — `ami-0c02fb55956c7d316` is only valid
in `us-east-1`. Always verify the AMI exists in the target region before launching. Use
`ec2:DescribeImages` to look up the correct AMI ID per region.

**Security groups and subnets**: If both `security_group_ids` and `subnet_id` are provided,
the security groups must belong to the same VPC as the subnet — mismatches cause an
`InvalidGroup.NotFound` error. If only `security_group_names` are provided (no subnet), they
apply to EC2-Classic or the default VPC.

**IAM instance profile**: Specify as `{"Name": "profile-name"}` or `{"Arn": "arn:..."}`.
The profile must already exist — this operator does not create it. The execution role needs
`iam:PassRole` permission to attach a profile.

**network_interfaces vs top-level subnet/SG**: When `network_interfaces` is provided,
`subnet_id` and `security_group_ids` are removed from the top-level params to avoid
API conflicts — AWS only accepts one or the other, not both.

**Waiter and async**: This operator is async — `run()` returns immediately after
`run_instances` succeeds. `check_completion()` polls `describe_instances` until all
instances reach `running` state. An instance in `terminated` or `shutting-down` during
polling is treated as a launch failure.

**Cost awareness**: Instances start incurring charges from the moment they reach `pending`
state — not from `running`. Terminate test instances promptly after validation.
"""
