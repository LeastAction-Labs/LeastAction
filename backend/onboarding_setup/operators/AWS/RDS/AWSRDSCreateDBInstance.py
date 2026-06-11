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
AWS RDS Create DB Instance Operator

Creates a new RDS DB instance. Async â€” polls until available.
Auth priority: explicit keys â†’ assume IAM role â†’ default credential chain.
Execution is async â€” run() triggers creation; check_completion() polls until available state.
"""

import json

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from src.common.logger.logger import log_error, log_info


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_rds_client(connection: dict):
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
        return session.client("rds")

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
        return session.client("rds")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info(
        "task", "initialize", "auth_default",
        "Using default AWS credential chain (instance profile / ECS task role / env / config)"
    )
    session = boto3.Session(region_name=region)
    return session.client("rds")


# ---------------------------------------------------------------------------
# Operator methods
# ---------------------------------------------------------------------------

def initialize(least_action_task_object):
    """
    Build and verify the RDS boto3 client.

    Returns:
        boto3 RDS client
    """
    try:
        connection = least_action_task_object.get("connection", {})
        task_laui = least_action_task_object.get("laui")

        log_info(
            "task", "initialize", "start",
            f"Initializing RDS create DB instance operator for task: {task_laui}"
        )

        rds_client = _build_rds_client(connection)

        region = connection.get("region", "us-east-1")
        log_info(
            "task", "initialize", "verify_connection",
            f"Verifying RDS connectivity in region: {region}"
        )
        rds_client.describe_db_instances(MaxRecords=20)

        log_info(
            "task", "initialize", "connection_established",
            f"RDS client ready for region: {region}"
        )
        return rds_client

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
    Create a new RDS DB instance using create_db_instance.

    Payload fields:
        db_instance_identifier       (str, required)           -- unique DB instance identifier
        db_instance_class            (str, required)           -- instance type, e.g. "db.t3.micro"
        engine                       (str, required)           -- e.g. "mysql", "postgres", "aurora-mysql"
        master_username              (str, required)           -- master username for DB
        master_user_password         (str, required)           -- master user password
        allocated_storage            (int, optional)           -- storage in GB, default 20
        db_name                      (str, optional)           -- initial database name
        db_subnet_group_name         (str, optional)           -- DB subnet group for VPC placement
        vpc_security_group_ids       (list[str], optional)     -- VPC security group IDs
        multi_az                     (bool, optional)          -- enable Multi-AZ, default False
        publicly_accessible          (bool, optional)          -- publicly accessible, default False
        backup_retention_period      (int, optional)           -- backup retention days, default 0 (disabled)
        engine_version               (str, optional)           -- specific engine version
        storage_type                 (str, optional)           -- gp2, gp3, io1, standard; default "gp2"
        iops                         (int, optional)           -- provisioned IOPS, only for io1/gp3
        storage_encrypted            (bool, optional)          -- enable storage encryption, default False
        kms_key_id                   (str, optional)           -- KMS key ARN for encryption
        auto_minor_version_upgrade   (bool, optional)          -- auto minor version upgrade, default True
        deletion_protection          (bool, optional)          -- enable deletion protection, default False
        tags                         (list[dict], optional)    -- list of {"Key": str, "Value": str}

    Returns:
        dict with status="pending", execution_type="async", result
    """
    try:
        task_laui = least_action_task_object.get("laui")
        payload = least_action_task_object.get("payload", {})

        log_info(
            "task", "run", "extracting_payload",
            f"Extracting create DB instance configuration for task: {task_laui}"
        )

        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                log_error("task", "run", "payload_parse_error", "Failed to parse payload as JSON")
                return {
                    "status": "failed",
                    "execution_type": "async",
                    "result": None,
                    "error": "Invalid payload format â€” expected flat JSON object",
                }

        db_instance_identifier = payload.get("db_instance_identifier")
        db_instance_class = payload.get("db_instance_class")
        engine = payload.get("engine")
        master_username = payload.get("master_username")
        master_user_password = payload.get("master_user_password")

        for field, val in [
            ("db_instance_identifier", db_instance_identifier),
            ("db_instance_class", db_instance_class),
            ("engine", engine),
            ("master_username", master_username),
            ("master_user_password", master_user_password),
        ]:
            if not val:
                log_error("task", "run", f"missing_{field}", f"{field} is required in payload")
                return {
                    "status": "failed",
                    "execution_type": "async",
                    "result": None,
                    "error": f"{field} is required in payload",
                }

        create_kwargs = {
            "DBInstanceIdentifier": db_instance_identifier,
            "DBInstanceClass": db_instance_class,
            "Engine": engine,
            "MasterUsername": master_username,
            "MasterUserPassword": master_user_password,
            "AllocatedStorage": payload.get("allocated_storage", 20),
        }

        if payload.get("db_name"):
            create_kwargs["DBName"] = payload["db_name"]
        if payload.get("db_subnet_group_name"):
            create_kwargs["DBSubnetGroupName"] = payload["db_subnet_group_name"]
        if payload.get("vpc_security_group_ids"):
            create_kwargs["VpcSecurityGroupIds"] = payload["vpc_security_group_ids"]
        if payload.get("multi_az") is not None:
            create_kwargs["MultiAZ"] = payload["multi_az"]
        if payload.get("publicly_accessible") is not None:
            create_kwargs["PubliclyAccessible"] = payload["publicly_accessible"]
        if payload.get("backup_retention_period") is not None:
            create_kwargs["BackupRetentionPeriod"] = payload["backup_retention_period"]
        if payload.get("engine_version"):
            create_kwargs["EngineVersion"] = payload["engine_version"]
        if payload.get("storage_type"):
            create_kwargs["StorageType"] = payload["storage_type"]
        if payload.get("iops"):
            create_kwargs["Iops"] = payload["iops"]
        if payload.get("storage_encrypted") is not None:
            create_kwargs["StorageEncrypted"] = payload["storage_encrypted"]
        if payload.get("kms_key_id"):
            create_kwargs["KmsKeyId"] = payload["kms_key_id"]
        if payload.get("auto_minor_version_upgrade") is not None:
            create_kwargs["AutoMinorVersionUpgrade"] = payload["auto_minor_version_upgrade"]
        if payload.get("deletion_protection") is not None:
            create_kwargs["DeletionProtection"] = payload["deletion_protection"]
        if payload.get("tags"):
            create_kwargs["Tags"] = payload["tags"]

        log_info(
            "task", "run", "creating_db_instance",
            f"Issuing create_db_instance for: {db_instance_identifier} "
            f"(engine={engine}, class={db_instance_class})"
        )

        response = client.create_db_instance(**create_kwargs)
        db_arn = response["DBInstance"]["DBInstanceArn"]

        log_info(
            "task", "run", "create_issued",
            f"create_db_instance call succeeded for {db_instance_identifier} â€” "
            f"ARN: {db_arn} â€” instance is provisioning asynchronously"
        )

        return {
            "status": "pending",
            "execution_type": "async",
            "result": {
                "db_instance_identifier": db_instance_identifier,
                "db_instance_arn": db_arn,
                "engine": engine,
                "db_instance_class": db_instance_class,
            },
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "client_error", f"AWS ClientError ({error_code}): {error_msg}")
        return {
            "status": "failed",
            "execution_type": "async",
            "result": None,
            "error": f"{error_code}: {error_msg}",
        }
    except Exception as e:
        log_error("task", "run", "unexpected_error", f"Unexpected error during run: {str(e)}")
        return {
            "status": "failed",
            "execution_type": "async",
            "result": None,
            "error": str(e),
        }


def check_completion(least_action_task_object, client, run_details):
    """
    Poll describe_db_instances to determine whether the DB instance is available.

    Returns:
        dict with status (success | pending | failed), message, output
    """
    try:
        if run_details.get("status") == "failed":
            log_error("task", "check_completion", "run_phase_failed",
                      f"Run phase reported failure: {run_details.get('error')}")
            return {
                "status": "failed",
                "message": f"Create failed in run phase: {run_details.get('error')}",
                "output": None,
            }

        result = run_details.get("result", {})
        db_instance_identifier = result.get("db_instance_identifier")
        if not db_instance_identifier:
            return {"status": "failed", "message": "No db_instance_identifier in run_details", "output": None}

        log_info(
            "task", "check_completion", "polling_db_status",
            f"Polling describe_db_instances for: {db_instance_identifier}"
        )

        response = client.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
        db = response["DBInstances"][0]
        db_status = db.get("DBInstanceStatus", "unknown")

        log_info(
            "task", "check_completion", "db_instance_status",
            f"DB instance {db_instance_identifier}: status={db_status}"
        )

        if db_status == "available":
            endpoint = db.get("Endpoint", {})
            log_info("task", "check_completion", "db_available",
                     f"DB instance {db_instance_identifier} is available")
            return {
                "status": "success",
                "message": f"DB instance {db_instance_identifier} is available",
                "output": {
                    "db_instance_identifier": db_instance_identifier,
                    "db_instance_arn": result.get("db_instance_arn"),
                    "db_instance_status": db_status,
                    "endpoint": endpoint.get("Address", ""),
                    "port": endpoint.get("Port", 0),
                    "engine": db.get("Engine", ""),
                    "db_instance_class": db.get("DBInstanceClass", ""),
                },
            }

        if db_status in ("failed", "incompatible-parameters", "incompatible-restore"):
            log_error("task", "check_completion", "db_failed",
                      f"DB instance {db_instance_identifier} entered failure state: {db_status}")
            return {
                "status": "failed",
                "message": f"DB instance entered failure state: {db_status}",
                "output": {"db_instance_identifier": db_instance_identifier, "db_instance_status": db_status},
            }

        log_info("task", "check_completion", "db_still_creating",
                 f"DB instance {db_instance_identifier} still provisioning â€” current status: {db_status}")
        return {
            "status": "pending",
            "message": f"DB instance status: {db_status}",
            "output": {"db_instance_identifier": db_instance_identifier, "db_instance_status": db_status},
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "check_completion", "client_error", f"AWS ClientError ({error_code}): {error_msg}")
        return {"status": "failed", "message": f"{error_code}: {error_msg}", "output": None}
    except Exception as e:
        log_error("task", "check_completion", "unexpected_error",
                  f"Unexpected error during completion check: {str(e)}")
        return {"status": "failed", "message": f"Completion check error: {str(e)}", "output": None}


def finish(least_action_task_object, client, completion_details, run_details):
    """
    Log final outcome and release any held resources.

    Returns:
        None
    """
    try:
        task_laui = least_action_task_object.get("laui")
        log_info("task", "finish", "starting_cleanup", f"Starting cleanup for task: {task_laui}")

        final_status = completion_details.get("status", "unknown")
        log_info("task", "finish", "final_status", f"Task ended with status: {final_status}")

        if client:
            try:
                client.close()
                log_info("task", "finish", "client_closed", "RDS boto3 client connection closed successfully")
            except Exception as close_error:
                log_error("task", "finish", "client_close_error", f"Error closing RDS client: {str(close_error)}")

        if final_status == "success":
            output = completion_details.get("output", {})
            log_info(
                "task", "finish", "operation_summary",
                f"DB instance {output.get('db_instance_identifier')} created â€” "
                f"status={output.get('db_instance_status')}, endpoint={output.get('endpoint')}, "
                f"port={output.get('port')}"
            )
        elif final_status == "failed":
            log_error("task", "finish", "operation_failed",
                      f"Create operation failed: {completion_details.get('message')}")
        else:
            log_info("task", "finish", "operation_status",
                     f"Operation ended with status={final_status}, message={completion_details.get('message')}")

        log_info("task", "finish", "cleanup_complete", f"Cleanup complete for task: {task_laui}")

    except Exception as e:
        log_error("task", "finish", "cleanup_error", f"Error during finish/cleanup: {str(e)}")
        # Never re-raise from finish â€” allow graceful task completion
'''}

bashblock = {"main.sh": """#!/bin/bash
set -e
pip install boto3>=1.28.0
pip install botocore>=1.31.0
echo "Dependencies installed successfully"
"""}

connection = {"region": "us-east-1"}

payload = {
    "db_instance_identifier": "my-db",            # required
    "db_instance_class": "db.t3.micro",            # required â€” instance type
    "engine": "mysql",                             # required â€” e.g. mysql, postgres, aurora-mysql
    "master_username": "admin",                    # required
    "master_user_password": "MyPassword123!",      # required
    # "allocated_storage": 20,                     # optional â€” storage in GB, default 20
    # "db_name": "mydb",                           # optional â€” initial database name
    # "db_subnet_group_name": "my-subnet-group",   # optional â€” for VPC placement
    # "vpc_security_group_ids": ["sg-xxx"],        # optional
    # "multi_az": False,                           # optional â€” default False
    # "publicly_accessible": False,                # optional â€” default False
    # "backup_retention_period": 0,                # optional â€” 0 disables automated backups
    # "engine_version": "8.0.35",                  # optional
    # "storage_type": "gp2",                       # optional â€” gp2, gp3, io1, standard
    # "iops": 3000,                                # optional â€” only for io1/gp3
    # "storage_encrypted": False,                  # optional â€” default False
    # "kms_key_id": "arn:aws:kms:...",             # optional â€” KMS key ARN for encryption
    # "auto_minor_version_upgrade": True,          # optional â€” default True
    # "deletion_protection": False,                # optional â€” default False
    # "tags": [{"Key": "Env", "Value": "dev"}]    # optional
}

prompt = (
    "Create a new RDS DB instance. Payload: db_instance_identifier, db_instance_class, engine, "
    "master_username, master_user_password (all required). "
    "Optional: allocated_storage, db_name, db_subnet_group_name, vpc_security_group_ids, "
    "multi_az, publicly_accessible, backup_retention_period, engine_version, storage_type, iops, "
    "storage_encrypted, kms_key_id, auto_minor_version_upgrade, deletion_protection, tags. "
    "Call create_db_instance and return immediately with status:pending (async). "
    "check_completion polls describe_db_instances until the instance reaches available state. "
    "Auth: explicit keys first, then assume_iam_role via STS, then default credential chain. "
    "finish() must close the boto3 client without re-raising exceptions."
)

install_docs = """# AWSRDSCreateDBInstance â€” Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {"Effect": "Allow", "Action": ["rds:CreateDBInstance", "rds:DescribeDBInstances"], "Resource": "*"}

## Auth Setup

| Method             | How                                                                    |
|--------------------|------------------------------------------------------------------------|
| Access keys        | Set aws_access_key_id and aws_secret_access_key in connection          |
| Assume IAM role    | Set assume_iam_role (ARN) in connection â€” runner assumes it via STS    |
| Default chain      | Omit all auth fields â€” boto3 uses instance profile / ECS task role etc |

## Prerequisites

- DB subnet group must exist in target VPC if specifying db_subnet_group_name
"""

guide_docs = """# AWSRDSCreateDBInstance â€” Operator Guide

## What it does

Creates a new RDS DB instance and returns immediately with status:pending (async).
check_completion polls describe_db_instances until the instance reaches available state (typically 5-10 min).

---

## Auth

1. **Access keys** â€” aws_access_key_id + aws_secret_access_key in connection
2. **Assume IAM role** â€” assume_iam_role (ARN) in connection, assumed via STS
3. **Default credential chain** â€” instance profile, ECS task role, env vars, ~/.aws/credentials

---

## Connection

**Scenario 1:** `{"region": "us-east-1", "aws_access_key_id": "AKIA...", "aws_secret_access_key": "..."}`
**Scenario 2:** `{"region": "us-east-1", "assume_iam_role": "arn:aws:iam::123456789012:role/MyRole"}`
**Scenario 3:** `{"region": "us-east-1"}`

---

## Payload

| Field                      | Required | Description                                               |
|----------------------------|----------|-----------------------------------------------------------|
| db_instance_identifier     | Yes      | Unique DB instance identifier                             |
| db_instance_class          | Yes      | Instance type, e.g. "db.t3.micro"                        |
| engine                     | Yes      | Engine type: mysql, postgres, aurora-mysql, etc.          |
| master_username            | Yes      | Master username                                           |
| master_user_password       | Yes      | Master user password                                      |
| allocated_storage          | No       | Storage in GB, default 20                                 |
| db_name                    | No       | Initial database name                                     |
| db_subnet_group_name       | No       | DB subnet group for VPC placement                         |
| vpc_security_group_ids     | No       | List of VPC security group IDs                            |
| multi_az                   | No       | Enable Multi-AZ, default False                            |
| publicly_accessible        | No       | Publicly accessible, default False                        |
| backup_retention_period    | No       | Backup retention days (0 = disabled), default 0           |
| engine_version             | No       | Specific engine version                                   |
| storage_type               | No       | gp2, gp3, io1, standard; default "gp2"                   |
| iops                       | No       | Provisioned IOPS, only for io1/gp3                        |
| storage_encrypted          | No       | Enable storage encryption, default False                  |
| kms_key_id                 | No       | KMS key ARN for encryption                                |
| auto_minor_version_upgrade | No       | Auto minor version upgrade, default True                  |
| deletion_protection        | No       | Enable deletion protection, default False                 |
| tags                       | No       | List of {"Key": str, "Value": str}                        |

---

## Output (on success)

    {
      "db_instance_identifier": "my-db",
      "db_instance_arn": "arn:aws:rds:us-east-1:123456789012:db:my-db",
      "db_instance_status": "available",
      "endpoint": "my-db.abc123.us-east-1.rds.amazonaws.com",
      "port": 3306,
      "engine": "mysql",
      "db_instance_class": "db.t3.micro"
    }
"""

description = """
Creates a new RDS DB instance (async). Calls create_db_instance and returns immediately.
check_completion polls describe_db_instances until the instance reaches available state.
Supports full configuration including storage, networking, encryption, and backup settings.
Auth: explicit keys first, then assume_iam_role via STS, then default credential chain.
finish() closes the boto3 client without re-raising exceptions.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "RDS",
    "category": "Database",
    "tags": ["rds", "database", "create", "mysql", "postgres", "aws"],
    "airflow_equivalent": "RdsCreateDbInstanceOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Notes

This operator has been reviewed and tested by LeastActionLabs.
"""
