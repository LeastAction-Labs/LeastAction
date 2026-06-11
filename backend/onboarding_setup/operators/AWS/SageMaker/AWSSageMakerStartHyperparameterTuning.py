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
AWS SageMaker Start Hyperparameter Tuning Operator

Starts a SageMaker hyperparameter tuning job to find optimal model hyperparameters. Async.
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
                 f"Initializing AWSSageMakerStartHyperparameterTuning for task: {task_laui}")
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
    Starts a SageMaker hyperparameter tuning job.

    Payload fields:
        tuning_job_name                     (str, required)   -- unique name for the tuning job
        hyper_parameter_tuning_job_config   (dict, required)  -- config with Strategy, Objective, ResourceLimits, ParameterRanges
        training_job_definition             (dict, required)  -- full training job definition dict
        tags                                (list, optional)  -- list of {"Key": ..., "Value": ...} dicts
        warm_start_config                   (dict, optional)  -- transfer learning from previous tuning job

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

        tuning_job_name = payload.get("tuning_job_name")
        tuning_config = payload.get("hyper_parameter_tuning_job_config")
        training_job_definition = payload.get("training_job_definition")

        for field, val in [("tuning_job_name", tuning_job_name),
                           ("hyper_parameter_tuning_job_config", tuning_config),
                           ("training_job_definition", training_job_definition)]:
            if not val:
                log_error("task", "run", "validation_error", f"Required field missing: {field}")
                return {"status": "failed", "execution_type": "async", "result": None,
                        "error": f"Required field missing: {field}"}

        kwargs = {
            "HyperParameterTuningJobName": tuning_job_name,
            "HyperParameterTuningJobConfig": tuning_config,
            "TrainingJobDefinition": training_job_definition,
        }
        if payload.get("tags"):
            kwargs["Tags"] = payload["tags"]
        if payload.get("warm_start_config"):
            kwargs["WarmStartConfig"] = payload["warm_start_config"]

        strategy = tuning_config.get("Strategy", "Unknown")
        max_jobs = tuning_config.get("ResourceLimits", {}).get("MaxNumberOfTrainingJobs", "?")
        log_info("task", "run", "starting_tuning_job",
                 f"Starting HPO tuning job: {tuning_job_name} strategy={strategy} max_jobs={max_jobs}")
        response = client.create_hyper_parameter_tuning_job(**kwargs)
        tuning_job_arn = response.get("HyperParameterTuningJobArn", "")
        log_info("task", "run", "tuning_job_started",
                 f"HPO tuning job started. ARN: {tuning_job_arn}")

        return {"status": "pending", "execution_type": "async",
                "result": {"tuning_job_name": tuning_job_name,
                           "tuning_job_arn": tuning_job_arn}}
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
    """Poll describe_hyper_parameter_tuning_job until Completed, Failed, or Stopped."""
    if run_details.get("status") == "failed":
        log_error("task", "check_completion", "run_phase_failed",
                  f"Run phase reported failure: {run_details.get('error')}")
        return {"status": "failed",
                "message": f"Run phase failed: {run_details.get('error')}",
                "output": None}
    try:
        tuning_job_name = (run_details.get("result") or {}).get("tuning_job_name")
        if not tuning_job_name:
            return {"status": "failed", "message": "No tuning_job_name in run_details", "output": None}

        response = client.describe_hyper_parameter_tuning_job(
            HyperParameterTuningJobName=tuning_job_name)
        job_status = response.get("HyperParameterTuningJobStatus", "Unknown")
        counters = response.get("TrainingJobStatusCounters", {})
        completed_count = counters.get("Completed", 0)
        total_count = counters.get("Completed", 0) + counters.get("InProgress", 0) + counters.get("Pending", 0)
        log_info("task", "check_completion", "tuning_status",
                 f"Tuning job {tuning_job_name} status: {job_status} "
                 f"completed: {completed_count}/{total_count}")

        if job_status == "Completed":
            best_training_job = response.get("BestTrainingJob", {})
            return {"status": "success",
                    "message": f"Tuning job {tuning_job_name} completed successfully",
                    "output": {"tuning_job_name": tuning_job_name,
                               "tuning_job_arn": (run_details.get("result") or {}).get("tuning_job_arn", ""),
                               "job_status": job_status,
                               "best_training_job": best_training_job,
                               "training_jobs_completed": completed_count}}
        elif job_status == "Failed":
            failure_reason = response.get("FailureReason", "Unknown")
            return {"status": "failed",
                    "message": f"Tuning job failed: {failure_reason}",
                    "output": {"tuning_job_name": tuning_job_name,
                               "failure_reason": failure_reason}}
        elif job_status == "Stopped":
            return {"status": "failed",
                    "message": f"Tuning job {tuning_job_name} was stopped",
                    "output": {"tuning_job_name": tuning_job_name}}
        return {"status": "pending",
                "message": (f"Tuning job {tuning_job_name} is {job_status}. "
                            f"Completed: {completed_count}/{total_count} training jobs"),
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
            best = output.get("best_training_job", {})
            log_info("task", "finish", "operation_summary",
                     f"Tuning job {output.get('tuning_job_name')} completed. "
                     f"Best training job: {best.get('TrainingJobName', 'N/A')} "
                     f"Completed: {output.get('training_jobs_completed')} jobs")
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
    "tuning_job_name": "my-hpo-job",
    "hyper_parameter_tuning_job_config": {
        "Strategy": "Bayesian",
        "HyperParameterTuningJobObjective": {
            "Type": "Maximize",
            "MetricName": "validation:accuracy"
        },
        "ResourceLimits": {
            "MaxNumberOfTrainingJobs": 10,
            "MaxParallelTrainingJobs": 2
        },
        "ParameterRanges": {
            "ContinuousParameterRanges": [
                {"Name": "learning_rate", "MinValue": "0.001", "MaxValue": "0.1", "ScalingType": "Logarithmic"}
            ],
            "IntegerParameterRanges": [
                {"Name": "num_layers", "MinValue": "1", "MaxValue": "5", "ScalingType": "Auto"}
            ]
        }
    },
    "training_job_definition": {
        "AlgorithmSpecification": {
            "TrainingImage": "683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-xgboost:1.5-1",
            "TrainingInputMode": "File"
        },
        "RoleArn": "arn:aws:iam::123456789012:role/SageMakerExecutionRole",
        "OutputDataConfig": {"S3OutputPath": "s3://my-bucket/hpo-output/"},
        "ResourceConfig": {"InstanceType": "ml.m5.xlarge", "InstanceCount": 1, "VolumeSizeInGB": 10},
        "StoppingCondition": {"MaxRuntimeInSeconds": 3600}
    }
}

prompt = (
    "Starts a SageMaker hyperparameter tuning job and polls until Completed/Failed/Stopped. "
    "Provide tuning_job_name, hyper_parameter_tuning_job_config (Strategy, Objective, ResourceLimits, ParameterRanges), "
    "training_job_definition. Optional: tags, warm_start_config. "
    "Returns best_training_job on success. Async."
)

install_docs = """## Dependencies
- boto3>=1.28.0
- botocore>=1.31.0

## IAM Permissions Required
- sagemaker:CreateHyperParameterTuningJob
- sagemaker:DescribeHyperParameterTuningJob
- iam:PassRole (on role in training_job_definition)
"""

guide_docs = """## What it does

Starts a SageMaker hyperparameter tuning job that spawns multiple training jobs in parallel to find the optimal set of hyperparameters for a model. The tuning job uses Bayesian or Random strategy to explore the hyperparameter search space defined in the config, evaluates each trial against an objective metric, and reports the best training job on completion. This operator is async and polls until the tuning job reaches Completed, Failed, or Stopped.

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

| Field                              | Required | Description                                                                    |
|------------------------------------|----------|--------------------------------------------------------------------------------|
| tuning_job_name                    | Yes      | Unique name for the hyperparameter tuning job                                  |
| hyper_parameter_tuning_job_config  | Yes      | Dict with Strategy, HyperParameterTuningJobObjective, ResourceLimits, ParameterRanges |
| training_job_definition            | Yes      | Full training job definition dict (AlgorithmSpecification, RoleArn, OutputDataConfig, ResourceConfig, StoppingCondition) |
| tags                               | No       | List of {"Key": ..., "Value": ...} dicts                                       |
| warm_start_config                  | No       | Dict for warm starting from a previous tuning job's results                    |

---

## Output (on success)

    {
      "tuning_job_name": "my-hpo-job",
      "tuning_job_arn": "arn:aws:sagemaker:us-east-1:123456789012:hyper-parameter-tuning-job/my-hpo-job",
      "job_status": "Completed",
      "best_training_job": {
        "TrainingJobName": "my-hpo-job-001-abc123",
        "FinalHyperParameterTuningJobObjectiveMetric": {"MetricName": "validation:accuracy", "Value": 0.95}
      },
      "training_jobs_completed": 10
    }

| Field                    | Description                                                           |
|--------------------------|-----------------------------------------------------------------------|
| tuning_job_name          | Name of the completed tuning job                                      |
| tuning_job_arn           | Full ARN of the tuning job                                            |
| job_status               | Final job status — Completed on success                               |
| best_training_job        | Dict with the best training job name and its objective metric value   |
| training_jobs_completed  | Total number of training jobs that completed during tuning            |

---

## Scenarios and Edge Cases

Job name not unique:
  tuning_job_name must be unique within the account. AWS raises ValidationException if the name is already in use. Append a timestamp or UUID for rerunnable pipelines.

Bayesian vs Random strategy trade-offs:
  Bayesian strategy learns from previous trials and focuses exploration on promising hyperparameter regions — recommended for most use cases as it requires fewer trials. Random strategy independently samples from the search space — useful when trials are very fast or when parallelism is high enough to explore broadly.

Warm start from previous job:
  warm_start_config with WarmStartType "IDENTICAL_DATA_AND_ALGORITHM" transfers prior tuning knowledge to continue exploration, reducing the number of trials needed to reach a good result.

---

## What this operator does NOT do

- Does not deploy the best model to an endpoint — use the best_training_job output to retrieve model artifacts and create a deployment.
- Does not clean up individual training jobs spawned by the tuning job — those remain in SageMaker until deleted.
- Does not validate that the MetricName in the objective matches what the training script logs.
"""

description = (
    "Starts a SageMaker hyperparameter tuning job that spawns multiple training jobs to find "
    "optimal hyperparameters. Returns best_training_job on completion. Async."
)

publisher = "LeastActionLabs"

metadata = {
    "service": "SageMaker",
    "category": "ML",
    "tags": ["sagemaker", "hyperparameter-tuning", "training", "optimization", "aws"],
    "airflow_equivalent": "SageMakerTuningOperator",
}

version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False
status = "draft"

publisher_notes = """## Publisher Notes

Hyperparameter tuning spawns multiple training jobs — each incurs compute costs. Set MaxNumberOfTrainingJobs conservatively for initial testing.
Bayesian strategy is recommended over Random for most use cases: it learns from previous trial results to focus on promising hyperparameter ranges, reducing the number of trials needed.
warm_start_config enables warm starting from a previous tuning job — use WarmStartType: "IDENTICAL_DATA_AND_ALGORITHM" or "TRANSFER_LEARNING" to carry over prior knowledge.
The MetricName in HyperParameterTuningJobObjective must match exactly what the training script logs to stdout or CloudWatch (via MetricDefinitions in the training job spec).
best_training_job in the output contains TrainingJobName and FinalHyperParameterTuningJobObjectiveMetric — use TrainingJobName to retrieve the model artifacts.
tuning_job_name must be unique within the account.
"""
