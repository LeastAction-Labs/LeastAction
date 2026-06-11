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
AWS SageMaker Create Notebook Instance Operator

Creates and starts a SageMaker managed Jupyter notebook instance. Async.
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
                 f"Initializing AWSSageMakerCreateNotebookInstance for task: {task_laui}")
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
    Creates and starts a SageMaker notebook instance.

    Payload fields:
        notebook_instance_name  (str, required)  -- unique name for the notebook instance
        instance_type           (str, required)  -- SageMaker instance type (e.g. ml.t3.medium)
        role_arn                (str, required)  -- IAM role ARN for the notebook instance
        volume_size_gb          (int, optional)  -- EBS volume size in GB (default: 5)
        subnet_id               (str, optional)  -- VPC subnet ID
        security_group_ids      (list, optional) -- list of security group IDs
        kms_key_id              (str, optional)  -- KMS key ID for EBS encryption
        lifecycle_config_name   (str, optional)  -- lifecycle configuration name for startup scripts
        direct_internet_access  (str, optional)  -- "Enabled" or "Disabled" (default: "Enabled")
        root_access             (str, optional)  -- "Enabled" or "Disabled" (default: "Enabled")
        tags                    (list, optional) -- list of {"Key": ..., "Value": ...} dicts

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
        instance_type = payload.get("instance_type")
        role_arn = payload.get("role_arn")

        if not notebook_instance_name:
            log_error("task", "run", "validation_error", "Required field missing: notebook_instance_name")
            return {"status": "failed", "execution_type": "async", "result": None,
                    "error": "Required field missing: notebook_instance_name"}
        if not instance_type:
            log_error("task", "run", "validation_error", "Required field missing: instance_type")
            return {"status": "failed", "execution_type": "async", "result": None,
                    "error": "Required field missing: instance_type"}
        if not role_arn:
            log_error("task", "run", "validation_error", "Required field missing: role_arn")
            return {"status": "failed", "execution_type": "async", "result": None,
                    "error": "Required field missing: role_arn"}

        kwargs = {
            "NotebookInstanceName": notebook_instance_name,
            "InstanceType": instance_type,
            "RoleArn": role_arn,
        }
        optional_fields = {
            "VolumeSizeInGB": payload.get("volume_size_gb", 5),
            "SubnetId": payload.get("subnet_id"),
            "KmsKeyId": payload.get("kms_key_id"),
            "LifecycleConfigName": payload.get("lifecycle_config_name"),
            "DirectInternetAccess": payload.get("direct_internet_access"),
            "RootAccess": payload.get("root_access"),
        }
        for key, value in optional_fields.items():
            if value is not None:
                kwargs[key] = value
        if payload.get("security_group_ids"):
            kwargs["SecurityGroupIds"] = payload["security_group_ids"]
        if payload.get("tags"):
            kwargs["Tags"] = payload["tags"]

        log_info("task", "run", "creating_notebook_instance",
                 f"Creating notebook instance: {notebook_instance_name} type={instance_type}")
        response = client.create_notebook_instance(**kwargs)
        notebook_instance_arn = response.get("NotebookInstanceArn", "")
        log_info("task", "run", "notebook_instance_created",
                 f"Notebook instance creation initiated. ARN: {notebook_instance_arn}")

        return {"status": "pending", "execution_type": "async",
                "result": {"notebook_instance_name": notebook_instance_name,
                           "notebook_instance_arn": notebook_instance_arn}}
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
                               "notebook_instance_arn": (run_details.get("result") or {}).get("notebook_instance_arn", ""),
                               "notebook_instance_url": notebook_instance_url,
                               "notebook_instance_status": nb_status}}
        elif nb_status == "Failed":
            failure_reason = response.get("FailureReason", "Unknown")
            return {"status": "failed",
                    "message": f"Notebook instance creation failed: {failure_reason}",
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
    "instance_type": "ml.t3.medium",
    "role_arn": "arn:aws:iam::123456789012:role/SageMakerExecutionRole",
    # "volume_size_gb": 5,                    # optional, default 5
    # "subnet_id": "subnet-abc123",           # optional
    # "security_group_ids": ["sg-xxx"],       # optional
    # "kms_key_id": "arn:aws:kms:...",        # optional
    # "lifecycle_config_name": "my-config",   # optional
    # "direct_internet_access": "Enabled",    # optional
    # "root_access": "Enabled",               # optional
}

prompt = (
    "Creates and starts a SageMaker managed Jupyter notebook instance. "
    "Provide notebook_instance_name, instance_type, role_arn. "
    "Optional: volume_size_gb (default 5), subnet_id, security_group_ids, kms_key_id, "
    "lifecycle_config_name, direct_internet_access (default Enabled), root_access (default Enabled), tags. "
    "Async — polls describe_notebook_instance until InService or Failed."
)

install_docs = """## Dependencies
- boto3>=1.28.0
- botocore>=1.31.0

## IAM Permissions Required
- sagemaker:CreateNotebookInstance
- sagemaker:DescribeNotebookInstance
- iam:PassRole (on role_arn)

## Prerequisites
- role_arn must trust sagemaker.amazonaws.com as a service principal
"""

guide_docs = """## What it does

Creates and starts a SageMaker managed Jupyter notebook instance. The instance is a fully managed EC2 machine with pre-installed Jupyter, conda environments, and AWS SDK integrations. The operator submits the create request and polls describe_notebook_instance until the instance reaches InService. On success it returns the notebook URL for direct browser access. This operator is async.

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

| Field                  | Required | Description                                                                      |
|------------------------|----------|----------------------------------------------------------------------------------|
| notebook_instance_name | Yes      | Unique name for the notebook instance                                            |
| instance_type          | Yes      | SageMaker instance type (e.g. ml.t3.medium, ml.m5.xlarge)                       |
| role_arn               | Yes      | IAM role ARN that the notebook instance assumes for AWS API calls                |
| volume_size_gb         | No       | EBS volume size in GB (default: 5)                                               |
| subnet_id              | No       | VPC subnet ID — required for VPC-only (no direct internet access) mode           |
| security_group_ids     | No       | List of security group IDs attached to the instance                              |
| kms_key_id             | No       | KMS key ID or ARN for EBS volume encryption                                      |
| lifecycle_config_name  | No       | Name of a lifecycle configuration to run startup/shutdown scripts                |
| direct_internet_access | No       | "Enabled" or "Disabled" — controls internet access (default: Enabled)            |
| root_access            | No       | "Enabled" or "Disabled" — controls root access in Jupyter (default: Enabled)     |
| tags                   | No       | List of {"Key": ..., "Value": ...} dicts                                         |

---

## Output (on success)

    {
      "notebook_instance_name": "my-dev-notebook",
      "notebook_instance_arn": "arn:aws:sagemaker:us-east-1:123456789012:notebook-instance/my-dev-notebook",
      "notebook_instance_url": "https://my-dev-notebook.notebook.us-east-1.sagemaker.aws/",
      "notebook_instance_status": "InService"
    }

| Field                    | Description                                                      |
|--------------------------|------------------------------------------------------------------|
| notebook_instance_name   | Name of the created notebook instance                            |
| notebook_instance_arn    | Full ARN of the notebook instance                                |
| notebook_instance_url    | Direct URL to open the Jupyter environment in a browser          |
| notebook_instance_status | Final status — InService on success                              |

---

## Scenarios and Edge Cases

Name already exists (ValidationException):
  If a notebook instance with the same name already exists, AWS raises ValidationException. Use a unique name or start the existing instance with AWSSageMakerStartNotebookInstance.

Lifecycle config not found:
  If lifecycle_config_name refers to a configuration that does not exist, the create call raises ValidationException. Verify the lifecycle config name in the console before using it.

Subnet and security groups in different VPCs:
  If subnet_id and security_group_ids belong to different VPCs, AWS raises a ValidationException during create. Ensure all networking resources are in the same VPC.

---

## What this operator does NOT do

- Does not install Python packages at runtime — use a lifecycle configuration script to pre-install packages on every start.
- Does not access S3 data directly — the role_arn must have the appropriate S3 permissions for the notebook to read or write data.
- Does not stop or delete the instance after creation — use AWSSageMakerStopNotebookInstance to halt billing when not in use.
"""

description = (
    "Creates and starts a SageMaker managed Jupyter notebook instance. "
    "Polls asynchronously until InService. Returns the notebook URL on success."
)

publisher = "LeastActionLabs"

metadata = {
    "service": "SageMaker",
    "category": "ML",
    "tags": ["sagemaker", "notebook", "jupyter", "development", "aws"],
    "airflow_equivalent": "SageMakerCreateNotebookInstanceOperator",
}

version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False
status = "draft"

publisher_notes = """## Publisher Notes

Notebook instances are ML development environments — they are NOT suitable for production workloads.
Instances run continuously and incur charges even when idle — always pair with AWSSageMakerStopNotebookInstance in scheduled pipelines.
For automated/batch workloads, use AWSSageMakerStartProcessingJob or AWSSageMakerStartTrainingJob instead.
Lifecycle configs run scripts on every start — use them to pre-install packages and configure the environment.
ml.t3.medium is the cheapest instance type (~$0.05/hr) and sufficient for most notebook development tasks.
direct_internet_access="Disabled" + subnet_id enables VPC-only mode — the notebook cannot reach the internet but can access VPC resources.
"""
