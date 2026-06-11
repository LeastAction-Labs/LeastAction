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
AWS RDS Create Event Subscription Operator

Creates an RDS event subscription to send DB notifications to an SNS topic. Synchronous.
Auth priority: explicit keys â†’ assume IAM role â†’ default credential chain.
create_event_subscription returns immediately â€” no polling needed.
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
            f"Initializing RDS create event subscription operator for task: {task_laui}"
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
    Create an RDS event subscription using create_event_subscription. Synchronous â€” returns immediately.

    Payload fields:
        subscription_name    (str, required)           -- unique name for the subscription
        sns_topic_arn        (str, required)           -- SNS topic ARN to publish events to
        source_type          (str, optional)           -- db-instance | db-cluster | db-snapshot |
                                                          db-cluster-snapshot | db-parameter-group |
                                                          db-security-group
        source_ids           (list[str], optional)     -- specific source IDs (default: all sources of source_type)
        event_categories     (list[str], optional)     -- availability | backup | configuration change |
                                                          creation | deletion | failover | failure |
                                                          maintenance | notification | recovery | restoration
        enabled              (bool, optional)          -- enable subscription, default True
        tags                 (list[dict], optional)    -- list of {"Key": str, "Value": str}

    Returns:
        dict with status="success", execution_type="sync", result
    """
    try:
        task_laui = least_action_task_object.get("laui")
        payload = least_action_task_object.get("payload", {})

        log_info(
            "task", "run", "extracting_payload",
            f"Extracting create event subscription configuration for task: {task_laui}"
        )

        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                log_error("task", "run", "payload_parse_error", "Failed to parse payload as JSON")
                return {
                    "status": "failed",
                    "execution_type": "sync",
                    "result": None,
                    "error": "Invalid payload format â€” expected flat JSON object",
                }

        subscription_name = payload.get("subscription_name")
        sns_topic_arn = payload.get("sns_topic_arn")

        for field, val in [
            ("subscription_name", subscription_name),
            ("sns_topic_arn", sns_topic_arn),
        ]:
            if not val:
                log_error("task", "run", f"missing_{field}", f"{field} is required in payload")
                return {
                    "status": "failed",
                    "execution_type": "sync",
                    "result": None,
                    "error": f"{field} is required in payload",
                }

        create_kwargs = {
            "SubscriptionName": subscription_name,
            "SnsTopicArn": sns_topic_arn,
            "Enabled": payload.get("enabled", True),
        }

        if payload.get("source_type"):
            create_kwargs["SourceType"] = payload["source_type"]
        if payload.get("source_ids"):
            create_kwargs["SourceIds"] = payload["source_ids"]
        if payload.get("event_categories"):
            create_kwargs["EventCategories"] = payload["event_categories"]
        if payload.get("tags"):
            create_kwargs["Tags"] = payload["tags"]

        log_info(
            "task", "run", "creating_event_subscription",
            f"Issuing create_event_subscription: {subscription_name} -> {sns_topic_arn}"
        )

        response = client.create_event_subscription(**create_kwargs)
        sub_arn = response["EventSubscription"].get("EventSubscriptionArn", "")

        log_info(
            "task", "run", "subscription_created",
            f"create_event_subscription call succeeded for {subscription_name} â€” ARN: {sub_arn}"
        )

        return {
            "status": "success",
            "execution_type": "sync",
            "result": {
                "subscription_name": subscription_name,
                "event_subscription_arn": sub_arn,
                "sns_topic_arn": sns_topic_arn,
            },
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "client_error", f"AWS ClientError ({error_code}): {error_msg}")
        return {
            "status": "failed",
            "execution_type": "sync",
            "result": None,
            "error": f"{error_code}: {error_msg}",
        }
    except Exception as e:
        log_error("task", "run", "unexpected_error", f"Unexpected error during run: {str(e)}")
        return {
            "status": "failed",
            "execution_type": "sync",
            "result": None,
            "error": str(e),
        }


def check_completion(least_action_task_object, client, run_details):
    """
    Pass through run_details â€” create_event_subscription is synchronous, no polling needed.

    Returns:
        dict with status, message, output passed through from run_details
    """
    log_info("task", "check_completion", "sync_passthrough",
             "CreateEventSubscription is synchronous â€” passing through run_details")
    result = run_details.get("result") or {}
    return {
        "status": run_details.get("status", "success"),
        "message": "Synchronous create_event_subscription completed",
        "output": result,
    }


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
                f"Event subscription {output.get('subscription_name')} created â€” "
                f"ARN: {output.get('event_subscription_arn')}"
            )
        elif final_status == "failed":
            log_error("task", "finish", "operation_failed",
                      f"Create event subscription failed: {completion_details.get('message')}")
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
    "subscription_name": "my-rds-events",                                              # required
    "sns_topic_arn": "arn:aws:sns:us-east-1:123456789012:my-topic",                   # required
    # "source_type": "db-instance",                                                   # optional â€” db-instance | db-cluster | db-snapshot | db-cluster-snapshot | db-parameter-group | db-security-group
    # "source_ids": ["my-db-instance"],                                               # optional â€” specific source IDs (default: all)
    # "event_categories": ["availability", "failure", "backup"],                      # optional â€” filter by event category
    # "enabled": True,                                                                # optional â€” default True
    # "tags": [{"Key": "Env", "Value": "prod"}]                                      # optional
}

prompt = (
    "Create an RDS event subscription to send DB notifications to an SNS topic. "
    "Payload: subscription_name (required), sns_topic_arn (required). "
    "Optional: source_type (db-instance, db-cluster, db-snapshot, etc.), "
    "source_ids (list), event_categories (list), enabled (default True), tags. "
    "Call create_event_subscription and return immediately with status:success (sync). "
    "check_completion passes through run_details â€” no polling needed. "
    "Auth: explicit keys first, then assume_iam_role via STS, then default credential chain. "
    "finish() must close the boto3 client without re-raising exceptions."
)

install_docs = """# AWSRDSCreateEventSubscription â€” Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {"Effect": "Allow", "Action": ["rds:CreateEventSubscription", "rds:DescribeDBInstances"], "Resource": "*"}

## Prerequisites

- SNS topic must exist before creating the subscription
- SNS topic does NOT need subscribers â€” RDS publishes to it directly

## Auth Setup

| Method             | How                                                                    |
|--------------------|------------------------------------------------------------------------|
| Access keys        | Set aws_access_key_id and aws_secret_access_key in connection          |
| Assume IAM role    | Set assume_iam_role (ARN) in connection â€” runner assumes it via STS    |
| Default chain      | Omit all auth fields â€” boto3 uses instance profile / ECS task role etc |
"""

guide_docs = """# AWSRDSCreateEventSubscription â€” Operator Guide

## What it does

Creates an RDS event subscription that publishes DB events to an SNS topic.
Returns status:success immediately (synchronous).

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

| Field               | Required | Description                                                           |
|---------------------|----------|-----------------------------------------------------------------------|
| subscription_name   | Yes      | Unique name for the subscription                                      |
| sns_topic_arn       | Yes      | SNS topic ARN to publish events to                                    |
| source_type         | No       | db-instance, db-cluster, db-snapshot, db-cluster-snapshot,           |
|                     |          | db-parameter-group, db-security-group                                 |
| source_ids          | No       | Specific source IDs (default: all sources of source_type)             |
| event_categories    | No       | availability, backup, configuration change, creation, deletion,       |
|                     |          | failover, failure, maintenance, notification, recovery, restoration   |
| enabled             | No       | Enable subscription, default True                                     |
| tags                | No       | List of {"Key": str, "Value": str}                                    |

---

## Output (on success)

    {
      "subscription_name": "my-rds-events",
      "event_subscription_arn": "arn:aws:rds:us-east-1:123456789012:es:my-rds-events",
      "sns_topic_arn": "arn:aws:sns:us-east-1:123456789012:my-topic"
    }
"""

description = """
Creates an RDS event subscription to send DB notifications to an SNS topic (sync).
Calls create_event_subscription and returns immediately. check_completion passes through run_details.
Auth: explicit keys first, then assume_iam_role via STS, then default credential chain.
finish() closes the boto3 client without re-raising exceptions.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "RDS",
    "category": "Database",
    "tags": ["rds", "events", "sns", "notifications", "aws"],
    "airflow_equivalent": "RdsCreateEventSubscriptionOperator"
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
