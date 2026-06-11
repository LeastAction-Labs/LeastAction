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
AWS CloudFormation Create Stack Operator

Creates a CloudFormation stack from a template and polls until CREATE_COMPLETE. Async.
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
            f"Initializing CloudFormation create stack operator for task: {task_laui}"
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
    Create a CloudFormation stack using create_stack.

    Payload fields:
        stack_name           (str, required)   -- unique stack name
        template_body        (str|dict, required*) -- inline template as JSON/YAML string or dict (auto-serialized)
        template_url         (str, required*)  -- S3 URL of template (alternative to template_body)
        parameters           (list, optional)  -- list of {"ParameterKey": str, "ParameterValue": str}
        capabilities         (list, optional)  -- ["CAPABILITY_IAM"] / ["CAPABILITY_NAMED_IAM"] / ["CAPABILITY_AUTO_EXPAND"]
        on_failure           (str, optional)   -- DO_NOTHING | ROLLBACK | DELETE (default: ROLLBACK)
        timeout_in_minutes   (int, optional)   -- stack creation timeout; triggers on_failure if exceeded
        tags                 (list, optional)  -- list of {"Key": str, "Value": str}
        notification_arns    (list, optional)  -- SNS topic ARNs for stack event notifications
        role_arn             (str, optional)   -- IAM role ARN for CloudFormation to assume during creation

    *Provide either template_body OR template_url, not both.

    Returns:
        dict with status="pending", execution_type="async", result
    """
    try:
        task_laui = least_action_task_object.get("laui")
        payload = least_action_task_object.get("payload", {})

        log_info(
            "task", "run", "extracting_payload",
            f"Extracting create stack configuration for task: {task_laui}"
        )

        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                log_error("task", "run", "payload_parse_error", "Failed to parse payload as JSON")
                return {"status": "failed", "execution_type": "async", "result": None,
                        "error": "Invalid payload format — expected flat JSON object"}

        stack_name = payload.get("stack_name")
        template_body = payload.get("template_body")
        template_url = payload.get("template_url")

        if not stack_name:
            log_error("task", "run", "missing_stack_name", "stack_name is required in payload")
            return {"status": "failed", "execution_type": "async", "result": None,
                    "error": "stack_name is required in payload"}

        if not template_body and not template_url:
            log_error("task", "run", "missing_template",
                      "Either template_body or template_url is required in payload")
            return {"status": "failed", "execution_type": "async", "result": None,
                    "error": "Either template_body or template_url is required in payload"}

        kwargs = {
            "StackName": stack_name,
            "OnFailure": payload.get("on_failure", "ROLLBACK"),
        }

        if template_body:
            kwargs["TemplateBody"] = (
                json.dumps(template_body) if isinstance(template_body, dict) else template_body
            )
            log_info("task", "run", "template_source", "Using inline template_body")
        elif template_url:
            kwargs["TemplateURL"] = template_url
            log_info("task", "run", "template_source", f"Using template from S3: {template_url}")

        if payload.get("parameters"):
            kwargs["Parameters"] = payload["parameters"]
            log_info("task", "run", "parameters",
                     f"Stack parameters: {len(payload['parameters'])} parameter(s)")

        if payload.get("capabilities"):
            kwargs["Capabilities"] = payload["capabilities"]
            log_info("task", "run", "capabilities", f"Capabilities: {payload['capabilities']}")

        if payload.get("tags"):
            kwargs["Tags"] = payload["tags"]
            log_info("task", "run", "tags", f"Tags: {len(payload['tags'])} tag(s)")

        if payload.get("timeout_in_minutes"):
            kwargs["TimeoutInMinutes"] = int(payload["timeout_in_minutes"])
            log_info("task", "run", "timeout", f"Timeout: {payload['timeout_in_minutes']} minutes")

        if payload.get("notification_arns"):
            kwargs["NotificationARNs"] = payload["notification_arns"]

        if payload.get("role_arn"):
            kwargs["RoleARN"] = payload["role_arn"]
            log_info("task", "run", "role_arn", f"CloudFormation role: {payload['role_arn']}")

        log_info(
            "task", "run", "creating_stack",
            f"Creating CloudFormation stack: {stack_name} | on_failure={kwargs['OnFailure']}"
        )

        response = client.create_stack(**kwargs)
        stack_id = response.get("StackId", "")

        log_info(
            "task", "run", "stack_creation_initiated",
            f"Stack {stack_name} creation initiated — Stack ID: {stack_id}"
        )

        return {
            "status": "pending",
            "execution_type": "async",
            "result": {
                "stack_name": stack_name,
                "stack_id": stack_id,
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
    Poll describe_stacks to determine whether the stack reached CREATE_COMPLETE.

    Returns:
        dict with status (success | pending | failed), message, output
    """
    try:
        if run_details.get("status") == "failed":
            log_error("task", "check_completion", "run_phase_failed",
                      f"Run phase reported failure: {run_details.get('error')}")
            return {"status": "failed",
                    "message": f"Stack creation failed in run phase: {run_details.get('error')}",
                    "output": None}

        result = run_details.get("result", {})
        stack_name = result.get("stack_name")
        if not stack_name:
            return {"status": "failed", "message": "No stack_name in run_details", "output": None}

        log_info(
            "task", "check_completion", "polling_stack_status",
            f"Polling describe_stacks for: {stack_name}"
        )

        response = client.describe_stacks(StackName=stack_name)
        stacks = response.get("Stacks", [])

        if not stacks:
            return {"status": "failed", "message": f"Stack {stack_name} not found", "output": None}

        stack = stacks[0]
        stack_status = stack.get("StackStatus", "Unknown")
        status_reason = stack.get("StackStatusReason", "")

        log_info(
            "task", "check_completion", "stack_status",
            f"Stack {stack_name}: status={stack_status}"
        )

        if stack_status == "CREATE_COMPLETE":
            outputs = {o["OutputKey"]: o["OutputValue"] for o in stack.get("Outputs", [])}
            log_info(
                "task", "check_completion", "stack_created",
                f"Stack {stack_name} created successfully — {len(outputs)} output(s)"
            )
            return {
                "status": "success",
                "message": f"Stack {stack_name} created successfully",
                "output": {
                    "stack_name": stack_name,
                    "stack_id": result.get("stack_id"),
                    "stack_status": stack_status,
                    "outputs": outputs,
                },
            }

        if "FAILED" in stack_status or "ROLLBACK" in stack_status:
            log_error(
                "task", "check_completion", "stack_failed",
                f"Stack {stack_name} entered failure state: {stack_status} — {status_reason}"
            )
            return {
                "status": "failed",
                "message": f"Stack creation failed: {stack_status} — {status_reason}",
                "output": {"stack_name": stack_name, "stack_status": stack_status,
                           "status_reason": status_reason},
            }

        log_info(
            "task", "check_completion", "stack_still_creating",
            f"Stack {stack_name} still creating — current status: {stack_status}"
        )
        return {
            "status": "pending",
            "message": f"Stack status: {stack_status}",
            "output": {"stack_name": stack_name, "stack_status": stack_status},
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
                log_info("task", "finish", "client_closed",
                         "CloudFormation boto3 client closed successfully")
            except Exception as close_error:
                log_error("task", "finish", "client_close_error",
                          f"Error closing CloudFormation client: {str(close_error)}")

        if final_status == "success":
            output = completion_details.get("output", {})
            log_info(
                "task", "finish", "operation_summary",
                f"Stack {output.get('stack_name')} created — "
                f"status={output.get('stack_status')}, "
                f"outputs={list(output.get('outputs', {}).keys())}"
            )
        elif final_status == "failed":
            log_error("task", "finish", "operation_failed",
                      f"Stack creation failed: {completion_details.get('message')}")
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
    "stack_name": "my-stack",                          # required
    "template_body": {                                  # required* — inline template (dict auto-serialized to JSON)
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "My stack",
        "Resources": {
            "MyBucket": {"Type": "AWS::S3::Bucket"}
        }
    },
    # "template_url": "https://s3.amazonaws.com/bucket/template.yaml",  # required* — alternative to template_body
    "capabilities": ["CAPABILITY_IAM"],                 # optional — required for IAM/named IAM/SAM resources
    "on_failure": "ROLLBACK",                           # optional — DO_NOTHING | ROLLBACK | DELETE (default: ROLLBACK)
    # "parameters": [                                   # optional — template parameter overrides
    #     {"ParameterKey": "EnvName", "ParameterValue": "prod"}
    # ],
    # "timeout_in_minutes": 30,                         # optional — triggers on_failure if exceeded
    # "tags": [{"Key": "Env", "Value": "prod"}],        # optional
    # "notification_arns": ["arn:aws:sns:..."],          # optional — SNS topics for stack event notifications
    # "role_arn": "arn:aws:iam::123456789012:role/CFNRole"  # optional — role CloudFormation assumes
}

prompt = (
    "Create a CloudFormation stack from a template. "
    "Required: stack_name and either template_body (inline JSON/YAML string or dict) or template_url (S3 URL). "
    "Optional: parameters, capabilities (CAPABILITY_IAM/CAPABILITY_NAMED_IAM/CAPABILITY_AUTO_EXPAND), "
    "on_failure (DO_NOTHING/ROLLBACK/DELETE, default ROLLBACK), timeout_in_minutes, tags, notification_arns, role_arn. "
    "Async — polls until CREATE_COMPLETE. Returns stack outputs on success. "
    "Auth: explicit keys first, then assume_iam_role via STS, then default credential chain. "
    "finish() must close the boto3 client without re-raising exceptions."
)

install_docs = """# AWSCloudFormationCreateStack — Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:CreateStack",
        "cloudformation:DescribeStacks",
        "cloudformation:ListStacks"
      ],
      "Resource": "*"
    }

    Plus permissions for every resource type in your template
    (e.g. s3:CreateBucket, ec2:RunInstances, iam:CreateRole).

## Auth Setup

| Method             | How                                                                    |
|--------------------|------------------------------------------------------------------------|
| Access keys        | Set aws_access_key_id and aws_secret_access_key in connection          |
| Assume IAM role    | Set assume_iam_role (ARN) in connection — runner assumes it via STS    |
| Default chain      | Omit all auth fields — boto3 uses instance profile / ECS task role etc |
"""

guide_docs = """# AWSCloudFormationCreateStack — Operator Guide

## What it does

Creates a CloudFormation stack from an inline template or an S3-hosted template. Async —
returns immediately after the `create_stack` API call with `status:pending`. `check_completion`
polls `describe_stacks` until the stack reaches `CREATE_COMPLETE` or a failure state.
Stack outputs (defined in the `Outputs` section of your template) are returned on success.

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

| Field                 | Required   | Description                                              |
|-----------------------|------------|----------------------------------------------------------|
| region                | Yes        | AWS region to create the stack in                        |
| aws_access_key_id     | Scenario 1 | IAM user access key                                      |
| aws_secret_access_key | Scenario 1 | IAM user secret key                                      |
| aws_session_token     | No         | Temporary session token for STS-issued credentials       |
| assume_iam_role       | Scenario 2 | Role ARN to assume via STS                               |

---

## Payload

| Field               | Required | Description                                                                    |
|---------------------|----------|--------------------------------------------------------------------------------|
| stack_name          | Yes      | Unique stack name (letters, numbers, hyphens only)                             |
| template_body       | Yes*     | Inline template — JSON/YAML string or dict (dict auto-serialized)              |
| template_url        | Yes*     | S3 HTTPS URL of the template (alternative to template_body)                    |
| parameters          | No       | List of `{"ParameterKey": str, "ParameterValue": str}` overrides              |
| capabilities        | No       | Required for IAM resources: CAPABILITY_IAM, CAPABILITY_NAMED_IAM, CAPABILITY_AUTO_EXPAND |
| on_failure          | No       | DO_NOTHING / ROLLBACK / DELETE (default: ROLLBACK)                             |
| timeout_in_minutes  | No       | Max creation time — triggers on_failure if exceeded                            |
| tags                | No       | List of `{"Key": str, "Value": str}` applied to the stack and its resources   |
| notification_arns   | No       | SNS topic ARNs for stack event notifications                                   |
| role_arn            | No       | IAM role CloudFormation assumes to create resources                            |

*Provide either `template_body` OR `template_url`, not both.

---

## Output (on success)

    {
      "stack_name":   "my-stack",
      "stack_id":     "arn:aws:cloudformation:us-east-1:123456789012:stack/my-stack/abc123",
      "stack_status": "CREATE_COMPLETE",
      "outputs":      {"BucketName": "my-bucket-abc123", "ApiUrl": "https://..."}
    }

| Field        | Description                                                              |
|--------------|--------------------------------------------------------------------------|
| stack_name   | Name of the created stack                                                |
| stack_id     | Unique stack ARN                                                         |
| stack_status | Always CREATE_COMPLETE on success                                        |
| outputs      | Dict of Output key→value from the template's Outputs section             |

---

## Scenarios and Edge Cases

**Stack already exists:**
  `create_stack` returns `AlreadyExistsException`. Caught and returned as `status:failed`.
  Use a CloudFormation update or delete+recreate pattern.

**Missing capabilities:**
  If the template creates IAM resources and `capabilities` is not set,
  AWS returns `InsufficientCapabilitiesException`. Add `CAPABILITY_IAM` or `CAPABILITY_NAMED_IAM`.

**Template too large for inline:**
  Inline templates are limited to 51,200 bytes. For larger templates, upload to S3 and use `template_url`.

**Creation failure with ROLLBACK:**
  The stack enters ROLLBACK_COMPLETE. `check_completion` returns `status:failed` with the
  `StackStatusReason` explaining the failure.

**on_failure=DELETE:**
  Failed stacks are automatically deleted — useful for clean CI/CD pipelines where failed
  stacks should not linger.

---

## What this operator does NOT do

- Does not update existing stacks — use CloudFormation UpdateStack for that
- Does not validate the template before creation — use ValidateTemplate first if needed
- Does not support change sets — use CreateChangeSet for zero-downtime updates
"""

description = """
Creates a CloudFormation stack from an inline template or S3-hosted template. Async —
polls describe_stacks until CREATE_COMPLETE. Supports parameters, capabilities, on_failure
behavior, timeout, tags, SNS notifications, and custom IAM role for CloudFormation. Returns
all stack outputs on success. Auth: explicit keys first, then assume_iam_role via STS, then
default credential chain. finish() closes the boto3 client without re-raising exceptions.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "CloudFormation",
    "category": "Infrastructure",
    "tags": ["cloudformation", "iac", "infrastructure", "stack", "aws"],
    "airflow_equivalent": "CloudFormationCreateStackOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

**Capabilities requirement**: Templates that create IAM roles, policies, or instance profiles
require `CAPABILITY_IAM`. Templates with explicitly named IAM resources require
`CAPABILITY_NAMED_IAM`. SAM (Serverless Application Model) templates require
`CAPABILITY_AUTO_EXPAND`. Omitting the required capability returns
`InsufficientCapabilitiesException` — always check your template for IAM resources.

**Template size limits**: Inline `template_body` is limited to 51,200 bytes. For larger
templates, upload to S3 and pass the HTTPS URL via `template_url`. Note that the URL must
be an HTTPS S3 URL (not an s3:// URI) and the template must be publicly readable or
accessible by the CloudFormation service role.

**on_failure behavior**: `ROLLBACK` (default) keeps the stack in ROLLBACK_COMPLETE state
after failure — useful for debugging but the stack must be manually deleted before retrying.
`DELETE` automatically removes the failed stack — cleaner for CI/CD. `DO_NOTHING` leaves
resources as-is for investigation.

**Stack outputs**: Template `Outputs` are returned in the `outputs` dict on success. Use
these to pass resource identifiers (bucket names, endpoint URLs, ARNs) to downstream tasks
without hardcoding names.

**Permission model**: The calling identity needs permissions for every resource type in the
template PLUS `cloudformation:CreateStack`. Alternatively, use `role_arn` to delegate
resource creation to a dedicated CloudFormation execution role — the calling identity only
needs `iam:PassRole` and `cloudformation:CreateStack`.
"""
