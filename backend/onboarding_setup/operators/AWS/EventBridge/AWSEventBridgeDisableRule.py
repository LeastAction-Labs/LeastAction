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
AWS EventBridge Disable Rule Operator

Disables an active EventBridge rule without deleting it. Synchronous.
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
            f"Initializing EventBridge disable rule operator for task: {task_laui}"
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
    Disable an active EventBridge rule using disable_rule.

    Payload fields:
        rule_name       (str, required)  -- name of the rule to disable
        event_bus_name  (str, optional)  -- event bus the rule belongs to (default: default)

    Returns:
        dict with status="success"|"failed", execution_type="sync", result
    """
    try:
        task_laui = least_action_task_object.get("laui")
        payload = least_action_task_object.get("payload", {})

        log_info(
            "task", "run", "extracting_payload",
            f"Extracting disable rule configuration for task: {task_laui}"
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

        kwargs = {"Name": rule_name}
        if payload.get("event_bus_name"):
            kwargs["EventBusName"] = payload["event_bus_name"]

        log_info(
            "task", "run", "disabling_rule",
            f"Disabling EventBridge rule: {rule_name} | bus={payload.get('event_bus_name', 'default')}"
        )

        client.disable_rule(**kwargs)

        log_info("task", "run", "rule_disabled",
                 f"Rule {rule_name} disabled successfully — rule config is preserved, use EnableRule to reactivate")

        return {
            "status": "success",
            "execution_type": "sync",
            "result": {
                "rule_name": rule_name,
                "state": "DISABLED",
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
    DisableRule is synchronous — pass through run_details directly.

    Returns:
        dict with status, message, output
    """
    if run_details.get("status") == "failed":
        log_error("task", "check_completion", "run_phase_failed",
                  f"Run phase reported failure: {run_details.get('error')}")
        return {
            "status": "failed",
            "message": f"DisableRule failed: {run_details.get('error')}",
            "output": run_details.get("result"),
        }

    result = run_details.get("result", {})
    log_info("task", "check_completion", "sync_complete",
             f"DisableRule completed — rule={result.get('rule_name')}, state={result.get('state')}")
    return {
        "status": "success",
        "message": f"EventBridge rule {result.get('rule_name')} is now DISABLED",
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
                     f"Rule {output.get('rule_name')} disabled — state={output.get('state')}")
        elif final_status == "failed":
            log_error("task", "finish", "operation_failed",
                      f"DisableRule operation failed: {completion_details.get('message')}")
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
    "rule_name": "my-rule",          # required
    # "event_bus_name": "default"    # optional — bus the rule belongs to
}

prompt = (
    "Disable an active EventBridge rule via disable_rule. Payload: rule_name (required). "
    "Optional: event_bus_name. Idempotent — disabling an already-disabled rule succeeds silently. "
    "Rule config is preserved — use EnableRule to reactivate. Synchronous — returns immediately. "
    "Auth: explicit keys first, then assume_iam_role via STS, then default credential chain. "
    "finish() must close the boto3 client without re-raising exceptions."
)

install_docs = """# AWSEventBridgeDisableRule — Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {"Effect": "Allow", "Action": ["events:DisableRule", "events:ListEventBuses"], "Resource": "*"}
"""

guide_docs = """# AWSEventBridgeDisableRule — Operator Guide

## What it does

Disables an active EventBridge rule without deleting it. Synchronous — returns immediately.
Idempotent — disabling an already-disabled rule succeeds with no error. The rule configuration
is preserved and can be reactivated with EnableRule. Disabled rules stop triggering but the
rule still exists and incurs the standard $1/month charge.

---

## Auth

1. **Access keys** — aws_access_key_id + aws_secret_access_key in connection
2. **Assume IAM role** — assume_iam_role (ARN) in connection, assumed via STS
3. **Default credential chain** — instance profile, ECS task role, env vars, ~/.aws/credentials

---

## Payload

| Field          | Required | Description                                      |
|----------------|----------|--------------------------------------------------|
| rule_name      | Yes      | Name of the rule to disable                      |
| event_bus_name | No       | Event bus the rule belongs to (default: default) |

---

## Output (on success)

    {"rule_name": "my-rule", "state": "DISABLED"}
"""

description = """
Disables an active EventBridge rule via disable_rule without deleting it. Synchronous —
returns immediately. Idempotent — disabling an already-disabled rule succeeds silently.
Rule config is preserved and can be reactivated with EnableRule.
Auth: explicit keys first, then assume_iam_role via STS, then default credential chain.
finish() closes the boto3 client without re-raising exceptions.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "EventBridge",
    "category": "Integration",
    "tags": ["eventbridge", "rule", "disable", "aws"],
    "airflow_equivalent": "EventBridgeDisableRuleOperator"
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
