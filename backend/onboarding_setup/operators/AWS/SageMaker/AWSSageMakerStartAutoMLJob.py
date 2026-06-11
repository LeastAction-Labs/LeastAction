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
AWS SageMaker Start AutoML Job Operator

Starts a SageMaker Autopilot AutoML job for automated algorithm and hyperparameter discovery. Async.
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
                 f"Initializing AWSSageMakerStartAutoMLJob for task: {task_laui}")
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
    Starts a SageMaker Autopilot AutoML job.

    Payload fields:
        auto_ml_job_name        (str, required)   -- unique name for the AutoML job
        input_data_config       (list, required)  -- list of input data source dicts with TargetAttributeName
        output_data_config      (dict, required)  -- {"S3OutputPath": "s3://..."}
        role_arn                (str, required)   -- IAM execution role ARN
        problem_type            (str, optional)   -- BinaryClassification/MulticlassClassification/Regression
        auto_ml_job_objective   (dict, optional)  -- {"MetricName": "F1"|"Accuracy"|"MSE"|"RMSE"|"MAE"|"R2"}
        generate_candidate_definitions_only (bool, optional) -- only generate candidates, don't train (default: False)
        tags                    (list, optional)  -- list of {"Key": ..., "Value": ...} dicts

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

        auto_ml_job_name = payload.get("auto_ml_job_name")
        input_data_config = payload.get("input_data_config")
        output_data_config = payload.get("output_data_config")
        role_arn = payload.get("role_arn")

        for field, val in [("auto_ml_job_name", auto_ml_job_name),
                           ("input_data_config", input_data_config),
                           ("output_data_config", output_data_config),
                           ("role_arn", role_arn)]:
            if not val:
                log_error("task", "run", "validation_error", f"Required field missing: {field}")
                return {"status": "failed", "execution_type": "async", "result": None,
                        "error": f"Required field missing: {field}"}

        kwargs = {
            "AutoMLJobName": auto_ml_job_name,
            "InputDataConfig": input_data_config,
            "OutputDataConfig": output_data_config,
            "RoleArn": role_arn,
        }
        if payload.get("problem_type"):
            kwargs["ProblemType"] = payload["problem_type"]
        if payload.get("auto_ml_job_objective"):
            kwargs["AutoMLJobObjective"] = payload["auto_ml_job_objective"]
        if payload.get("generate_candidate_definitions_only") is not None:
            kwargs["GenerateCandidateDefinitionsOnly"] = bool(
                payload["generate_candidate_definitions_only"])
        if payload.get("tags"):
            kwargs["Tags"] = payload["tags"]

        log_info("task", "run", "starting_automl_job",
                 f"Starting AutoML job: {auto_ml_job_name} role={role_arn}")
        response = client.create_auto_ml_job(**kwargs)
        auto_ml_job_arn = response.get("AutoMLJobArn", "")
        log_info("task", "run", "automl_job_started",
                 f"AutoML job started. ARN: {auto_ml_job_arn}")

        return {"status": "pending", "execution_type": "async",
                "result": {"auto_ml_job_name": auto_ml_job_name,
                           "auto_ml_job_arn": auto_ml_job_arn}}
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
    """Poll describe_auto_ml_job until Completed, Failed, or Stopped."""
    if run_details.get("status") == "failed":
        log_error("task", "check_completion", "run_phase_failed",
                  f"Run phase reported failure: {run_details.get('error')}")
        return {"status": "failed",
                "message": f"Run phase failed: {run_details.get('error')}",
                "output": None}
    try:
        auto_ml_job_name = (run_details.get("result") or {}).get("auto_ml_job_name")
        if not auto_ml_job_name:
            return {"status": "failed", "message": "No auto_ml_job_name in run_details", "output": None}

        response = client.describe_auto_ml_job(AutoMLJobName=auto_ml_job_name)
        job_status = response.get("AutoMLJobStatus", "Unknown")
        secondary_status = response.get("AutoMLJobSecondaryStatus", "")
        log_info("task", "check_completion", "automl_status",
                 f"AutoML job {auto_ml_job_name} status: {job_status} secondary: {secondary_status}")

        if job_status == "Completed":
            best_candidate = response.get("BestCandidate", {})
            return {"status": "success",
                    "message": f"AutoML job {auto_ml_job_name} completed successfully",
                    "output": {"auto_ml_job_name": auto_ml_job_name,
                               "auto_ml_job_arn": (run_details.get("result") or {}).get("auto_ml_job_arn", ""),
                               "job_status": job_status,
                               "best_candidate": best_candidate}}
        elif job_status == "Failed":
            failure_reason = response.get("FailureReason", "Unknown")
            return {"status": "failed",
                    "message": f"AutoML job failed: {failure_reason}",
                    "output": {"auto_ml_job_name": auto_ml_job_name,
                               "failure_reason": failure_reason}}
        elif job_status == "Stopped":
            return {"status": "failed",
                    "message": f"AutoML job {auto_ml_job_name} was stopped",
                    "output": {"auto_ml_job_name": auto_ml_job_name}}
        return {"status": "pending",
                "message": f"AutoML job {auto_ml_job_name} is {job_status} ({secondary_status})",
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
            best = output.get("best_candidate", {})
            log_info("task", "finish", "operation_summary",
                     f"AutoML job {output.get('auto_ml_job_name')} completed. "
                     f"Best candidate: {best.get('CandidateName', 'N/A')}")
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
    "auto_ml_job_name": "my-automl-job",
    "role_arn": "arn:aws:iam::123456789012:role/SageMakerExecutionRole",
    "input_data_config": [
        {
            "DataSource": {
                "S3DataSource": {
                    "S3DataType": "S3Prefix",
                    "S3Uri": "s3://my-bucket/train/"
                }
            },
            "TargetAttributeName": "label"
        }
    ],
    "output_data_config": {"S3OutputPath": "s3://my-bucket/automl-output/"},
    # "problem_type": "BinaryClassification",    # optional, auto-detected if omitted
    # "auto_ml_job_objective": {"MetricName": "F1"},  # optional
    # "generate_candidate_definitions_only": False,   # optional
}

prompt = (
    "Starts a SageMaker Autopilot AutoML job that automatically discovers the best algorithm "
    "and hyperparameters for a tabular dataset. "
    "Provide auto_ml_job_name, role_arn, input_data_config (list with TargetAttributeName), "
    "output_data_config. "
    "Optional: problem_type (BinaryClassification/MulticlassClassification/Regression), "
    "auto_ml_job_objective (dict), generate_candidate_definitions_only (bool), tags. "
    "Dataset must have at least 500 rows. Async — polls until Completed/Failed/Stopped."
)

install_docs = """## Dependencies
- boto3>=1.28.0
- botocore>=1.31.0

## IAM Permissions Required
- sagemaker:CreateAutoMLJob
- sagemaker:DescribeAutoMLJob
- iam:PassRole (on role_arn)
- s3:GetObject (on input data bucket)
- s3:PutObject (on output bucket)

## Prerequisites
- Dataset must have minimum 500 rows (AWS hard requirement)
- CSV must have a header row with TargetAttributeName as one of the column names
"""

guide_docs = """## What it does

Starts a SageMaker Autopilot AutoML job that automatically explores multiple algorithms and hyperparameter configurations to find the best model for a tabular dataset. Autopilot reads input data from S3, runs many trial training jobs internally, and reports the best candidate upon completion. This operator is async and polls until the job reaches Completed, Failed, or Stopped.

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
| auto_ml_job_name                   | Yes      | Unique name for the AutoML job (account + region scoped)                       |
| input_data_config                  | Yes      | List of input data source dicts — each must include TargetAttributeName        |
| output_data_config                 | Yes      | Dict with S3OutputPath for storing AutoML results                              |
| role_arn                           | Yes      | IAM execution role ARN for the AutoML job                                      |
| problem_type                       | No       | BinaryClassification, MulticlassClassification, or Regression (auto-detected)  |
| auto_ml_job_objective              | No       | Dict with MetricName — e.g. {"MetricName": "F1"} or {"MetricName": "Accuracy"} |
| generate_candidate_definitions_only| No       | Bool — only generate candidate definitions without training (default: False)    |
| tags                               | No       | List of {"Key": ..., "Value": ...} dicts                                       |

---

## Output (on success)

    {
      "auto_ml_job_name": "my-automl-job",
      "auto_ml_job_arn": "arn:aws:sagemaker:us-east-1:123456789012:automl-job/my-automl-job",
      "job_status": "Completed",
      "best_candidate": {
        "CandidateName": "...",
        "InferenceContainers": [...],
        "CandidateSteps": [...]
      }
    }

| Field             | Description                                                           |
|-------------------|-----------------------------------------------------------------------|
| auto_ml_job_name  | Name of the completed AutoML job                                      |
| auto_ml_job_arn   | Full ARN of the AutoML job                                            |
| job_status        | Final job status — Completed on success                               |
| best_candidate    | Dict with the winning candidate's name, containers, and steps         |

---

## Scenarios and Edge Cases

Job name not unique (ValidationException):
  auto_ml_job_name must be unique within the account and region. AWS raises ValidationException if the name is already in use. Append a timestamp or UUID for rerunnable pipelines.

Problem type auto-detected if not specified:
  If problem_type is omitted, Autopilot infers it from the target column values — binary labels map to BinaryClassification, integers to MulticlassClassification, and floats to Regression. Provide it explicitly for predictable behavior.

Large dataset equals long runtime (hours):
  Autopilot runs many trial training jobs internally. For large datasets or high MaxCandidates limits, jobs can take several hours. Use auto_ml_job_objective to guide the search and set a MaxCandidates limit in AutoMLJobConfig to control cost and runtime.

---

## What this operator does NOT do

- Does not deploy the best model automatically — use the best_candidate output to create a model and deploy it with AWSSageMakerCreateEndpoint.
- Does not clean up trial training jobs spawned during the AutoML process.
- Does not enforce a minimum dataset size check before submitting — AWS raises ValidationException if the dataset has fewer than 500 rows.
"""

description = (
    "Starts a SageMaker Autopilot AutoML job that automatically discovers the best algorithm "
    "and hyperparameters. Returns best_candidate on completion. Async."
)

publisher = "LeastActionLabs"

metadata = {
    "service": "SageMaker",
    "category": "ML",
    "tags": ["sagemaker", "automl", "autopilot", "training", "aws"],
    "airflow_equivalent": "SageMakerAutoMLOperator",
}

version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False
status = "draft"

publisher_notes = """## Publisher Notes

Autopilot automatically explores multiple algorithms and hyperparameter settings — it runs many training jobs internally, so costs can add up for large datasets or high MaxCandidates limits.
The auto_ml_job_name must be unique within the account and region.
input_data_config TargetAttributeName must match a column name in the CSV header exactly (case-sensitive).
AWS enforces a hard minimum of 500 rows — the API returns ValidationException for smaller datasets.
Problem type is auto-detected from the target column if not specified: binary labels → BinaryClassification, integer labels → MulticlassClassification, float labels → Regression.
The best_candidate dict in the output contains CandidateName, InferenceContainers, and CandidateSteps — use this to deploy the winning model.
Completed Autopilot jobs can take 30 minutes to several hours depending on dataset size and the MaxCandidates limit in AutoMLJobConfig.
"""
