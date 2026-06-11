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
AWS CloudFormation Delete Stack Operator

Deletes a CloudFormation stack and all its resources. Async.
Auth priority: explicit keys → assume IAM role → default credential chain.
"""

import json

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from src.common.logger.logger import log_error, log_info


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_cloudformation_client(connection: dict):
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
        return session.client("cloudformation")

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
        return session.client("cloudformation")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info(
        "task", "initialize", "auth_default",
        "Using default AWS credential chain (instance profile / ECS task role / env / config)"
    )
    return boto3.Session(region_name=region).client("cloudformation")


# ---------------------------------------------------------------------------
# Operator methods
# ---------------------------------------------------------------------------

def initialize(least_action_task_object):
    """
    Build and verify the CloudFormation boto3 client.

    Returns:
        boto3 cloudformation client
    """
    try:
        connection = least_action_task_object.get("connection", {})
        task_laui = least_action_task_object.get("laui")

        log_info(
            "task", "initialize", "start",
            f"Initializing CloudFormation delete stack operator for task: {task_laui}"
        )

        cf_client = _build_cloudformation_client(connection)

        region = connection.get("region", "us-east-1")
        log_info(
            "task", "initialize", "verify_connection",
            f"Verifying CloudFormation connectivity in region: {region}"
        )
        cf_client.list_stacks(StackStatusFilter=["CREATE_COMPLETE"])

        log_info(
            "task", "initialize", "connection_established",
            f"CloudFormation client ready for region: {region}"
        )
        return cf_client

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
    Delete a CloudFormation stack using delete_stack.

    Payload fields:
        stack_name        (str, required)    -- name or ARN of the stack to delete
        retain_resources  (list, optional)   -- list of logical resource IDs to skip deletion
                                               (e.g. ["MyS3Bucket"] to preserve the bucket)
        role_arn          (str, optional)    -- IAM role ARN for CloudFormation to assume during deletion

    Returns:
        dict with status="pending", execution_type="async", result
    """
    try:
        task_laui = least_action_task_object.get("laui")
        payload = least_action_task_object.get("payload", {})

        log_info(
            "task", "run", "extracting_payload",
            f"Extracting delete stack configuration for task: {task_laui}"
        )

        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                log_error("task", "run", "payload_parse_error", "Failed to parse payload as JSON")
                return {"status": "failed", "execution_type": "async", "result": None,
                        "error": "Invalid payload format — expected flat JSON object"}

        stack_name = payload.get("stack_name")
        if not stack_name:
            log_error("task", "run", "missing_stack_name", "stack_name is required in payload")
            return {"status": "failed", "execution_type": "async", "result": None,
                    "error": "stack_name is required in payload"}

        kwargs = {"StackName": stack_name}

        retain_resources = payload.get("retain_resources")
        if retain_resources:
            kwargs["RetainResources"] = retain_resources
            log_info("task", "run", "retain_resources",
                     f"Retaining {len(retain_resources)} resource(s): {retain_resources}")

        if payload.get("role_arn"):
            kwargs["RoleARN"] = payload["role_arn"]
            log_info("task", "run", "role_arn", f"CloudFormation role: {payload['role_arn']}")

        log_info(
            "task", "run", "deleting_stack",
            f"Initiating deletion of CloudFormation stack: {stack_name}"
        )

        client.delete_stack(**kwargs)

        log_info(
            "task", "run", "delete_initiated",
            f"Stack {stack_name} deletion initiated — polling for DELETE_COMPLETE"
        )

        return {
            "status": "pending",
            "execution_type": "async",
            "result": {
                "stack_name": stack_name,
                "retain_resources": retain_resources or [],
            },
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "client_error", f"AWS ClientError ({error_code}): {error_msg}")
        return {"status": "failed", "execution_type": "async", "result": None,
                "error": f"{error_code}: {error_msg}"}
    except Exception as e:
        log_error("task", "run", "unexpected_error", f"Unexpected error during run: {str(e)}")
        return {"status": "failed", "execution_type": "async", "result": None, "error": str(e)}


def check_completion(least_action_task_object, client, run_details):
    """
    Poll describe_stacks to determine whether the stack has been deleted.

    A stack that no longer appears in describe_stacks (ValidationError: does not exist)
    is considered successfully deleted.

    Returns:
        dict with status (success | pending | failed), message, output
    """
    try:
        if run_details.get("status") == "failed":
            log_error("task", "check_completion", "run_phase_failed",
                      f"Run phase reported failure: {run_details.get('error')}")
            return {"status": "failed",
                    "message": f"Stack deletion failed in run phase: {run_details.get('error')}",
                    "output": None}

        result = run_details.get("result", {})
        stack_name = result.get("stack_name")
        if not stack_name:
            return {"status": "failed", "message": "No stack_name in run_details", "output": None}

        log_info(
            "task", "check_completion", "polling_stack_status",
            f"Polling describe_stacks for: {stack_name}"
        )

        try:
            response = client.describe_stacks(StackName=stack_name)
            stacks = response.get("Stacks", [])

            if not stacks:
                log_info("task", "check_completion", "stack_deleted",
                         f"Stack {stack_name} no longer exists — deletion complete")
                return {
                    "status": "success",
                    "message": f"Stack {stack_name} deleted successfully",
                    "output": {"stack_name": stack_name, "stack_status": "DELETE_COMPLETE"},
                }

            stack = stacks[0]
            stack_status = stack.get("StackStatus", "Unknown")
            status_reason = stack.get("StackStatusReason", "")

            log_info(
                "task", "check_completion", "stack_status",
                f"Stack {stack_name}: status={stack_status}"
            )

            if stack_status == "DELETE_COMPLETE":
                log_info("task", "check_completion", "stack_deleted",
                         f"Stack {stack_name} deleted successfully")
                return {
                    "status": "success",
                    "message": f"Stack {stack_name} deleted successfully",
                    "output": {"stack_name": stack_name, "stack_status": stack_status},
                }

            if "FAILED" in stack_status:
                log_error("task", "check_completion", "stack_delete_failed",
                          f"Stack deletion failed: {stack_status} — {status_reason}")
                return {
                    "status": "failed",
                    "message": f"Stack deletion failed: {stack_status} — {status_reason}",
                    "output": {"stack_name": stack_name, "stack_status": stack_status,
                               "status_reason": status_reason},
                }

            log_info("task", "check_completion", "stack_still_deleting",
                     f"Stack {stack_name} still deleting — current status: {stack_status}")
            return {
                "status": "pending",
                "message": f"Stack status: {stack_status}",
                "output": {"stack_name": stack_name, "stack_status": stack_status},
            }

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            # Stack no longer exists — deletion complete
            if error_code == "ValidationError" and "does not exist" in error_msg:
                log_info("task", "check_completion", "stack_deleted",
                         f"Stack {stack_name} no longer visible in describe — deletion complete")
                return {
                    "status": "success",
                    "message": f"Stack {stack_name} deleted successfully",
                    "output": {"stack_name": stack_name, "stack_status": "DELETE_COMPLETE"},
                }
            raise

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
                log_info("task", "finish", "client_closed",
                         "CloudFormation boto3 client closed successfully")
            except Exception as close_error:
                log_error("task", "finish", "client_close_error",
                          f"Error closing CloudFormation client: {str(close_error)}")

        if final_status == "success":
            output = completion_details.get("output", {})
            log_info(
                "task", "finish", "operation_summary",
                f"Stack {output.get('stack_name')} deleted — status={output.get('stack_status')}"
            )
        elif final_status == "failed":
            log_error("task", "finish", "operation_failed",
                      f"Stack deletion failed: {completion_details.get('message')}")
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
    "stack_name": "my-stack",                # required
    # "retain_resources": ["MyS3Bucket"],    # optional — logical resource IDs to skip deletion
    # "role_arn": "arn:aws:iam::123456789012:role/CFNRole"  # optional — role CloudFormation assumes
}

prompt = (
    "Delete a CloudFormation stack and all its resources. Payload: stack_name (required). "
    "Optional: retain_resources (list of logical resource IDs to preserve), role_arn. "
    "Async — polls until DELETE_COMPLETE or stack no longer exists. "
    "Auth: explicit keys first, then assume_iam_role via STS, then default credential chain. "
    "finish() must close the boto3 client without re-raising exceptions."
)

install_docs = """# AWSCloudFormationDeleteStack — Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:DeleteStack",
        "cloudformation:DescribeStacks",
        "cloudformation:ListStacks"
      ],
      "Resource": "*"
    }

    Plus permissions to delete every resource type in the stack
    (e.g. s3:DeleteBucket, ec2:TerminateInstances, iam:DeleteRole).

## Auth Setup

| Method             | How                                                                    |
|--------------------|------------------------------------------------------------------------|
| Access keys        | Set aws_access_key_id and aws_secret_access_key in connection          |
| Assume IAM role    | Set assume_iam_role (ARN) in connection — runner assumes it via STS    |
| Default chain      | Omit all auth fields — boto3 uses instance profile / ECS task role etc |
"""

guide_docs = """# AWSCloudFormationDeleteStack — Operator Guide

## What it does

Deletes a CloudFormation stack and all of its managed resources. Async — returns immediately
after `delete_stack` and polls `describe_stacks` until the stack reaches `DELETE_COMPLETE` or
disappears from the API. Stacks that no longer appear in `describe_stacks` are treated as
successfully deleted.

---

## Auth

Three methods are supported, evaluated in this priority order:

1. **Access keys** — if `aws_access_key_id` + `aws_secret_access_key` are present in the connection.
2. **Assume IAM role** — if `assume_iam_role` (role ARN) is present and access keys are absent.
3. **Default credential chain** — EC2 instance profile, ECS task role, env vars, `~/.aws/credentials`.

---

## Connection

**Scenario 1 — Access keys:**

    {"region": "us-east-1", "aws_access_key_id": "AKIA...", "aws_secret_access_key": "..."}

**Scenario 2 — Assume IAM role:**

    {"region": "us-east-1", "assume_iam_role": "arn:aws:iam::123456789012:role/MyRole"}

**Scenario 3 — Default credential chain:**

    {"region": "us-east-1"}

---

## Payload

| Field            | Required | Description                                                              |
|------------------|----------|--------------------------------------------------------------------------|
| stack_name       | Yes      | Stack name or ARN to delete                                              |
| retain_resources | No       | List of logical resource IDs to skip during deletion (they are detached from the stack but not deleted) |
| role_arn         | No       | IAM role CloudFormation assumes to delete resources                      |

---

## Output (on success)

    {
      "stack_name":   "my-stack",
      "stack_status": "DELETE_COMPLETE"
    }

---

## Scenarios and Edge Cases

**Stack does not exist:**
  `delete_stack` on a non-existent stack name succeeds silently — no error is returned.
  `check_completion` confirms via `describe_stacks` returning nothing or a ValidationError.

**S3 buckets with objects:**
  CloudFormation cannot delete non-empty S3 buckets. The stack enters `DELETE_FAILED`.
  Use `retain_resources` to skip the bucket, or empty it first before deleting the stack.

**Resources with deletion policy Retain:**
  Resources with `DeletionPolicy: Retain` in the template are not deleted — this is
  separate from `retain_resources` (which is a runtime override).

**Stacks with termination protection:**
  Stacks with termination protection enabled return `TerminationProtection` error.
  Disable termination protection first via the CloudFormation console or UpdateTerminationProtection API.

**DELETE_FAILED state:**
  If deletion fails, the stack enters `DELETE_FAILED`. Individual resource deletion errors
  are visible in the stack events. Retry after fixing the blocking resource (e.g. empty the
  S3 bucket, release the ENI). Use `retain_resources` to skip permanently blocking resources.

---

## What this operator does NOT do

- Does not disable termination protection before deleting
- Does not empty S3 buckets before deletion — must be done separately
- Does not delete retained resources — they are detached from the stack but preserved
"""

description = """
Deletes a CloudFormation stack and all its managed resources. Async — polls describe_stacks
until DELETE_COMPLETE or the stack is no longer visible. Supports retain_resources to
preserve specific resources during deletion (e.g. non-empty S3 buckets). Stacks no longer
visible in describe_stacks are treated as successfully deleted.
Auth: explicit keys first, then assume_iam_role via STS, then default credential chain.
finish() closes the boto3 client without re-raising exceptions.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "CloudFormation",
    "category": "Infrastructure",
    "tags": ["cloudformation", "iac", "infrastructure", "delete", "aws"],
    "airflow_equivalent": "CloudFormationDeleteStackOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

**S3 bucket deletion blocker**: The most common cause of `DELETE_FAILED` is a non-empty S3
bucket — CloudFormation cannot delete buckets that contain objects. Options: (1) add a
Lambda-backed custom resource in your template to empty the bucket on delete, (2) empty the
bucket manually before running this operator, or (3) use `retain_resources: ["MyBucketLogicalId"]`
to skip the bucket and clean it up separately.

**retain_resources vs DeletionPolicy**: `retain_resources` is a runtime override for this
delete call only — it takes logical resource IDs (not physical resource names). Resources
with `DeletionPolicy: Retain` in the template are always retained regardless of this field.
Both mechanisms result in the resource being detached from the stack but not deleted.

**Termination protection**: Stacks with termination protection enabled will fail deletion
with a `TerminationProtection` error. This operator does not disable protection automatically
— disable it via the console or API before calling this operator.

**Idempotency**: `delete_stack` on a stack name that doesn't exist returns success silently.
This means re-running after a successful deletion is safe.

**Permission model**: The calling identity needs delete permissions for every resource type
in the stack. Use `role_arn` to delegate to a dedicated CloudFormation execution role with
the necessary permissions — cleaner than granting broad delete permissions to the runner.
"""
