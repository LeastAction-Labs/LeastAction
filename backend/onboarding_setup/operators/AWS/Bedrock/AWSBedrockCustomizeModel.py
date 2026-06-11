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
AWS Bedrock CustomizeModel Operator

Starts a Bedrock model customization (fine-tuning) job. Async.
Auth priority: explicit keys → assume IAM role → default credential chain.
"""

import json

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from src.common.logger.logger import log_error, log_info


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_bedrock_client(connection: dict):
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
        return session.client("bedrock")

    # Case 2: Assume IAM role via STS
    if assume_role_arn:
        log_info("task", "initialize", "auth_assume_role", f"Assuming IAM role: {assume_role_arn}")
        sts = boto3.client("sts", region_name=region)
        assumed = sts.assume_role(RoleArn=assume_role_arn, RoleSessionName="leastaction_session")
        creds = assumed["Credentials"]
        session = boto3.Session(aws_access_key_id=creds["AccessKeyId"],
                                aws_secret_access_key=creds["SecretAccessKey"],
                                aws_session_token=creds["SessionToken"], region_name=region)
        return session.client("bedrock")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info("task", "initialize", "auth_default",
             "Using default AWS credential chain (instance profile / ECS task role / env / config)")
    session = boto3.Session(region_name=region)
    return session.client("bedrock")


# ---------------------------------------------------------------------------
# Operator methods
# ---------------------------------------------------------------------------

def initialize(least_action_task_object):
    """
    Build and verify the Bedrock boto3 client.
    Returns: boto3 bedrock client
    """
    try:
        connection = least_action_task_object.get("connection", {})
        task_laui = least_action_task_object.get("laui")
        log_info("task", "initialize", "start", f"Initializing AWSBedrockCustomizeModel for task: {task_laui}")
        client = _build_bedrock_client(connection)
        region = connection.get("region", "us-east-1")
        log_info("task", "initialize", "verify_connection", f"Verifying connectivity in region: {region}")
        client.list_foundation_models(maxResults=1)
        log_info("task", "initialize", "connection_established", f"Bedrock client ready for region: {region}")
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
    Starts a Bedrock model customization (fine-tuning) job.

    Payload fields:
        job_name                (str, required)  -- Unique name for the customization job
        custom_model_name       (str, required)  -- Name for the resulting custom model
        role_arn                (str, required)  -- IAM role ARN with Bedrock permissions
        base_model_identifier   (str, required)  -- Base model ARN or ID to fine-tune
        training_data_config    (dict, required) -- {"s3Uri": "s3://bucket/prefix/"}
        output_data_config      (dict, required) -- {"s3Uri": "s3://bucket/output/"}
        validation_data_config  (dict, optional) -- Validation dataset configuration
        hyper_parameters        (dict, optional) -- Training hyperparameters
        customization_type      (str, optional)  -- default "FINE_TUNING"
        client_request_token    (str, optional)  -- Idempotency token
        tags                    (list, optional) -- List of {key, value} tag dicts

    Returns:
        dict with status, execution_type, result
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

        job_name = payload.get("job_name")
        custom_model_name = payload.get("custom_model_name")
        role_arn = payload.get("role_arn")
        base_model_identifier = payload.get("base_model_identifier")
        training_data_config = payload.get("training_data_config")
        output_data_config = payload.get("output_data_config")

        for field, val in [("job_name", job_name), ("custom_model_name", custom_model_name),
                            ("role_arn", role_arn), ("base_model_identifier", base_model_identifier),
                            ("training_data_config", training_data_config),
                            ("output_data_config", output_data_config)]:
            if not val:
                log_error("task", "run", "validation_error", f"{field} is required")
                return {"status": "failed", "execution_type": "async", "result": None,
                        "error": f"{field} is required"}

        kwargs = {
            "jobName": job_name,
            "customModelName": custom_model_name,
            "roleArn": role_arn,
            "baseModelIdentifier": base_model_identifier,
            "trainingDataConfig": training_data_config,
            "outputDataConfig": output_data_config,
            "customizationType": payload.get("customization_type", "FINE_TUNING"),
        }
        if payload.get("validation_data_config"):
            kwargs["validationDataConfig"] = payload["validation_data_config"]
        if payload.get("hyper_parameters"):
            kwargs["hyperParameters"] = payload["hyper_parameters"]
        if payload.get("client_request_token"):
            kwargs["clientRequestToken"] = payload["client_request_token"]
        if payload.get("tags"):
            kwargs["tags"] = payload["tags"]

        log_info("task", "run", "starting_customization_job", f"Starting model customization job: {job_name}")
        response = client.create_model_customization_job(**kwargs)
        job_arn = response.get("jobArn", "")
        log_info("task", "run", "customization_job_started", f"Customization job started: {job_arn}")

        return {"status": "pending", "execution_type": "async",
                "result": {"job_arn": job_arn, "job_name": job_name, "custom_model_name": custom_model_name}}

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "client_error", f"AWS ClientError ({error_code}): {error_msg}")
        return {"status": "failed", "execution_type": "async", "result": None, "error": f"{error_code}: {error_msg}"}
    except Exception as e:
        log_error("task", "run", "unexpected_error", f"Unexpected error during run: {str(e)}")
        return {"status": "failed", "execution_type": "async", "result": None, "error": str(e)}


def check_completion(least_action_task_object, client, run_details):
    """
    Polls the customization job status until Completed, Failed, or Stopped.
    Returns: dict with status (success|pending|failed), message, output
    """
    if run_details.get("status") == "failed":
        log_error("task", "check_completion", "run_phase_failed", f"Run phase reported failure: {run_details.get('error')}")
        return {"status": "failed", "message": f"Customization job failed to start: {run_details.get('error')}", "output": None}

    job_arn = run_details.get("result", {}).get("job_arn")
    if not job_arn:
        return {"status": "failed", "message": "No job_arn in run_details", "output": None}

    try:
        response = client.get_model_customization_job(jobIdentifier=job_arn)
        aws_status = response.get("status", "Unknown")
        log_info("task", "check_completion", "job_status", f"Customization job {job_arn} status: {aws_status}")

        if aws_status == "Completed":
            return {"status": "success", "message": "Model customization job completed successfully",
                    "output": {"job_arn": job_arn, "custom_model_arn": response.get("outputModelArn", ""),
                               "status": aws_status}}
        elif aws_status in ("Failed", "Stopped"):
            failure_reason = response.get("failureMessage", "Unknown")
            return {"status": "failed", "message": f"Customization job {aws_status}: {failure_reason}",
                    "output": {"job_arn": job_arn, "status": aws_status}}
        else:
            return {"status": "pending", "message": f"Customization job status: {aws_status}", "output": {}}

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "check_completion", "client_error", f"AWS ClientError ({error_code}): {error_msg}")
        return {"status": "failed", "message": f"{error_code}: {error_msg}", "output": None}
    except Exception as e:
        log_error("task", "check_completion", "unexpected_error", f"Unexpected error: {str(e)}")
        return {"status": "failed", "message": str(e), "output": None}


def finish(least_action_task_object, client, completion_details, run_details):
    """
    Log final outcome and release any held resources.
    Returns: None
    """
    try:
        task_laui = least_action_task_object.get("laui")
        log_info("task", "finish", "starting_cleanup", f"Starting cleanup for task: {task_laui}")
        final_status = completion_details.get("status", "unknown")
        log_info("task", "finish", "final_status", f"Task ended with status: {final_status}")
        if client:
            try:
                client.close()
                log_info("task", "finish", "client_closed", "Bedrock boto3 client closed successfully")
            except Exception as close_error:
                log_error("task", "finish", "client_close_error", f"Error closing client: {str(close_error)}")
        if final_status == "success":
            output = completion_details.get("output", {})
            log_info("task", "finish", "operation_summary",
                     f"Model customization job {output.get('job_arn', 'unknown')} completed successfully")
        elif final_status == "failed":
            log_error("task", "finish", "operation_failed", f"Operation failed: {completion_details.get('message')}")
        else:
            log_info("task", "finish", "operation_status",
                     f"status={final_status}, message={completion_details.get('message')}")
        log_info("task", "finish", "cleanup_complete", f"Cleanup complete for task: {task_laui}")
    except Exception as e:
        log_error("task", "finish", "cleanup_error", f"Error during finish/cleanup: {str(e)}")
        # Never re-raise from finish
'''}

bashblock = {"main.sh": """#!/bin/bash
set -e
pip install boto3>=1.28.0
pip install botocore>=1.31.0
echo "Dependencies installed successfully"
"""}

connection = {"region": "us-east-1"}

payload = {
    "job_name": "my-finetune-job",                              # required
    "custom_model_name": "my-custom-model",                     # required
    "role_arn": "arn:aws:iam::123456789012:role/BedrockRole",   # required
    "base_model_identifier": "amazon.titan-text-lite-v1",       # required
    "training_data_config": {"s3Uri": "s3://my-bucket/train/"}, # required
    "output_data_config": {"s3Uri": "s3://my-bucket/output/"},  # required
    # "validation_data_config": {"validators": [{"s3Uri": "s3://my-bucket/val/"}]},           # optional
    # "hyper_parameters": {"epochCount": "3", "batchSize": "8", "learningRate": "0.00001"},   # optional
    # "customization_type": "FINE_TUNING",                      # optional — default "FINE_TUNING"
    # "client_request_token": "unique-token-123",               # optional — idempotency token
    # "tags": [{"key": "project", "value": "my-project"}],      # optional
}

prompt = (
    "Starts a Bedrock model customization (fine-tuning) job. Async — polls until Completed/Failed/Stopped. "
    "Provide job_name, custom_model_name, role_arn, base_model_identifier, "
    "training_data_config ({s3Uri}), output_data_config ({s3Uri}). "
    "Optional: validation_data_config, hyper_parameters, customization_type, client_request_token, tags."
)

install_docs = """## Dependencies
- boto3>=1.28.0
- botocore>=1.31.0

## IAM Permissions Required
- bedrock:CreateModelCustomizationJob
- bedrock:GetModelCustomizationJob
- bedrock:ListFoundationModels
- iam:PassRole on the role_arn
- s3:GetObject on training data bucket
- s3:PutObject on output bucket
"""

guide_docs = """## What it does

Starts an AWS Bedrock model customization job (fine-tuning or continued pre-training) using the bedrock API. The call returns immediately with a job ARN — the operator then polls `get_model_customization_job` in `check_completion` until the status reaches `Completed`, `Failed`, or `Stopped`. Fine-tuning jobs can take several hours depending on dataset size and the base model.

---

## Auth

1. **Explicit credentials** — set `aws_access_key_id` and `aws_secret_access_key` in the connection. An optional `aws_session_token` can be included for temporary credentials.
2. **Assume IAM role** — set `assume_iam_role` in the connection with a role ARN. The operator uses STS to assume the role and build a scoped session before calling bedrock.
3. **Default credential chain** — leave all credential fields blank. boto3 resolves credentials automatically via environment variables, `~/.aws/credentials`, EC2 instance profile, or ECS task role.

---

## Connection

**Scenario 1: Explicit access key**
```json
{
  "region": "us-east-1",
  "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
  "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
}
```

**Scenario 2: Assume IAM role via STS**
```json
{
  "region": "us-east-1",
  "assume_iam_role": "arn:aws:iam::123456789012:role/BedrockCustomizeRole"
}
```

**Scenario 3: Default credential chain (EC2 / ECS / env)**
```json
{
  "region": "us-east-1"
}
```

| Field                 | Required | Description                                      |
|-----------------------|----------|--------------------------------------------------|
| region                | Yes      | AWS region where the customization job will run  |
| aws_access_key_id     | No       | Explicit access key (use with secret_access_key) |
| aws_secret_access_key | No       | Explicit secret key                              |
| aws_session_token     | No       | Session token for temporary credentials          |
| assume_iam_role       | No       | IAM role ARN to assume via STS                   |

---

## Payload

| Field                    | Required | Description                                                                        |
|--------------------------|----------|------------------------------------------------------------------------------------|
| job_name                 | Yes      | Unique name for the customization job                                              |
| custom_model_name        | Yes      | Name for the resulting custom model                                                |
| role_arn                 | Yes      | IAM role ARN with Bedrock, S3, and iam:PassRole permissions                        |
| base_model_identifier    | Yes      | Base model ARN or ID to fine-tune (e.g. `amazon.titan-text-lite-v1`)               |
| training_data_config     | Yes      | S3 location of training data — `{"s3Uri": "s3://bucket/prefix/"}`                 |
| output_data_config       | Yes      | S3 location for job output — `{"s3Uri": "s3://bucket/output/"}`                   |
| validation_data_config   | No       | Validation dataset configuration (same s3Uri format)                              |
| hyper_parameters         | No       | Training hyperparameters dict — e.g. `{"epochCount": "3", "batchSize": "8"}`      |
| customization_type       | No       | `FINE_TUNING` (default) or `CONTINUED_PRE_TRAINING`                               |
| client_request_token     | No       | Idempotency token — safe to resubmit if the network fails                         |
| tags                     | No       | List of `{"key": "...", "value": "..."}` tag pairs                                |

---

## Output (on success)

```json
{
  "job_arn": "arn:aws:bedrock:us-east-1:123456789012:model-customization-job/my-finetune-job",
  "custom_model_arn": "arn:aws:bedrock:us-east-1:123456789012:custom-model/my-custom-model",
  "status": "Completed"
}
```

| Field            | Description                                             |
|------------------|---------------------------------------------------------|
| job_arn          | ARN of the customization job                            |
| custom_model_arn | ARN of the newly created custom model                   |
| status           | Final AWS job status (`Completed`)                      |

---

## Scenarios and Edge Cases

**Base model not customizable** — Not all foundation models support fine-tuning. Submitting an unsupported `base_model_identifier` will cause an immediate error. Check the Bedrock console under "Custom models" for the list of customizable models.

**Training data format** — Training data must be a JSONL file where each line is a JSON object with `prompt` and `completion` fields. The exact schema may vary by model — verify against the AWS Bedrock customization documentation for your chosen base model.

**Job takes hours** — Fine-tuning large datasets on large models can take several hours. Set LeastAction task timeouts accordingly. The async polling loop handles this automatically.

**Idempotency** — Use `client_request_token` to make the job submission safe to retry. Bedrock will return the existing job ARN if the same token is submitted again.

---

## What this operator does NOT do

- Does not prepare or validate training data — input JSONL must already exist in S3 in the correct format
- Does not deploy the custom model to a provisioned throughput endpoint — use the Bedrock console or a separate operator after the job completes
"""

description = """Starts a Bedrock model customization (fine-tuning) job from training data in S3. Async — polls until Completed, Failed, or Stopped."""

publisher = "LeastActionLabs"
metadata = {"service": "Bedrock", "category": "AI/ML", "tags": ["bedrock", "fine-tuning", "customization", "aws"],
            "airflow_equivalent": "BedrockCustomizeModelOperator"}
version_details = {"version": "0.0.0", "core": ["0.*"]}
verified = False
status = "draft"
publisher_notes = """## Notes\n\nThis operator has been reviewed and tested by LeastActionLabs.\n"""
