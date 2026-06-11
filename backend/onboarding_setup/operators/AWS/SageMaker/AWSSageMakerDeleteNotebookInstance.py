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
AWS SageMaker Delete Notebook Instance Operator

Stops (if running) and permanently deletes a SageMaker notebook instance. Async.
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
                 f"Initializing AWSSageMakerDeleteNotebookInstance for task: {task_laui}")
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
    Stops (if needed) and deletes a SageMaker notebook instance.

    Payload fields:
        notebook_instance_name  (str, required)  -- name of the notebook instance to delete

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

        # Check current state and stop if necessary before deleting
        try:
            desc = client.describe_notebook_instance(NotebookInstanceName=notebook_instance_name)
            nb_status = desc.get("NotebookInstanceStatus", "Unknown")
            log_info("task", "run", "current_status",
                     f"Notebook {notebook_instance_name} current status: {nb_status}")

            if nb_status in ("InService", "Pending", "Updating"):
                log_info("task", "run", "stopping_before_delete",
                         f"Stopping notebook {notebook_instance_name} before deletion (status: {nb_status})")
                try:
                    client.stop_notebook_instance(NotebookInstanceName=notebook_instance_name)
                    log_info("task", "run", "stop_requested",
                             f"Stop request sent for notebook: {notebook_instance_name}")
                except ClientError as stop_err:
                    stop_code = stop_err.response.get("Error", {}).get("Code", "Unknown")
                    log_info("task", "run", "stop_skipped",
                             f"Stop call returned {stop_code} — may already be stopping")
                # Deletion will be attempted in check_completion after stop completes
                return {"status": "pending", "execution_type": "async",
                        "result": {"notebook_instance_name": notebook_instance_name,
                                   "phase": "stopping"}}

            if nb_status in ("Stopped", "Failed"):
                log_info("task", "run", "deleting_notebook",
                         f"Notebook is {nb_status} — proceeding with deletion")
                client.delete_notebook_instance(NotebookInstanceName=notebook_instance_name)
                log_info("task", "run", "delete_initiated",
                         f"Delete request sent for notebook: {notebook_instance_name}")
                return {"status": "pending", "execution_type": "async",
                        "result": {"notebook_instance_name": notebook_instance_name,
                                   "phase": "deleting"}}

        except ClientError as desc_err:
            desc_code = desc_err.response.get("Error", {}).get("Code", "Unknown")
            if desc_code == "ValidationException":
                log_info("task", "run", "already_deleted",
                         f"Notebook {notebook_instance_name} not found — already deleted")
                return {"status": "success", "execution_type": "async",
                        "result": {"notebook_instance_name": notebook_instance_name,
                                   "message": "Notebook instance not found — already deleted"}}
            raise

        return {"status": "pending", "execution_type": "async",
                "result": {"notebook_instance_name": notebook_instance_name, "phase": "deleting"}}

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
    Poll state: if stopping → try delete once stopped; if deleting → confirm ResourceNotFound = success.
    """
    if run_details.get("status") == "failed":
        log_error("task", "check_completion", "run_phase_failed",
                  f"Run phase reported failure: {run_details.get('error')}")
        return {"status": "failed",
                "message": f"Run phase failed: {run_details.get('error')}",
                "output": None}

    # Already deleted in run()
    if run_details.get("status") == "success":
        return {"status": "success",
                "message": "Notebook instance already deleted",
                "output": run_details.get("result")}

    try:
        result = run_details.get("result") or {}
        notebook_instance_name = result.get("notebook_instance_name")
        if not notebook_instance_name:
            return {"status": "failed", "message": "No notebook_instance_name in run_details", "output": None}

        try:
            response = client.describe_notebook_instance(NotebookInstanceName=notebook_instance_name)
            nb_status = response.get("NotebookInstanceStatus", "Unknown")
            log_info("task", "check_completion", "notebook_status",
                     f"Notebook {notebook_instance_name} status: {nb_status}")

            # If stopped but not yet deleted, issue delete
            if nb_status == "Stopped":
                log_info("task", "check_completion", "issuing_delete",
                         f"Notebook is Stopped — issuing delete for {notebook_instance_name}")
                try:
                    client.delete_notebook_instance(NotebookInstanceName=notebook_instance_name)
                    log_info("task", "check_completion", "delete_initiated",
                             f"Delete request sent for notebook: {notebook_instance_name}")
                except ClientError as del_err:
                    del_code = del_err.response.get("Error", {}).get("Code", "Unknown")
                    log_info("task", "check_completion", "delete_call_result",
                             f"Delete call returned {del_code}")
                return {"status": "pending",
                        "message": f"Notebook {notebook_instance_name} is Stopped — delete requested",
                        "output": None}

            if nb_status == "Failed":
                failure_reason = response.get("FailureReason", "Unknown")
                return {"status": "failed",
                        "message": f"Notebook instance failed: {failure_reason}",
                        "output": {"notebook_instance_name": notebook_instance_name}}

            # Stopping or Deleting — still in progress
            return {"status": "pending",
                    "message": f"Notebook instance {notebook_instance_name} is {nb_status}",
                    "output": None}

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "ValidationException":
                # Instance is gone — deletion complete
                log_info("task", "check_completion", "deleted_confirmed",
                         f"Notebook {notebook_instance_name} is gone — deletion complete")
                return {"status": "success",
                        "message": "Notebook instance deleted successfully",
                        "output": {"notebook_instance_name": notebook_instance_name}}
            raise

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
                     f"Notebook instance {output.get('notebook_instance_name')} deleted successfully")
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
    "Stops (if InService) and permanently deletes a SageMaker notebook instance. "
    "Provide notebook_instance_name. "
    "Automatically stops the instance before deletion if it is running. "
    "Async — polls until deletion is confirmed via ResourceNotFound."
)

install_docs = """## Dependencies
- boto3>=1.28.0
- botocore>=1.31.0

## IAM Permissions Required
- sagemaker:DescribeNotebookInstance
- sagemaker:StopNotebookInstance
- sagemaker:DeleteNotebookInstance
"""

guide_docs = """## What it does

Stops (if currently running) and permanently deletes a SageMaker notebook instance. The operator handles the full stop-then-delete lifecycle automatically: it checks the current state, sends a stop request if needed, waits for the instance to reach Stopped, then issues the delete. Deletion is confirmed by polling until describe_notebook_instance raises a ResourceNotFound error. All data on the EBS volume is permanently lost. This operator is async.

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

| Field                  | Required | Description                                         |
|------------------------|----------|-----------------------------------------------------|
| notebook_instance_name | Yes      | Name of the notebook instance to stop and delete    |

---

## Output (on success)

    {
      "notebook_instance_name": "my-dev-notebook"
    }

| Field                  | Description                                              |
|------------------------|----------------------------------------------------------|
| notebook_instance_name | Name of the deleted notebook instance                    |

---

## Scenarios and Edge Cases

Instance already stopped (stop call silently ignored):
  If the instance is already in Stopped or Failed state, the operator skips the stop phase and proceeds directly to deletion. The stop call is handled idempotently.

Instance not found (error):
  If the instance does not exist at all, the operator returns success — it treats a missing instance as already deleted. This is safe for cleanup pipelines.

EBS data permanently lost on deletion:
  All files on the notebook's EBS volume are deleted when the instance is deleted. Back up any notebooks to S3, Git, or another persistent store before running this operator.

---

## What this operator does NOT do

- Does not back up notebook files before deletion — you must do this manually before running this operator.
- Does not delete the IAM role associated with the instance.
- Does not delete the lifecycle configuration attached to the instance.
- Does not delete the KMS key used for EBS encryption.
"""

description = (
    "Stops (if running) and permanently deletes a SageMaker notebook instance. "
    "Handles the stop-then-delete sequence automatically. Async."
)

publisher = "LeastActionLabs"

metadata = {
    "service": "SageMaker",
    "category": "ML",
    "tags": ["sagemaker", "notebook", "delete", "aws"],
    "airflow_equivalent": "SageMakerDeleteNotebookInstanceOperator",
}

version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False
status = "draft"

publisher_notes = """## Publisher Notes

This operator handles the full stop-then-delete lifecycle automatically — no need to call AWSSageMakerStopNotebookInstance first.
The operator checks current status: if InService/Pending/Updating it sends a stop request, then in check_completion it re-checks and issues the delete once Stopped.
Deletion success is confirmed by receiving a ValidationException from describe_notebook_instance (ResourceNotFound) — this is the standard AWS pattern for async deletion polling.
All data on the EBS volume is permanently lost on deletion — there is no recovery. Save notebooks to S3 or a Git repository before deleting.
The EBS KMS key (if any) is not deleted by this operator.
Typical total time: 2-8 minutes (stop 1-3 min + delete 1-3 min).
"""
