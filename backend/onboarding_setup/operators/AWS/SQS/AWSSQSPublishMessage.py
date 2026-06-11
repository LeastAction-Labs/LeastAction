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
AWS SQS Publish Message Operator

Sends a message to an SQS queue (standard or FIFO). Synchronous.
Auth priority: explicit keys → assume IAM role → default credential chain.
"""

import json

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from src.common.logger.logger import log_error, log_info


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_sqs_client(connection: dict):
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
        return session.client("sqs")

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
        return session.client("sqs")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info(
        "task", "initialize", "auth_default",
        "Using default AWS credential chain (instance profile / ECS task role / env / config)"
    )
    return boto3.Session(region_name=region).client("sqs")


# ---------------------------------------------------------------------------
# Operator methods
# ---------------------------------------------------------------------------

def initialize(least_action_task_object):
    """
    Build and verify the SQS boto3 client.

    Returns:
        boto3 SQS client
    """
    try:
        connection = least_action_task_object.get("connection", {})
        task_laui = least_action_task_object.get("laui")

        log_info(
            "task", "initialize", "start",
            f"Initializing SQS publish message operator for task: {task_laui}"
        )

        sqs_client = _build_sqs_client(connection)

        region = connection.get("region", "us-east-1")
        log_info(
            "task", "initialize", "verify_connection",
            f"Verifying SQS connectivity in region: {region}"
        )
        sqs_client.list_queues(MaxResults=1)

        log_info(
            "task", "initialize", "connection_established",
            f"SQS client ready for region: {region}"
        )
        return sqs_client

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
    Send a message to an SQS queue using send_message.

    Payload fields:
        queue_url                 (str, required)   -- full SQS queue URL
        message_body              (str|dict, required) -- message content; dict is auto-serialized to JSON
        delay_seconds             (int, optional)   -- delivery delay in seconds 0-900 (default: 0)
        message_attributes        (dict, optional)  -- SQS message attributes for consumer-side filtering
                                                       format: {"attr_name": {"DataType": "String", "StringValue": "val"}}
        message_group_id          (str, optional)   -- required for FIFO queues (URL ends in .fifo)
        message_deduplication_id  (str, optional)   -- for FIFO queues with ContentBasedDeduplication disabled

    Returns:
        dict with status="success", execution_type="sync", result
    """
    try:
        task_laui = least_action_task_object.get("laui")
        payload = least_action_task_object.get("payload", {})

        log_info(
            "task", "run", "extracting_payload",
            f"Extracting SQS send message configuration for task: {task_laui}"
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

        queue_url = payload.get("queue_url")
        message_body = payload.get("message_body")

        if not queue_url:
            log_error("task", "run", "missing_queue_url", "queue_url is required in payload")
            return {"status": "failed", "execution_type": "sync", "result": None,
                    "error": "queue_url is required in payload"}
        if message_body is None:
            log_error("task", "run", "missing_message_body", "message_body is required in payload")
            return {"status": "failed", "execution_type": "sync", "result": None,
                    "error": "message_body is required in payload"}

        delay_seconds = int(payload.get("delay_seconds", 0))
        message_attributes = payload.get("message_attributes")
        message_group_id = payload.get("message_group_id")
        message_deduplication_id = payload.get("message_deduplication_id")

        body = json.dumps(message_body) if isinstance(message_body, dict) else message_body

        is_fifo = queue_url.endswith(".fifo")
        if is_fifo and not message_group_id:
            log_error("task", "run", "missing_message_group_id",
                      "message_group_id is required for FIFO queues (queue URL ends in .fifo)")
            return {"status": "failed", "execution_type": "sync", "result": None,
                    "error": "message_group_id is required for FIFO queues"}

        kwargs = {
            "QueueUrl": queue_url,
            "MessageBody": body,
            "DelaySeconds": delay_seconds,
        }
        if message_attributes:
            kwargs["MessageAttributes"] = message_attributes
            log_info("task", "run", "message_attributes",
                     f"Message attributes: {list(message_attributes.keys())}")
        if message_group_id:
            kwargs["MessageGroupId"] = message_group_id
            log_info("task", "run", "fifo_group", f"FIFO message group: {message_group_id}")
        if message_deduplication_id:
            kwargs["MessageDeduplicationId"] = message_deduplication_id
            log_info("task", "run", "dedup_id", f"Deduplication ID: {message_deduplication_id}")

        queue_type = "FIFO" if is_fifo else "standard"
        log_info(
            "task", "run", "sending_message",
            f"Sending message to {queue_type} queue | delay={delay_seconds}s | "
            f"body_type={'dict (JSON-serialized)' if isinstance(message_body, dict) else 'string'}"
        )

        response = client.send_message(**kwargs)
        message_id = response["MessageId"]
        md5_of_body = response["MD5OfMessageBody"]
        sequence_number = response.get("SequenceNumber", "")

        log_info(
            "task", "run", "message_sent",
            f"Message sent successfully — message_id={message_id} | md5={md5_of_body}"
        )

        return {
            "status": "success",
            "execution_type": "sync",
            "result": {
                "message_id": message_id,
                "md5_of_body": md5_of_body,
                "sequence_number": sequence_number,
                "queue_url": queue_url,
            },
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "client_error", f"AWS ClientError ({error_code}): {error_msg}")
        return {"status": "failed", "execution_type": "sync", "result": None,
                "error": f"{error_code}: {error_msg}"}
    except Exception as e:
        log_error("task", "run", "unexpected_error", f"Unexpected error during run: {str(e)}")
        return {"status": "failed", "execution_type": "sync", "result": None, "error": str(e)}


def check_completion(least_action_task_object, client, run_details):
    """
    send_message is synchronous — pass through run_details directly.

    Returns:
        dict with status, message, output
    """
    if run_details.get("status") == "failed":
        log_error("task", "check_completion", "run_phase_failed",
                  f"Run phase reported failure: {run_details.get('error')}")
        return {
            "status": "failed",
            "message": f"SendMessage failed: {run_details.get('error')}",
            "output": None,
        }

    result = run_details.get("result", {})
    log_info(
        "task", "check_completion", "sync_complete",
        f"SendMessage completed — message_id={result.get('message_id')}"
    )
    return {
        "status": "success",
        "message": f"Message delivered to SQS — message_id={result.get('message_id')}",
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
                         "SQS boto3 client connection closed successfully")
            except Exception as close_error:
                log_error("task", "finish", "client_close_error",
                          f"Error closing SQS client: {str(close_error)}")

        if final_status == "success":
            output = completion_details.get("output", {})
            log_info("task", "finish", "operation_summary",
                     f"Message sent successfully — message_id={output.get('message_id')}, "
                     f"queue={output.get('queue_url')}")
        elif final_status == "failed":
            log_error("task", "finish", "operation_failed",
                      f"SendMessage failed: {completion_details.get('message')}")
        else:
            log_info("task", "finish", "operation_status",
                     f"status={final_status}, message={completion_details.get('message')}")

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
    "queue_url": "https://sqs.us-east-1.amazonaws.com/123456789012/my-queue",  # required
    "message_body": "Pipeline stage completed successfully.",                    # required — dict auto-serialized to JSON
    # "delay_seconds": 0,                     # optional — delivery delay 0-900 seconds (default: 0)
    # "message_attributes": {                 # optional — metadata for consumer-side filtering
    #     "environment": {"DataType": "String", "StringValue": "production"}
    # },
    # "message_group_id": "group-1",          # optional — required for FIFO queues (.fifo suffix)
    # "message_deduplication_id": "run-001"   # optional — for FIFO queues without ContentBasedDeduplication
}

prompt = (
    "Send a message to an AWS SQS queue. Payload: queue_url (required), message_body (required, "
    "dict is auto-serialized to JSON). Optional: delay_seconds (0-900), message_attributes, "
    "message_group_id (required for FIFO queues), message_deduplication_id (FIFO without ContentBasedDeduplication). "
    "Synchronous — returns message_id immediately. "
    "Auth: explicit keys first, then assume_iam_role via STS, then default credential chain. "
    "finish() must close the boto3 client without re-raising exceptions."
)

install_docs = """# AWSSQSPublishMessage — Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": ["sqs:SendMessage", "sqs:ListQueues"],
      "Resource": "*"
    }

## Auth Setup

| Method             | How                                                                    |
|--------------------|------------------------------------------------------------------------|
| Access keys        | Set aws_access_key_id and aws_secret_access_key in connection          |
| Assume IAM role    | Set assume_iam_role (ARN) in connection — runner assumes it via STS    |
| Default chain      | Omit all auth fields — boto3 uses instance profile / ECS task role etc |
"""

guide_docs = """# AWSSQSPublishMessage — Operator Guide

## What it does

Sends a single message to an AWS SQS queue via send_message. Synchronous — returns the
message_id immediately. Supports both standard and FIFO queues, optional delivery delay,
message attributes for consumer-side filtering, and dict body auto-serialization to JSON.

This operator is useful for decoupling pipeline stages, triggering downstream consumers,
broadcasting events, or any pattern that requires durable async message delivery.

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
| region                | Yes        | AWS region where the SQS queue exists                    |
| aws_access_key_id     | Scenario 1 | IAM user access key                                      |
| aws_secret_access_key | Scenario 1 | IAM user secret key                                      |
| aws_session_token     | No         | Temporary session token for STS-issued credentials       |
| assume_iam_role       | Scenario 2 | Role ARN to assume via STS                               |

---

## Payload

| Field                   | Required | Description                                                                    |
|-------------------------|----------|--------------------------------------------------------------------------------|
| queue_url               | Yes      | Full SQS queue URL (from console or create_queue output)                       |
| message_body            | Yes      | Message content — string or dict (dict auto-serialized to JSON)                |
| delay_seconds           | No       | Delivery delay 0-900 seconds (default: 0). Standard queues only.               |
| message_attributes      | No       | Metadata dict for consumer-side filtering. Format: {"name": {"DataType": "String", "StringValue": "val"}} |
| message_group_id        | No*      | Required for FIFO queues (URL ends in `.fifo`). Groups related messages.       |
| message_deduplication_id| No       | For FIFO queues with ContentBasedDeduplication disabled. Prevents duplicates.  |

*`message_group_id` is required when queue_url ends in `.fifo`. The operator validates this and returns a clear error if missing.

---

## Output (on success)

    {
      "message_id":    "abc-123-def-456",
      "md5_of_body":   "d41d8cd98f00b204e9800998ecf8427e",
      "sequence_number": "12345678901234567890",
      "queue_url":     "https://sqs.us-east-1.amazonaws.com/123456789012/my-queue"
    }

| Field           | Description                                                                 |
|-----------------|-----------------------------------------------------------------------------|
| message_id      | SQS-assigned unique message ID                                              |
| md5_of_body     | MD5 of the raw message body — use to verify delivery integrity              |
| sequence_number | FIFO queues only — ordering sequence within the message group               |
| queue_url       | The queue the message was sent to                                           |

---

## Scenarios and Edge Cases

**Standard queue — simple string message:**

    {"queue_url": "https://sqs.us-east-1.amazonaws.com/123456789/my-queue", "message_body": "job done"}

**Standard queue — dict body (auto-serialized):**

    {"queue_url": "...", "message_body": {"job_id": "abc123", "status": "complete", "records": 1500}}

**FIFO queue — message_group_id required:**

    {"queue_url": "...my-queue.fifo", "message_body": "event", "message_group_id": "pipeline-1"}

**With message attributes for Lambda filtering:**

    {
      "queue_url": "...",
      "message_body": "event",
      "message_attributes": {
        "environment": {"DataType": "String", "StringValue": "production"},
        "priority": {"DataType": "Number", "StringValue": "1"}
      }
    }

**FIFO with explicit deduplication (ContentBasedDeduplication disabled):**

    {
      "queue_url": "...my-queue.fifo",
      "message_body": "retry-event",
      "message_group_id": "group-1",
      "message_deduplication_id": "unique-run-id-001"
    }

**Queue does not exist:**
  AWS returns NonExistentQueue ClientError. Caught and returned as status:failed.

**Message body exceeds 256 KB:**
  AWS returns InvalidMessageContents. Use S3 pointer pattern for large payloads.

**delay_seconds on a FIFO queue:**
  FIFO queues ignore per-message delay — the parameter is silently accepted but has no effect.

---

## What this operator does NOT do

- Does not create the queue — the queue must already exist
- Does not send batch messages — one message per run (use SQS batch API for bulk sends)
- Does not read or consume messages — use SQS receive_message for that
- Does not verify the message was consumed by a subscriber
"""

description = """
Sends a message to an AWS SQS queue via send_message. Synchronous — returns message_id
immediately. Supports standard and FIFO queues. Dict message_body is auto-serialized to JSON.
For FIFO queues, message_group_id is required and validated before the API call. Supports
delivery delay (0-900s, standard queues only), message attributes for consumer filtering,
and deduplication ID for FIFO queues without ContentBasedDeduplication.
Auth: explicit keys first, then assume_iam_role via STS, then default credential chain.
finish() closes the boto3 client without re-raising exceptions.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "SQS",
    "category": "Messaging",
    "tags": ["sqs", "queue", "messaging", "aws"],
    "airflow_equivalent": "SQSSendMessageOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

**FIFO queue validation**: This operator validates that `message_group_id` is present when
the `queue_url` ends in `.fifo` — it returns a clear error before calling the API rather than
letting SQS return a cryptic MissingParameter error. `message_deduplication_id` is only needed
when ContentBasedDeduplication is disabled on the queue; if enabled, SQS computes it automatically
from the body hash.

**Standard queue guarantees**: Standard queues offer at-least-once delivery and best-effort
ordering — messages may arrive out of order or more than once. Design consumers to be idempotent.
FIFO queues guarantee exactly-once processing and strict ordering within a message group.

**Message size limit**: SQS enforces a hard 256 KB limit per message including all attributes.
For larger payloads, use the S3 pointer pattern — store data in S3 and send an SQS message
containing only the S3 key. The AWS SQS Extended Client library automates this pattern.

**MD5 verification**: The `md5_of_body` in the output is the MD5 of the raw body string as
received by SQS. You can verify this against your local computation to confirm the message was
not corrupted in transit — useful for high-integrity pipelines.

**delay_seconds scope**: Per-message `delay_seconds` overrides the queue-level default delay
for that specific message, but only on standard queues. FIFO queues do not support per-message
delay — the parameter is accepted without error but has no effect.
"""
