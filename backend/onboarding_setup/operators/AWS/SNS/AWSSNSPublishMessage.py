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

codeblock = {"main.py": """
import json
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from src.common.logger.logger import log_info, log_error


def _build_sns_client(connection: dict):
    region = connection.get("region", "us-east-1")
    access_key = connection.get("aws_access_key_id")
    secret_key = connection.get("aws_secret_access_key")
    session_token = connection.get("aws_session_token")
    assume_role_arn = connection.get("assume_iam_role")

    # Case 1: Explicit credentials
    if access_key and secret_key:
        log_info("task", "initialize", "auth_keys",
                 f"Using explicit access key ending ...{access_key[-4:]}")
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token,
            region_name=region,
        )
        return session.client("sns")

    # Case 2: Assume IAM role via STS
    if assume_role_arn:
        log_info("task", "initialize", "auth_assume_role",
                 f"Assuming IAM role: {assume_role_arn}")
        sts = boto3.client("sts", region_name=region)
        assumed = sts.assume_role(RoleArn=assume_role_arn, RoleSessionName="leastaction_session")
        creds = assumed["Credentials"]
        session = boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region,
        )
        return session.client("sns")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info("task", "initialize", "auth_default",
             "Using default AWS credential chain (instance profile / ECS task role / env / config)")
    return boto3.Session(region_name=region).client("sns")


def initialize(least_action_task_object):
    try:
        connection = least_action_task_object.get("connection", {})
        if isinstance(connection, str):
            connection = json.loads(connection)
        region = connection.get("region", "us-east-1")
        log_info("task", "initialize", "building_client", f"region={region}")
        sts = (
            boto3.client("sts", region_name=region,
                         aws_access_key_id=connection.get("aws_access_key_id"),
                         aws_secret_access_key=connection.get("aws_secret_access_key"))
            if connection.get("aws_access_key_id")
            else boto3.client("sts", region_name=region)
        )
        identity = sts.get_caller_identity()
        log_info("task", "initialize", "connectivity_ok",
                 f"Credentials verified. Account: {identity.get('Account')} ARN: {identity.get('Arn')}")
        return _build_sns_client(connection)
    except ClientError as e:
        log_error("task", "initialize", "client_error",
                  f"({e.response.get('Error',{}).get('Code','Unknown')}) {e.response.get('Error',{}).get('Message',str(e))}")
        raise
    except Exception as e:
        log_error("task", "initialize", "init_failed", f"Error: {str(e)}")
        raise


def run(least_action_task_object, client):
    try:
        raw = least_action_task_object.get("payload", "{}")
        payload = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(payload, dict) and "data" in payload and isinstance(payload["data"], dict):
            payload = payload["data"]
            log_info("task", "run", "payload_unwrapped", "Unwrapped unexpected payload data envelope")

        message = payload.get("message")
        topic_arn = payload.get("topic_arn")
        target_arn = payload.get("target_arn")
        phone_number = payload.get("phone_number")

        if not message:
            log_error("task", "run", "validation_failed", "message is required")
            return {"execution_type": "sync", "status": "failed", "result": {"error": "message is required"}}
        if not any([topic_arn, target_arn, phone_number]):
            log_error("task", "run", "validation_failed",
                      "One of topic_arn, target_arn, or phone_number is required")
            return {"execution_type": "sync", "status": "failed",
                    "result": {"error": "One of topic_arn, target_arn, or phone_number is required"}}

        kwargs = {"Message": message}
        if topic_arn:
            kwargs["TopicArn"] = topic_arn
        if target_arn:
            kwargs["TargetArn"] = target_arn
        if phone_number:
            kwargs["PhoneNumber"] = phone_number
        if payload.get("subject"):
            kwargs["Subject"] = payload["subject"]
        if payload.get("message_structure"):
            kwargs["MessageStructure"] = payload["message_structure"]
        if payload.get("message_attributes"):
            kwargs["MessageAttributes"] = payload["message_attributes"]
        if payload.get("message_group_id"):
            kwargs["MessageGroupId"] = payload["message_group_id"]
        if payload.get("message_deduplication_id"):
            kwargs["MessageDeduplicationId"] = payload["message_deduplication_id"]

        destination = topic_arn or target_arn or phone_number
        log_info("task", "run", "publishing_message", f"Publishing to: {destination}")
        response = client.publish(**kwargs)
        message_id = response.get("MessageId", "")
        sequence_number = response.get("SequenceNumber", "")
        log_info("task", "run", "message_published", f"Message published. MessageId: {message_id}")

        result = {"message_id": message_id, "destination": destination}
        if sequence_number:
            result["sequence_number"] = sequence_number
        return {"execution_type": "sync", "status": "success", "result": result}

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "client_error", f"({error_code}) {error_msg}")
        return {"execution_type": "sync", "status": "failed", "result": {"error": f"({error_code}) {error_msg}"}}
    except BotoCoreError as e:
        log_error("task", "run", "botocore_error", f"BotoCoreError: {str(e)}")
        return {"execution_type": "sync", "status": "failed", "result": {"error": str(e)}}
    except Exception as e:
        log_error("task", "run", "unexpected_error", f"Error: {str(e)}")
        return {"execution_type": "sync", "status": "failed", "result": {"error": str(e)}}


def check_completion(least_action_task_object, client, run_details):
    log_info("task", "check_completion", "sync_complete", "SNS Publish is synchronous - already complete")
    return {"status": run_details.get("status", "success"),
            "message": "Synchronous SNS publish completed",
            "output": run_details.get("result", {})}


def finish(least_action_task_object, client, completion_details, run_details):
    try:
        status = completion_details.get("status", "unknown")
        log_info("task", "finish", "final_status", f"Task completed with status: {status}")
        if status == "success":
            output = completion_details.get("output", {})
            log_info("task", "finish", "summary",
                     f"Message published to {output.get('destination')} MessageId: {output.get('message_id')}")
        else:
            log_error("task", "finish", "operation_failed", completion_details.get("message", "No message"))
        if client:
            try:
                client.close()
                log_info("task", "finish", "client_closed", "boto3 client closed successfully")
            except Exception as close_error:
                log_error("task", "finish", "client_close_error", f"Error closing client: {str(close_error)}")
        log_info("task", "finish", "cleanup_complete", "Cleanup complete")
    except Exception as e:
        log_error("task", "finish", "cleanup_error", f"Error: {str(e)}")
"""}

bashblock = {"main.sh": """#!/bin/bash
set -e
pip install boto3>=1.28.0
pip install botocore>=1.31.0
echo "Dependencies installed successfully"
"""}

connection = {
    "region": "us-east-1",
    }

# Use topic_arn for topic publish, phone_number for SMS, target_arn for mobile push
payload = {
    "topic_arn": "arn:aws:sns:us-east-1:123456789012:my-topic",
    "message": "Pipeline completed successfully.",
    "subject": "Pipeline Notification",
}

prompt = (
    "Publishes a message via AWS SNS. Supports all delivery modes: "
    "topic publish (topic_arn), SMS direct (phone_number), mobile push (target_arn). "
    "Optional: subject (email only), message_structure ('json' for per-protocol messages), "
    "message_attributes (dict for filtering), message_group_id (FIFO topics), "
    "message_deduplication_id (FIFO topics). Synchronous — returns message_id immediately."
)

install_docs = """## Dependencies
- boto3>=1.28.0
- botocore>=1.31.0

## IAM Permissions Required
- sns:Publish on the target topic/endpoint ARN
- sts:GetCallerIdentity

## Auth Setup
Use IAM instance profile (recommended) or provide aws_access_key_id and aws_secret_access_key
in the connection.
"""

guide_docs = """## Payload Fields
| Field                     | Required    | Description                                              |
|---------------------------|-------------|----------------------------------------------------------|
| topic_arn                 | one of 3    | ARN of the SNS topic                                     |
| target_arn                | one of 3    | ARN of a specific endpoint (mobile push)                 |
| phone_number              | one of 3    | E.164 phone number for SMS (+12025551234)                |
| message                   | yes         | Message body (string, or JSON string if structure=json)  |
| subject                   | no          | Subject line (email subscribers only)                    |
| message_structure         | no          | 'json' to send different message per protocol            |
| message_attributes        | no          | Dict of {Name: {DataType, StringValue}} for filtering    |
| message_group_id          | no          | Required for FIFO topics                                 |
| message_deduplication_id  | no          | For FIFO topics (omit to use content-based dedup)        |

## Examples

### Standard topic (email/SQS/Lambda subscribers)
{"topic_arn": "arn:aws:sns:...", "message": "Done", "subject": "Alert"}

### SMS direct
{"phone_number": "+12025551234", "message": "Pipeline failed — check logs"}

### FIFO topic
{"topic_arn": "arn:aws:sns:...:my-topic.fifo", "message": "event", "message_group_id": "group1"}

### Per-protocol (different message per channel)
{
  "topic_arn": "arn:aws:sns:...",
  "message_structure": "json",
  "message": "{\"default\": \"Default\", \"email\": \"Full email body\", \"sqs\": \"{\\\"key\\\": \\\"val\\\"}\"}"
}

### With message attributes (for subscription filtering)
{
  "topic_arn": "arn:aws:sns:...",
  "message": "event",
  "message_attributes": {
    "environment": {"DataType": "String", "StringValue": "production"},
    "priority": {"DataType": "Number", "StringValue": "1"}
  }
}

## Output
{"message_id": "abc123-...", "destination": "arn:aws:sns:..."}

## Notes
- Synchronous — completes in <1 second, no polling
- Subscribers must confirm their subscription before receiving messages
- FIFO topics require message_group_id and have exactly-once delivery
"""

description = (
    "Publishes a message via AWS SNS to a topic, phone number, or device endpoint. "
    "Supports standard topics, FIFO topics, SMS, mobile push, per-protocol messages, "
    "and message attributes for subscription filtering. Synchronous."
)

publisher = "LeastActionLabs"

metadata = {
    "service": "SNS",
    "category": "Messaging",
    "tags": ["sns", "publish", "notification", "messaging", "fifo", "sms", "aws"],
    "airflow_equivalent": "SnsPublishOperator",
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

SNS publish is synchronous and completes in under 1 second. Provide exactly one of topic_arn, target_arn, or phone_number. For FIFO topics (ARN ending in .fifo), message_group_id is required. message_structure='json' enables per-protocol messages where the message field must be a JSON string with protocol keys (default, email, sqs, etc.). Phone numbers must be in E.164 format (+12025551234). Subscribers must confirm their subscription before they receive messages.
"""
