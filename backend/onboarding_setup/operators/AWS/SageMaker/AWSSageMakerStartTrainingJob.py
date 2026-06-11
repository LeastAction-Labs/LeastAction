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
AWS SageMaker Start Training Job Operator

Starts a SageMaker model training job and polls until completion. Async.
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
                 f"Initializing AWSSageMakerStartTrainingJob for task: {task_laui}")
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
    Starts a SageMaker training job.

    Payload fields:
        training_job_name           (str, required)   -- unique name for the training job
        role_arn                    (str, required)   -- IAM execution role ARN
        algorithm_specification     (dict, required)  -- {"TrainingImage": "...", "TrainingInputMode": "File"}
        output_data_config          (dict, required)  -- {"S3OutputPath": "s3://bucket/output/"}
        resource_config             (dict, required)  -- {"InstanceType": "ml.m5.xlarge", "InstanceCount": 1, "VolumeSizeInGB": 30}
        input_data_config           (list, optional)  -- list of input channel dicts
        hyper_parameters            (dict, optional)  -- hyperparameter key-value pairs (values auto-converted to str)
        stopping_condition          (dict, optional)  -- {"MaxRuntimeInSeconds": 3600}
        enable_network_isolation    (bool, optional)  -- isolate container from internet
        enable_inter_container_traffic_encryption (bool, optional) -- encrypt container-to-container traffic
        tags                        (list, optional)  -- list of {"Key": ..., "Value": ...} dicts

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

        training_job_name = payload.get("training_job_name")
        role_arn = payload.get("role_arn")
        algorithm_specification = payload.get("algorithm_specification")
        output_data_config = payload.get("output_data_config")
        resource_config = payload.get("resource_config")

        for field, val in [("training_job_name", training_job_name),
                           ("role_arn", role_arn),
                           ("algorithm_specification", algorithm_specification),
                           ("output_data_config", output_data_config),
                           ("resource_config", resource_config)]:
            if not val:
                log_error("task", "run", "validation_error", f"Required field missing: {field}")
                return {"status": "failed", "execution_type": "async", "result": None,
                        "error": f"Required field missing: {field}"}

        stopping_condition = payload.get("stopping_condition", {"MaxRuntimeInSeconds": 3600})
        kwargs = {
            "TrainingJobName": training_job_name,
            "RoleArn": role_arn,
            "AlgorithmSpecification": algorithm_specification,
            "OutputDataConfig": output_data_config,
            "ResourceConfig": resource_config,
            "StoppingCondition": stopping_condition,
        }
        if payload.get("input_data_config"):
            kwargs["InputDataConfig"] = payload["input_data_config"]
        if payload.get("hyper_parameters"):
            # All hyperparameter values must be strings
            kwargs["HyperParameters"] = {k: str(v) for k, v in payload["hyper_parameters"].items()}
        if payload.get("enable_network_isolation") is not None:
            kwargs["EnableNetworkIsolation"] = bool(payload["enable_network_isolation"])
        if payload.get("enable_inter_container_traffic_encryption") is not None:
            kwargs["EnableInterContainerTrafficEncryption"] = bool(
                payload["enable_inter_container_traffic_encryption"])
        if payload.get("tags"):
            kwargs["Tags"] = payload["tags"]

        instance_type = resource_config.get("InstanceType", "unknown")
        log_info("task", "run", "starting_training_job",
                 f"Starting training job: {training_job_name} instance={instance_type}")
        response = client.create_training_job(**kwargs)
        training_job_arn = response.get("TrainingJobArn", "")
        log_info("task", "run", "training_job_started",
                 f"Training job started. ARN: {training_job_arn}")

        return {"status": "pending", "execution_type": "async",
                "result": {"training_job_name": training_job_name,
                           "training_job_arn": training_job_arn}}
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
    """Poll describe_training_job until Completed, Failed, or Stopped."""
    if run_details.get("status") == "failed":
        log_error("task", "check_completion", "run_phase_failed",
                  f"Run phase reported failure: {run_details.get('error')}")
        return {"status": "failed",
                "message": f"Run phase failed: {run_details.get('error')}",
                "output": None}
    try:
        training_job_name = (run_details.get("result") or {}).get("training_job_name")
        if not training_job_name:
            return {"status": "failed", "message": "No training_job_name in run_details", "output": None}

        response = client.describe_training_job(TrainingJobName=training_job_name)
        job_status = response.get("TrainingJobStatus", "Unknown")
        secondary_status = response.get("SecondaryStatus", "")
        log_info("task", "check_completion", "training_status",
                 f"Training job {training_job_name} status: {job_status} secondary: {secondary_status}")

        if job_status == "Completed":
            model_artifacts_s3 = response.get("ModelArtifacts", {}).get("S3ModelArtifacts", "")
            billable_seconds = response.get("BillableTimeInSeconds", 0)
            return {"status": "success",
                    "message": f"Training job {training_job_name} completed successfully",
                    "output": {"training_job_name": training_job_name,
                               "training_job_arn": (run_details.get("result") or {}).get("training_job_arn", ""),
                               "model_artifacts_s3": model_artifacts_s3,
                               "billable_seconds": billable_seconds,
                               "job_status": job_status}}
        elif job_status == "Failed":
            failure_reason = response.get("FailureReason", "Unknown")
            return {"status": "failed",
                    "message": f"Training job failed: {failure_reason}",
                    "output": {"training_job_name": training_job_name,
                               "failure_reason": failure_reason}}
        elif job_status == "Stopped":
            return {"status": "failed",
                    "message": f"Training job {training_job_name} was stopped",
                    "output": {"training_job_name": training_job_name}}
        return {"status": "pending",
                "message": f"Training job {training_job_name} is {job_status} ({secondary_status})",
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
                     f"Training job {output.get('training_job_name')} completed. "
                     f"Model artifacts: {output.get('model_artifacts_s3')} "
                     f"Billable seconds: {output.get('billable_seconds')}")
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
    "training_job_name": "my-training-job",
    "role_arn": "arn:aws:iam::123456789012:role/SageMakerExecutionRole",
    "algorithm_specification": {
        "TrainingImage": "382416733822.dkr.ecr.us-east-1.amazonaws.com/linear-learner:1",
        "TrainingInputMode": "File"
    },
    "output_data_config": {"S3OutputPath": "s3://my-bucket/training-output/"},
    "resource_config": {
        "InstanceType": "ml.m5.xlarge",
        "InstanceCount": 1,
        "VolumeSizeInGB": 30
    },
    # "input_data_config": [...],           # optional
    # "hyper_parameters": {"lr": "0.01"},   # optional, values auto-converted to str
    # "stopping_condition": {"MaxRuntimeInSeconds": 3600},  # optional, default 3600s
}

prompt = (
    "Starts a SageMaker training job and polls until Completed/Failed/Stopped. "
    "Provide training_job_name, role_arn, algorithm_specification, output_data_config, resource_config. "
    "Optional: input_data_config, hyper_parameters (values auto-converted to str), "
    "stopping_condition (default 3600s), enable_network_isolation, "
    "enable_inter_container_traffic_encryption, tags. "
    "Returns model_artifacts_s3 and billable_seconds on completion. Async."
)

install_docs = """## Dependencies
- boto3>=1.28.0
- botocore>=1.31.0

## IAM Permissions Required
- sagemaker:CreateTrainingJob
- sagemaker:DescribeTrainingJob
- iam:PassRole (on role_arn)
- s3:GetObject (on input data buckets)
- s3:PutObject (on output bucket)

## Prerequisites
- Training image must be in the same region as the training job
- role_arn must trust sagemaker.amazonaws.com
"""

guide_docs = """## What it does

Starts a SageMaker model training job using a specified algorithm container and input data from S3. The training script runs inside the container on managed compute; upon completion the model artifacts are automatically uploaded to S3. The operator returns the S3 path to the model artifacts and the billable compute seconds. This operator is async and polls until the job reaches Completed, Failed, or Stopped.

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

| Field                                      | Required | Description                                                                 |
|--------------------------------------------|----------|-----------------------------------------------------------------------------|
| training_job_name                          | Yes      | Unique name for the training job                                            |
| role_arn                                   | Yes      | IAM execution role ARN for the training job                                 |
| algorithm_specification                    | Yes      | Dict with TrainingImage and TrainingInputMode ("File" or "Pipe")            |
| output_data_config                         | Yes      | Dict with S3OutputPath for storing model artifacts                          |
| resource_config                            | Yes      | Dict with InstanceType, InstanceCount, and VolumeSizeInGB                   |
| input_data_config                          | No       | List of input channel dicts pointing to S3 training data                    |
| hyper_parameters                           | No       | Dict of hyperparameter key-value pairs (values auto-converted to strings)   |
| stopping_condition                         | No       | {"MaxRuntimeInSeconds": N} — defaults to 3600 if not specified              |
| enable_network_isolation                   | No       | Bool — isolate the container from internet access                           |
| enable_inter_container_traffic_encryption  | No       | Bool — encrypt traffic between container nodes for distributed training     |
| tags                                       | No       | List of {"Key": ..., "Value": ...} dicts                                    |

---

## Output (on success)

    {
      "training_job_name": "my-training-job",
      "training_job_arn": "arn:aws:sagemaker:us-east-1:123456789012:training-job/my-training-job",
      "model_artifacts_s3": "s3://my-bucket/training-output/my-training-job/output/model.tar.gz",
      "billable_seconds": 120,
      "job_status": "Completed"
    }

| Field               | Description                                                             |
|---------------------|-------------------------------------------------------------------------|
| training_job_name   | Name of the completed training job                                      |
| training_job_arn    | Full ARN of the training job                                            |
| model_artifacts_s3  | S3 path to the model.tar.gz containing trained model weights            |
| billable_seconds    | Actual compute seconds billed for the training job                      |
| job_status          | Final job status — Completed on success                                 |

---

## Scenarios and Edge Cases

Job name not unique:
  training_job_name must be unique within the account. AWS raises ResourceInUse if the name already exists. Append a timestamp or UUID for rerunnable pipelines.

hyper_parameters values must be strings (auto-converted):
  The SageMaker API requires all hyperparameter values to be strings. This operator automatically converts non-string values (int, float, bool) to strings before submitting — no manual conversion needed.

Artifacts at output_data_config S3 path/job_name/output/model.tar.gz:
  Model artifacts are always written to output_data_config.S3OutputPath/<training_job_name>/output/model.tar.gz — SageMaker appends this path structure automatically. Use this path with AWSSageMakerCreateModel for deployment.

---

## What this operator does NOT do

- Does not deploy the trained model — use the model_artifacts_s3 path with AWSSageMakerCreateModel, then AWSSageMakerCreateEndpointConfig, then AWSSageMakerCreateEndpoint.
- Does not validate that the training image exists or is accessible in the region before submitting.
- Does not tune hyperparameters automatically — use AWSSageMakerStartHyperparameterTuning for automated hyperparameter search.
"""

description = (
    "Starts a SageMaker training job and polls asynchronously until completion. "
    "Returns model artifact S3 path and billable seconds on success."
)

publisher = "LeastActionLabs"

metadata = {
    "service": "SageMaker",
    "category": "ML",
    "tags": ["sagemaker", "training", "ml", "model", "aws"],
    "airflow_equivalent": "SageMakerTrainingOperator",
}

version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False
status = "draft"

publisher_notes = """## Publisher Notes

training_job_name must be unique within the account — append a timestamp or UUID for rerunnable pipelines.
hyper_parameters values are automatically converted to strings in this operator — the SageMaker API requires all hyperparameter values to be strings.
Model artifacts are automatically uploaded to output_data_config.S3OutputPath/<job_name>/output/model.tar.gz on completion — use this path with AWSSageMakerCreateModel for deployment.
stopping_condition.MaxRuntimeInSeconds is strongly recommended to cap maximum runtime and prevent unexpected cost overruns — default is 3600 seconds (1 hour).
For distributed training, set resource_config.InstanceCount > 1 — the training image must support distributed training (e.g. via Horovod, DeepSpeed, or PyTorch DDP).
The training image must be in the same region as the training job — cross-region image pulls are not supported.
enable_network_isolation=true prevents the container from making outbound network calls, which is useful for security-sensitive training workloads.
"""
