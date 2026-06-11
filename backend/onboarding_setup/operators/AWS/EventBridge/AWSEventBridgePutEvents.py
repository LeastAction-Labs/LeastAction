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
AWS EventBridge Put Events Operator

Sends one or more custom events to an EventBridge event bus. Synchronous.
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
            f"Initializing EventBridge put events operator for task: {task_laui}"
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
    Send one or more events to an EventBridge event bus using put_events.

    Payload fields:
        entries  (list[dict], required)  -- list of event entry dicts, each containing:
            Source        (str, required)   -- event source identifier, e.g. "com.myapp.orders"
            DetailType    (str, required)   -- free-form event type string, e.g. "OrderPlaced"
            Detail        (str|dict, required) -- event payload; dict is auto-serialized to JSON
            EventBusName  (str, optional)   -- target event bus name or ARN (default: "default")
            Resources     (list[str], optional) -- ARNs of resources involved in the event
            Time          (str, optional)   -- ISO8601 timestamp to associate with the event

    Returns:
        dict with status="success"|"failed", execution_type="sync", result
    """
    try:
        task_laui = least_action_task_object.get("laui")
        payload = least_action_task_object.get("payload", {})

        log_info(
            "task", "run", "extracting_payload",
            f"Extracting put events configuration for task: {task_laui}"
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

        entries = payload.get("entries", [])
        if not entries:
            log_error("task", "run", "missing_entries", "entries is required and must be non-empty")
            return {
                "status": "failed",
                "execution_type": "sync",
                "result": None,
                "error": "entries is required and must be non-empty",
            }

        formatted = []
        for i, e in enumerate(entries):
            entry = {}
            if e.get("Source"):
                entry["Source"] = e["Source"]
            if e.get("DetailType"):
                entry["DetailType"] = e["DetailType"]
            detail = e.get("Detail", "{}")
            entry["Detail"] = json.dumps(detail) if isinstance(detail, dict) else detail
            entry["EventBusName"] = e.get("EventBusName", "default")
            if e.get("Resources"):
                entry["Resources"] = e["Resources"]
            if e.get("Time"):
                entry["Time"] = e["Time"]
            formatted.append(entry)
            log_info(
                "task", "run", "entry_prepared",
                f"Entry {i+1}: Source={entry.get('Source')} | "
                f"DetailType={entry.get('DetailType')} | Bus={entry.get('EventBusName')}"
            )

        log_info(
            "task", "run", "putting_events",
            f"Sending {len(formatted)} event(s) to EventBridge"
        )

        response = client.put_events(Entries=formatted)
        failed_count = response.get("FailedEntryCount", 0)
        result_entries = [
            {
                "event_id": r.get("EventId", ""),
                "error_code": r.get("ErrorCode", ""),
                "error_message": r.get("ErrorMessage", ""),
            }
            for r in response.get("Entries", [])
        ]

        if failed_count > 0:
            log_error(
                "task", "run", "some_events_failed",
                f"{failed_count} of {len(formatted)} events failed to deliver"
            )
            return {
                "status": "failed",
                "execution_type": "sync",
                "result": {
                    "sent_count": len(formatted) - failed_count,
                    "failed_count": failed_count,
                    "entries": result_entries,
                },
            }

        log_info(
            "task", "run", "events_sent",
            f"All {len(formatted)} event(s) delivered successfully"
        )
        return {
            "status": "success",
            "execution_type": "sync",
            "result": {
                "sent_count": len(formatted),
                "failed_count": 0,
                "entries": result_entries,
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
    PutEvents is synchronous — pass through run_details directly.

    Returns:
        dict with status, message, output
    """
    if run_details.get("status") == "failed":
        log_error("task", "check_completion", "run_phase_failed",
                  f"Run phase reported failure: {run_details.get('error')}")
        return {
            "status": "failed",
            "message": f"PutEvents failed: {run_details.get('error')}",
            "output": run_details.get("result"),
        }

    result = run_details.get("result", {})
    log_info(
        "task", "check_completion", "sync_complete",
        f"PutEvents completed — sent={result.get('sent_count', 0)}, failed={result.get('failed_count', 0)}"
    )
    return {
        "status": "success",
        "message": f"All {result.get('sent_count', 0)} event(s) delivered to EventBridge",
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
                     f"Successfully delivered {output.get('sent_count', 0)} event(s) to EventBridge")
        elif final_status == "failed":
            log_error("task", "finish", "operation_failed",
                      f"PutEvents operation failed: {completion_details.get('message')}")
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
    "entries": [
        {
            "Source": "com.leastaction.pipeline",       # required — event source identifier
            "DetailType": "PipelineCompleted",           # required — event type label
            "Detail": {"status": "success", "pipeline": "my-pipeline"},  # required — event payload (dict auto-serialized)
            "EventBusName": "default",                   # optional — target bus name or ARN (default: "default")
            # "Resources": ["arn:aws:..."],              # optional — ARNs of involved resources
            # "Time": "2024-01-01T00:00:00Z"            # optional — ISO8601 event timestamp
        }
    ]
}

prompt = (
    "Send one or more events to an EventBridge event bus via put_events. "
    "Payload: entries (list of event dicts). Each entry requires Source, DetailType, Detail. "
    "Detail can be a dict (auto-serialized to JSON) or a JSON string. "
    "EventBusName defaults to 'default'. Up to 10 entries per call. "
    "Synchronous — returns event IDs and failed count immediately. "
    "Auth: explicit keys first, then assume_iam_role via STS, then default credential chain. "
    "finish() must close the boto3 client without re-raising exceptions."
)

install_docs = """# AWSEventBridgePutEvents — Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {"Effect": "Allow", "Action": ["events:PutEvents", "events:ListEventBuses"], "Resource": "*"}

## Auth Setup

| Method             | How                                                                    |
|--------------------|------------------------------------------------------------------------|
| Access keys        | Set aws_access_key_id and aws_secret_access_key in connection          |
| Assume IAM role    | Set assume_iam_role (ARN) in connection — runner assumes it via STS    |
| Default chain      | Omit all auth fields — boto3 uses instance profile / ECS task role etc |
"""

guide_docs = """# AWSEventBridgePutEvents — Operator Guide

## What it does

Sends one or more custom events to an EventBridge event bus via put_events. Synchronous —
returns event IDs and delivery counts immediately. Supports up to 10 entries per call.

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

| Field                  | Required | Description                                                        |
|------------------------|----------|--------------------------------------------------------------------|
| entries                | Yes      | List of event entry dicts (max 10 per call)                        |
| entries[].Source       | Yes      | Event source, e.g. "com.myapp.orders"                              |
| entries[].DetailType   | Yes      | Event type label, e.g. "OrderPlaced"                               |
| entries[].Detail       | Yes      | Event payload — dict (auto-serialized) or JSON string              |
| entries[].EventBusName | No       | Target event bus name or ARN (default: "default")                  |
| entries[].Resources    | No       | List of ARNs of resources involved in the event                    |
| entries[].Time         | No       | ISO8601 timestamp to associate with the event                      |

---

## Output (on success)

    {
      "sent_count": 1,
      "failed_count": 0,
      "entries": [{"event_id": "abc-123", "error_code": "", "error_message": ""}]
    }
"""

description = """
Sends one or more custom events to an AWS EventBridge event bus via put_events. Synchronous —
returns event IDs and delivery counts immediately. Supports up to 10 entries per call. Each
entry requires Source, DetailType, and Detail (dict auto-serialized to JSON). EventBusName
defaults to 'default'. Auth: explicit keys first, then assume_iam_role via STS, then default
credential chain. finish() closes the boto3 client without re-raising exceptions.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "EventBridge",
    "category": "Integration",
    "tags": ["eventbridge", "events", "messaging", "aws"],
    "airflow_equivalent": "EventBridgePutEventsOperator"
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
