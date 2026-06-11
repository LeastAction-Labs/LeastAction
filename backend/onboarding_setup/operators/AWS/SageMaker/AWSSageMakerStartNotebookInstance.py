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
AWS SageMaker Start Notebook Instance Operator

Starts a stopped SageMaker notebook instance and polls until InService. Async.
Auth priority: explicit keys → assume IAM role → default credential chain.
"""

import json
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from src.common.logger.logger import log_error, log_info


def _build_sagemaker_client(connection: dict):
    region = connection.get("region", "us-east-1")
    access_key = connection.get("aws_access_key_id")
    secret_key = connection.get("aws_secret_access_key")
    session_token = connection.get("aws_session_token")
    assume_role_arn = connection.get("assume_iam_role")

    # Case 1: Explicit credentials
    if access_key and secret_key:
        log_info("task", "initialize", "auth_keys", f"Using explicit access key ending ...{access_key[-4:]}")
        session = boto3.Session(aws_access_key_id=access_key, aws_secret_access_key=secret_key,
                                aws_session_token=session_token, region_name=region)
        return session.client("sagemaker")

    # Case 2: Assume IAM role via STS
    if assume_role_arn:
        log_info("task", "initialize", "auth_assume_role", f"Assuming IAM role: {assume_role_arn}")
        sts = boto3.client("sts", region_name=region)
        assumed = sts.assume_role(RoleArn=assume_role_arn, RoleSessionName="leastaction_session")
        creds = assumed["Credentials"]
        session = boto3.Session(aws_access_key_id=creds["AccessKeyId"],
                                aws_secret_access_key=creds["SecretAccessKey"],
                                aws_session_token=creds["SessionToken"], region_name=region)
        return session.client("sagemaker")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info("task", "initialize", "auth_default",
             "Using default AWS credential chain (instance profile / ECS task role / env / config)")
    return boto3.Session(region_name=region).client("sagemaker")


def initialize(least_action_task_object):
    """Build and verify the SageMaker boto3 client. Returns: boto3 sagemaker client"""
    try:
        connection = least_action_task_object.get("connection", {})
        if isinstance(connection, str):
            connection = json.loads(connection)
        task_laui = least_action_task_object.get("laui")
        log_info("task", "initialize", "start",
                 f"Initializing AWSSageMakerStartNotebookInstance for task: {task_laui}")
        client = _build_sagemaker_client(connection)
        region = connection.get("region", "us-east-1")
        log_info("task", "initialize", "verify_connection", f"Verifying SageMaker connectivity in region: {region}")
        try:
            client.list_domains(MaxResults=1)
        except ClientError:
            pass
        log_info("task", "initialize", "connection_established", f"SageMaker client ready for region: {region}")
        return client
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
    Starts a stopped SageMaker notebook instance.

    Payload fields:
        notebook_instance_name  (str, required)  -- name of the stopped notebook instance to start

    Returns: dict with status, execution_type, result
    """
    try:
        task_laui = least_action_task_object.get("laui")
        payload = least_action_task_object.get("payload", {})
        log_info("task", "run", "extracting_payload", f"Extracting configuration for task: {task_laui}")
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                log_error("task", "run", "payload_parse_error", "Failed to parse payload as JSON")
                return {"status": "failed", "execution_type": "async", "result": None,
                        "error": "Invalid payload format — expected flat JSON object"}
        if isinstance(payload, dict) and "data" in payload and isinstance(payload["data"], dict):
            payload = payload["data"]
            log_info("task", "run", "payload_unwrapped", "Unwrapped payload data envelope")

        notebook_instance_name = payload.get("notebook_instance_name")
        if not notebook_instance_name:
            log_error("task", "run", "validation_error", "Required field missing: notebook_instance_name")
            return {"status": "failed", "execution_type": "async", "result": None,
                    "error": "Required field missing: notebook_instance_name"}

        log_info("task", "run", "starting_notebook_instance",
                 f"Starting notebook instance: {notebook_instance_name}")
        client.start_notebook_instance(NotebookInstanceName=notebook_instance_name)
        log_info("task", "run", "start_requested",
                 f"Start request sent for notebook instance: {notebook_instance_name}")

        return {"status": "pending", "execution_type": "async",
                "result": {"notebook_instance_name": notebook_instance_name}}
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
    """Poll describe_notebook_instance until InService or Failed."""
    if run_details.get("status") == "failed":
        log_error("task", "check_completion", "run_phase_failed",
                  f"Run phase reported failure: {run_details.get('error')}")
        return {"status": "failed",
                "message": f"Run phase failed: {run_details.get('error')}",
                "output": None}
    try:
        notebook_instance_name = (run_details.get("result") or {}).get("notebook_instance_name")
        if not notebook_instance_name:
            return {"status": "failed", "message": "No notebook_instance_name in run_details", "output": None}

        response = client.describe_notebook_instance(NotebookInstanceName=notebook_instance_name)
        nb_status = response.get("NotebookInstanceStatus", "Unknown")
        log_info("task", "check_completion", "notebook_status",
                 f"Notebook {notebook_instance_name} status: {nb_status}")

        if nb_status == "InService":
            notebook_instance_url = response.get("Url", "")
            return {"status": "success",
                    "message": f"Notebook instance {notebook_instance_name} is InService",
                    "output": {"notebook_instance_name": notebook_instance_name,
                               "notebook_instance_url": notebook_instance_url,
                               "notebook_instance_status": nb_status}}
        elif nb_status == "Failed":
            failure_reason = response.get("FailureReason", "Unknown")
            return {"status": "failed",
                    "message": f"Notebook instance start failed: {failure_reason}",
                    "output": {"notebook_instance_name": notebook_instance_name,
                               "failure_reason": failure_reason}}
        return {"status": "pending",
                "message": f"Notebook instance {notebook_instance_name} is {nb_status}",
                "output": None}
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "check_completion", "client_error", f"AWS ClientError ({error_code}): {error_msg}")
        return {"status": "failed", "message": f"{error_code}: {error_msg}", "output": None}
    except Exception as e:
        log_error("task", "check_completion", "unexpected_error", f"Unexpected error: {str(e)}")
        return {"status": "failed", "message": str(e), "output": None}


def finish(least_action_task_object, client, completion_details, run_details):
    """Log final outcome and release held resources. Returns: None"""
    try:
        task_laui = least_action_task_object.get("laui")
        log_info("task", "finish", "starting_cleanup", f"Starting cleanup for task: {task_laui}")
        final_status = completion_details.get("status", "unknown")
        log_info("task", "finish", "final_status", f"Task ended with status: {final_status}")
        if client:
            try:
                client.close()
                log_info("task", "finish", "client_closed", "SageMaker boto3 client closed successfully")
            except Exception as close_error:
                log_error("task", "finish", "client_close_error", f"Error closing client: {str(close_error)}")
        if final_status == "success":
            output = completion_details.get("output") or {}
            log_info("task", "finish", "operation_summary",
                     f"Notebook instance {output.get('notebook_instance_name')} is InService. "
                     f"URL: {output.get('notebook_instance_url')}")
        elif final_status == "failed":
            log_error("task", "finish", "operation_failed",
                      f"Operation failed: {completion_details.get('message')}")
        else:
            log_info("task", "finish", "operation_status",
                     f"status={final_status}, message={completion_details.get('message')}")
        log_info("task", "finish", "cleanup_complete", f"Cleanup complete for task: {task_laui}")
    except Exception as e:
        log_error("task", "finish", "cleanup_error", f"Error during finish/cleanup: {str(e)}")
        # Never re-raise from finish
'''}

bashblock = {"main.sh": """#!/bin/bash\nset -e\npip install boto3>=1.28.0\npip install botocore>=1.31.0\necho \"Dependencies installed successfully\"\n"""}

connection = {"region": "us-east-1"}

payload = {
    "notebook_instance_name": "my-dev-notebook",
}

prompt = (
    "Starts a stopped SageMaker notebook instance and polls until InService. "
    "Provide notebook_instance_name. "
    "The instance must be in Stopped state. "
    "Async — polls describe_notebook_instance until InService or Failed."
)

install_docs = """## Dependencies
- boto3>=1.28.0
- botocore>=1.31.0

## IAM Permissions Required
- sagemaker:StartNotebookInstance
- sagemaker:DescribeNotebookInstance
"""

guide_docs = """## What it does

Starts a stopped SageMaker notebook instance and polls until it reaches InService status. Billing for compute resumes immediately when the start request is sent — before InService is reached. All data from the previous session on the EBS volume is preserved. On success the operator returns the notebook URL for direct browser access. This operator is async.

---

## Auth

Three methods are supported, evaluated in this priority order:

1. **Access keys** — if `aws_access_key_id` + `aws_secret_access_key` are present in the connection, they are used immediately. Suitable for IAM users, CI/CD pipelines, or any environment outside AWS.
2. **Assume IAM role** — if `assume_iam_role` (role ARN) is present and access keys are absent, the operator assumes the specified role via STS. Use this for cross-account access or when you need to scope down to a least-privilege role.
3. **Default credential chain** — boto3 falls back to the standard AWS credential chain: EC2 instance profile, ECS task role, Lambda execution role, environment variables, or `~/.aws/credentials`.

---

## Connection

**Scenario 1 — Access keys** (IAM user, CI/CD, running outside AWS):

    {
      "region": "us-east-1",
      "aws_access_key_id": "AKIA...",          // IAM user access key
      "aws_secret_access_key": "...",           // IAM user secret key
      "aws_session_token": "..."                // only needed for temporary/STS-issued credentials
    }

**Scenario 2 — Assume IAM role** (cross-account or least-privilege scoping):

    {
      "region": "us-east-1",
      "assume_iam_role": "arn:aws:iam::123456789012:role/MyRole"
    }

**Scenario 3 — Default credential chain** (EC2 instance profile, ECS task role, Lambda role):

    {"region": "us-east-1"}

| Field                 | Required   | Description                                                                          |
|-----------------------|------------|--------------------------------------------------------------------------------------|
| region                | Yes        | AWS region where the SageMaker resources exist                                       |
| aws_access_key_id     | Scenario 1 | IAM user access key                                                                  |
| aws_secret_access_key | Scenario 1 | IAM user secret key — required alongside aws_access_key_id                          |
| aws_session_token     | No         | Temporary session token — only needed with short-lived STS credentials               |
| assume_iam_role       | Scenario 2 | Role ARN to assume via STS                                                           |

---

## Payload

| Field                  | Required | Description                                                            |
|------------------------|----------|------------------------------------------------------------------------|
| notebook_instance_name | Yes      | Name of the stopped notebook instance to start                         |

---

## Output (on success)

    {
      "notebook_instance_name": "my-dev-notebook",
      "notebook_instance_url": "https://my-dev-notebook.notebook.us-east-1.sagemaker.aws/",
      "notebook_instance_status": "InService"
    }

| Field                    | Description                                                       |
|--------------------------|-------------------------------------------------------------------|
| notebook_instance_name   | Name of the started notebook instance                             |
| notebook_instance_url    | Direct URL to open the Jupyter environment in a browser           |
| notebook_instance_status | Final status — InService on success                               |

---

## Scenarios and Edge Cases

Instance already running (idempotent — succeeds):
  If the instance is already InService, the start call raises a ValidationException. This operator does not handle that case automatically — check the current status before calling if the instance state is uncertain.

Instance in Pending state (wait):
  If the instance is already in Pending or Updating state from a previous operation, the start call may fail. Poll describe_notebook_instance until it reaches a stable state (Stopped or InService) before calling start.

Instance Failed:
  If the instance entered the Failed state due to a prior error, start may raise ValidationException. The instance may need to be deleted and recreated.

---

## What this operator does NOT do

- Does not create the notebook instance — use AWSSageMakerCreateNotebookInstance to provision a new one.
- Does not install Python packages at runtime — packages must be pre-installed in the image or via lifecycle configuration.
- Does not handle the already-InService case gracefully — raises ValidationException if called on a running instance.
"""

description = (
    "Starts a stopped SageMaker notebook instance and polls asynchronously until InService. "
    "Returns the notebook URL on success."
)

publisher = "LeastActionLabs"

metadata = {
    "service": "SageMaker",
    "category": "ML",
    "tags": ["sagemaker", "notebook", "start", "aws"],
    "airflow_equivalent": "SageMakerStartNotebookInstanceOperator",
}

version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False
status = "draft"

publisher_notes = """## Publisher Notes

Billing resumes immediately when start_notebook_instance is called — the instance incurs charges even during the Pending state before reaching InService.
Starting typically takes 2-5 minutes. Lifecycle config scripts (if any) run on each start and can add extra time.
All data on the EBS volume is preserved between stop/start cycles — no data is lost.
Use this after AWSSageMakerStopNotebookInstance to resume a paused development session.
Calling start on an already-InService instance raises a ValidationException — handle gracefully in orchestration pipelines.
"""
