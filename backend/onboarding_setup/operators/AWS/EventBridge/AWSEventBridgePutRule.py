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
AWS EventBridge Put Rule Operator

Creates or updates an EventBridge rule triggered by a schedule or event pattern. Synchronous.
Auth priority: explicit keys → assume IAM role → default credential chain.
"""

import json

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from src.common.logger.logger import log_error, log_info


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_events_client(connection: dict):
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
        return session.client("events")

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
        return session.client("events")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info(
        "task", "initialize", "auth_default",
        "Using default AWS credential chain (instance profile / ECS task role / env / config)"
    )
    session = boto3.Session(region_name=region)
    return session.client("events")


# ---------------------------------------------------------------------------
# Operator methods
# ---------------------------------------------------------------------------

def initialize(least_action_task_object):
    """
    Build and verify the EventBridge boto3 client.

    Returns:
        boto3 events client
    """
    try:
        connection = least_action_task_object.get("connection", {})
        task_laui = least_action_task_object.get("laui")

        log_info(
            "task", "initialize", "start",
            f"Initializing EventBridge put rule operator for task: {task_laui}"
        )

        events_client = _build_events_client(connection)

        region = connection.get("region", "us-east-1")
        log_info(
            "task", "initialize", "verify_connection",
            f"Verifying EventBridge connectivity in region: {region}"
        )
        events_client.list_event_buses(Limit=1)

        log_info(
            "task", "initialize", "connection_established",
            f"EventBridge client ready for region: {region}"
        )
        return events_client

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "initialize", "client_error", f"AWS ClientError ({error_code}): {error_msg}")
        raise
    except BotoCoreError as e:
        log_error("task", "initialize", "botocore_error", f"BotoCoreError during initialization: {str(e)}")
        raise
    except Exception as e:
        log_error("task", "initialize", "unexpected_error", f"Unexpected error during initialization: {str(e)}")
        raise


def run(least_action_task_object, client):
    """
    Create or update an EventBridge rule using put_rule.

    Payload fields:
        rule_name             (str, required)    -- unique rule name
        schedule_expression   (str, optional)    -- e.g. "rate(5 minutes)", "cron(0 12 * * ? *)"
        event_pattern         (str|dict, optional) -- event pattern JSON; dict auto-serialized
        state                 (str, optional)    -- ENABLED or DISABLED (default: ENABLED)
        description           (str, optional)    -- human-readable rule description
        event_bus_name        (str, optional)    -- target event bus name or ARN (default: default)
        role_arn              (str, optional)    -- IAM role ARN for EventBridge to use
        tags                  (list[dict], optional) -- list of {"Key": str, "Value": str}

    Note: provide either schedule_expression OR event_pattern, not both.

    Returns:
        dict with status="success"|"failed", execution_type="sync", result
    """
    try:
        task_laui = least_action_task_object.get("laui")
        payload = least_action_task_object.get("payload", {})

        log_info(
            "task", "run", "extracting_payload",
            f"Extracting put rule configuration for task: {task_laui}"
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
                    "error": "Invalid payload format — expected flat JSON object",
                }

        rule_name = payload.get("rule_name")
        if not rule_name:
            log_error("task", "run", "missing_rule_name", "rule_name is required in payload")
            return {
                "status": "failed",
                "execution_type": "sync",
                "result": None,
                "error": "rule_name is required in payload",
            }

        kwargs = {
            "Name": rule_name,
            "State": payload.get("state", "ENABLED"),
        }

        schedule_expression = payload.get("schedule_expression")
        if schedule_expression:
            kwargs["ScheduleExpression"] = schedule_expression
            log_info("task", "run", "schedule", f"Schedule expression: {schedule_expression}")

        event_pattern = payload.get("event_pattern")
        if event_pattern:
            kwargs["EventPattern"] = json.dumps(event_pattern) if isinstance(event_pattern, dict) else event_pattern
            log_info("task", "run", "event_pattern", "Event pattern specified")

        if payload.get("description"):
            kwargs["Description"] = payload["description"]
        if payload.get("event_bus_name"):
            kwargs["EventBusName"] = payload["event_bus_name"]
        if payload.get("role_arn"):
            kwargs["RoleArn"] = payload["role_arn"]
        if payload.get("tags"):
            kwargs["Tags"] = payload["tags"]

        log_info(
            "task", "run", "putting_rule",
            f"Creating/updating EventBridge rule: {rule_name} | state={kwargs['State']}"
        )

        response = client.put_rule(**kwargs)
        rule_arn = response.get("RuleArn", "")

        log_info(
            "task", "run", "rule_created",
            f"Rule {rule_name} created/updated successfully — ARN: {rule_arn}"
        )

        return {
            "status": "success",
            "execution_type": "sync",
            "result": {
                "rule_name": rule_name,
                "rule_arn": rule_arn,
                "state": kwargs["State"],
            },
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "client_error", f"AWS ClientError ({error_code}): {error_msg}")
        return {"status": "failed", "execution_type": "sync", "result": None, "error": f"{error_code}: {error_msg}"}
    except Exception as e:
        log_error("task", "run", "unexpected_error", f"Unexpected error during run: {str(e)}")
        return {"status": "failed", "execution_type": "sync", "result": None, "error": str(e)}


def check_completion(least_action_task_object, client, run_details):
    """
    PutRule is synchronous — pass through run_details directly.

    Returns:
        dict with status, message, output
    """
    if run_details.get("status") == "failed":
        log_error("task", "check_completion", "run_phase_failed",
                  f"Run phase reported failure: {run_details.get('error')}")
        return {
            "status": "failed",
            "message": f"PutRule failed: {run_details.get('error')}",
            "output": run_details.get("result"),
        }

    result = run_details.get("result", {})
    log_info(
        "task", "check_completion", "sync_complete",
        f"PutRule completed — rule={result.get('rule_name')}, ARN={result.get('rule_arn')}"
    )
    return {
        "status": "success",
        "message": f"EventBridge rule {result.get('rule_name')} created/updated successfully",
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
                log_info("task", "finish", "client_closed",
                         "EventBridge boto3 client connection closed successfully")
            except Exception as close_error:
                log_error("task", "finish", "client_close_error",
                          f"Error closing EventBridge client: {str(close_error)}")

        if final_status == "success":
            output = completion_details.get("output", {})
            log_info("task", "finish", "operation_summary",
                     f"Rule {output.get('rule_name')} — ARN: {output.get('rule_arn')}, state: {output.get('state')}")
        elif final_status == "failed":
            log_error("task", "finish", "operation_failed",
                      f"PutRule operation failed: {completion_details.get('message')}")
        else:
            log_info("task", "finish", "operation_status",
                     f"Operation ended with status={final_status}, message={completion_details.get('message')}")

        log_info("task", "finish", "cleanup_complete", f"Cleanup complete for task: {task_laui}")

    except Exception as e:
        log_error("task", "finish", "cleanup_error", f"Error during finish/cleanup: {str(e)}")
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
    "rule_name": "my-rule",                          # required
    "schedule_expression": "rate(5 minutes)",         # optional — provide this OR event_pattern
    # "event_pattern": {"source": ["aws.s3"]},        # optional — provide this OR schedule_expression
    "state": "ENABLED",                              # optional — ENABLED or DISABLED (default: ENABLED)
    # "description": "My EventBridge rule",           # optional
    # "event_bus_name": "default",                    # optional — bus name or ARN
    # "role_arn": "arn:aws:iam::123456789012:role/MyRole",  # optional
    # "tags": [{"Key": "Env", "Value": "prod"}]       # optional
}

prompt = (
    "Create or update an EventBridge rule via put_rule. Payload: rule_name (required). "
    "Optional: schedule_expression, event_pattern (dict or JSON string), state (default ENABLED), "
    "description, event_bus_name, role_arn, tags. Provide either schedule_expression OR event_pattern. "
    "Synchronous — returns rule ARN immediately. "
    "Auth: explicit keys first, then assume_iam_role via STS, then default credential chain. "
    "finish() must close the boto3 client without re-raising exceptions."
)

install_docs = """# AWSEventBridgePutRule — Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {"Effect": "Allow", "Action": ["events:PutRule", "events:ListEventBuses"], "Resource": "*"}
"""

guide_docs = """# AWSEventBridgePutRule — Operator Guide

## What it does

Creates or updates an EventBridge rule triggered by a schedule or event pattern. Synchronous —
returns the rule ARN immediately. Rules are idempotent — calling put_rule with the same name
updates the existing rule.

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

## Payload

| Field               | Required | Description                                                              |
|---------------------|----------|--------------------------------------------------------------------------|
| rule_name           | Yes      | Unique rule name                                                         |
| schedule_expression | No*      | e.g. "rate(5 minutes)", "cron(0 12 * * ? *)"                            |
| event_pattern       | No*      | Event pattern dict or JSON string                                        |
| state               | No       | ENABLED or DISABLED (default: ENABLED)                                   |
| description         | No       | Human-readable description                                               |
| event_bus_name      | No       | Target bus name or ARN (default: default)                                |
| role_arn            | No       | IAM role ARN for EventBridge to assume                                   |
| tags                | No       | List of {"Key": str, "Value": str}                                       |

*Provide either schedule_expression OR event_pattern (not both).

---

## Output (on success)

    {"rule_name": "my-rule", "rule_arn": "arn:aws:events:...", "state": "ENABLED"}
"""

description = """
Creates or updates an EventBridge rule triggered by a schedule expression or event pattern.
Synchronous — returns the rule ARN immediately. Idempotent — calling with the same rule name
updates the existing rule. Provide either schedule_expression (e.g. rate(5 minutes)) or
event_pattern (dict auto-serialized to JSON), not both.
Auth: explicit keys first, then assume_iam_role via STS, then default credential chain.
finish() closes the boto3 client without re-raising exceptions.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "EventBridge",
    "category": "Integration",
    "tags": ["eventbridge", "rule", "schedule", "aws"],
    "airflow_equivalent": "EventBridgePutRuleOperator"
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
