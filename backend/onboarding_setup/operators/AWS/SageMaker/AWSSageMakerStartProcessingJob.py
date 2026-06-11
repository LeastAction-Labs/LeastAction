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
AWS SageMaker Start Processing Job Operator

Starts a SageMaker Processing Job for data preprocessing, evaluation, or custom scripts. Async.
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
                 f"Initializing AWSSageMakerStartProcessingJob for task: {task_laui}")
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
    Starts a SageMaker Processing Job.

    Payload fields:
        processing_job_name   (str, required)   -- unique name for the processing job
        role_arn              (str, required)   -- IAM execution role ARN
        app_specification     (dict, required)  -- {"ImageUri": "...", "ContainerEntrypoint": [...], "ContainerArguments": [...]}
        processing_resources  (dict, required)  -- {"ClusterConfig": {"InstanceCount": 1, "InstanceType": "ml.m5.xlarge", "VolumeSizeInGB": 30}}
        processing_inputs     (list, optional)  -- list of S3/dataset input channel configs
        processing_output_config (dict, optional) -- output channel configs with S3 destinations
        environment           (dict, optional)  -- environment variables injected into the container
        network_config        (dict, optional)  -- VPC and network isolation config
        stopping_condition    (dict, optional)  -- {"MaxRuntimeInSeconds": 3600}
        tags                  (list, optional)  -- list of {"Key": ..., "Value": ...} dicts

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

        processing_job_name = payload.get("processing_job_name")
        role_arn = payload.get("role_arn")
        app_specification = payload.get("app_specification")
        processing_resources = payload.get("processing_resources")

        for field, val in [("processing_job_name", processing_job_name),
                           ("role_arn", role_arn),
                           ("app_specification", app_specification),
                           ("processing_resources", processing_resources)]:
            if not val:
                log_error("task", "run", "validation_error", f"Required field missing: {field}")
                return {"status": "failed", "execution_type": "async", "result": None,
                        "error": f"Required field missing: {field}"}

        kwargs = {
            "ProcessingJobName": processing_job_name,
            "RoleArn": role_arn,
            "AppSpecification": app_specification,
            "ProcessingResources": processing_resources,
        }
        if payload.get("processing_inputs"):
            kwargs["ProcessingInputs"] = payload["processing_inputs"]
        if payload.get("processing_output_config"):
            kwargs["ProcessingOutputConfig"] = payload["processing_output_config"]
        if payload.get("environment"):
            kwargs["Environment"] = payload["environment"]
        if payload.get("network_config"):
            kwargs["NetworkConfig"] = payload["network_config"]
        if payload.get("stopping_condition"):
            kwargs["StoppingCondition"] = payload["stopping_condition"]
        if payload.get("tags"):
            kwargs["Tags"] = payload["tags"]

        instance_type = processing_resources.get("ClusterConfig", {}).get("InstanceType", "unknown")
        log_info("task", "run", "starting_processing_job",
                 f"Starting processing job: {processing_job_name} instance={instance_type}")
        response = client.create_processing_job(**kwargs)
        processing_job_arn = response.get("ProcessingJobArn", "")
        log_info("task", "run", "processing_job_started",
                 f"Processing job started. ARN: {processing_job_arn}")

        return {"status": "pending", "execution_type": "async",
                "result": {"processing_job_name": processing_job_name,
                           "processing_job_arn": processing_job_arn}}
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
    """Poll describe_processing_job until Completed, Failed, or Stopped."""
    if run_details.get("status") == "failed":
        log_error("task", "check_completion", "run_phase_failed",
                  f"Run phase reported failure: {run_details.get('error')}")
        return {"status": "failed",
                "message": f"Run phase failed: {run_details.get('error')}",
                "output": None}
    try:
        processing_job_name = (run_details.get("result") or {}).get("processing_job_name")
        if not processing_job_name:
            return {"status": "failed", "message": "No processing_job_name in run_details", "output": None}

        response = client.describe_processing_job(ProcessingJobName=processing_job_name)
        job_status = response.get("ProcessingJobStatus", "Unknown")
        log_info("task", "check_completion", "processing_status",
                 f"Processing job {processing_job_name} status: {job_status}")

        if job_status == "Completed":
            return {"status": "success",
                    "message": f"Processing job {processing_job_name} completed successfully",
                    "output": {"processing_job_name": processing_job_name,
                               "processing_job_arn": (run_details.get("result") or {}).get("processing_job_arn", ""),
                               "job_status": job_status}}
        elif job_status == "Failed":
            failure_reason = response.get("FailureReason", "Unknown")
            return {"status": "failed",
                    "message": f"Processing job failed: {failure_reason}",
                    "output": {"processing_job_name": processing_job_name,
                               "failure_reason": failure_reason}}
        elif job_status == "Stopped":
            return {"status": "failed",
                    "message": f"Processing job {processing_job_name} was stopped",
                    "output": {"processing_job_name": processing_job_name}}
        return {"status": "pending",
                "message": f"Processing job {processing_job_name} is {job_status}",
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
                     f"Processing job {output.get('processing_job_name')} completed successfully")
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
    "processing_job_name": "my-processing-job",
    "role_arn": "arn:aws:iam::123456789012:role/SageMakerExecutionRole",
    "app_specification": {
        "ImageUri": "683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-scikit-learn:0.23-1-cpu-py3",
        "ContainerEntrypoint": ["python3", "/opt/ml/processing/input/code/preprocess.py"]
    },
    "processing_resources": {
        "ClusterConfig": {
            "InstanceCount": 1,
            "InstanceType": "ml.m5.xlarge",
            "VolumeSizeInGB": 30
        }
    },
    # "processing_inputs": [...],           # optional
    # "processing_output_config": {...},    # optional
    # "environment": {"KEY": "VALUE"},      # optional
    # "stopping_condition": {"MaxRuntimeInSeconds": 3600},  # optional
}

prompt = (
    "Starts a SageMaker Processing Job for data preprocessing, feature engineering, or model evaluation. "
    "Provide processing_job_name, role_arn, app_specification (ImageUri + ContainerEntrypoint), "
    "processing_resources (ClusterConfig with InstanceType, InstanceCount, VolumeSizeInGB). "
    "Optional: processing_inputs, processing_output_config, environment, network_config, "
    "stopping_condition, tags. Async — polls until Completed/Failed/Stopped."
)

install_docs = """## Dependencies
- boto3>=1.28.0
- botocore>=1.31.0

## IAM Permissions Required
- sagemaker:CreateProcessingJob
- sagemaker:DescribeProcessingJob
- iam:PassRole (on role_arn)
- s3:GetObject (on input buckets)
- s3:PutObject (on output buckets)
"""

guide_docs = """## What it does

Starts a SageMaker Processing Job that runs a custom script inside a managed container for data preprocessing, feature engineering, or model evaluation. S3 inputs are downloaded and mounted into the container before the script runs; outputs written to /opt/ml/processing/output are automatically uploaded to S3 at job completion. This operator is async and polls until the job reaches Completed, Failed, or Stopped.

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

| Field                   | Required | Description                                                                      |
|-------------------------|----------|----------------------------------------------------------------------------------|
| processing_job_name     | Yes      | Unique name for the processing job                                               |
| role_arn                | Yes      | IAM execution role ARN that SageMaker assumes for the job                        |
| app_specification       | Yes      | Dict with ImageUri and ContainerEntrypoint (and optional ContainerArguments)     |
| processing_resources    | Yes      | Dict with ClusterConfig containing InstanceCount, InstanceType, VolumeSizeInGB   |
| processing_inputs       | No       | List of S3 input channel configs — each mounted at /opt/ml/processing/input/     |
| processing_output_config| No       | Output channel configs — written from /opt/ml/processing/output/ to S3           |
| environment             | No       | Dict of environment variables injected into the container                        |
| network_config          | No       | VPC and network isolation config dict                                            |
| stopping_condition      | No       | {"MaxRuntimeInSeconds": N} — caps maximum runtime to prevent cost overruns       |
| tags                    | No       | List of {"Key": ..., "Value": ...} dicts                                         |

---

## Output (on success)

    {
      "processing_job_name": "my-processing-job",
      "processing_job_arn": "arn:aws:sagemaker:us-east-1:123456789012:processing-job/my-processing-job",
      "job_status": "Completed"
    }

| Field               | Description                                              |
|---------------------|----------------------------------------------------------|
| processing_job_name | Name of the completed processing job                     |
| processing_job_arn  | Full ARN of the processing job                           |
| job_status          | Final job status — Completed on success                  |

---

## Scenarios and Edge Cases

Job name not unique:
  processing_job_name must be unique within the account. AWS raises ResourceInUse if the name is already in use. Append a timestamp or UUID for rerunnable pipelines.

Input paths mounted at /opt/ml/processing/input:
  Each entry in processing_inputs defines an S3 source and a LocalPath inside the container. The data is downloaded before the script starts. Files are available at the LocalPath specified in each input channel.

Output uploaded from /opt/ml/processing/output:
  Files written by the script to /opt/ml/processing/output (or the LocalPath defined in processing_output_config) are automatically uploaded to the configured S3 destination at job completion.

---

## What this operator does NOT do

- Does not build the container image — the ImageUri in app_specification must be a pre-built, accessible Docker image.
- Does not install Python packages at runtime — all dependencies must be pre-installed in the container image.
- Does not validate that S3 input paths exist before the job is submitted.
"""

description = (
    "Starts a SageMaker Processing Job for data preprocessing, feature engineering, "
    "model evaluation, or custom scripts. Async — polls until Completed/Failed/Stopped."
)

publisher = "LeastActionLabs"

metadata = {
    "service": "SageMaker",
    "category": "ML",
    "tags": ["sagemaker", "processing", "data-prep", "evaluation", "aws"],
    "airflow_equivalent": "SageMakerProcessingOperator",
}

version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False
status = "draft"

publisher_notes = """## Publisher Notes

Processing jobs are ideal for one-off data preparation, feature engineering, model evaluation, and custom batch scripts — they are cheaper than notebook instances for batch tasks.
The script runs inside the container at the ContainerEntrypoint. S3 inputs defined in processing_inputs are mounted at /opt/ml/processing/input/, and outputs are uploaded from /opt/ml/processing/output/ to S3 at job completion.
stopping_condition.MaxRuntimeInSeconds is strongly recommended to cap maximum runtime and prevent unexpected cost overruns.
Use AWS-provided containers for common tasks: sklearn (683313688378.dkr.ecr.{region}.amazonaws.com/sagemaker-scikit-learn:*) or Spark (aws-glue-containers-*) to avoid building custom images.
processing_job_name must be unique within the account — append a timestamp or UUID for rerunnable jobs.
For notebook execution via papermill, use AWSSageMakerRunNotebook instead.
"""
