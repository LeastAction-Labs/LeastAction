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
AWSBedrockStartBatchInference operator.
Starts a Bedrock batch inference job to run model invocations on a large dataset stored in S3.
Async: polls until the job reaches Completed, Failed, Stopped, or Expired.
"""
import json
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from src.common.logger.logger import log_error, log_info


def _build_bedrock_client(connection):
    region = connection.get("region", "us-east-1")

    # Case 1: Explicit access key + secret provided in connection
    if connection.get("aws_access_key_id") and connection.get("aws_secret_access_key"):
        session = boto3.Session(
            aws_access_key_id=connection["aws_access_key_id"],
            aws_secret_access_key=connection["aws_secret_access_key"],
            aws_session_token=connection.get("aws_session_token"),
            region_name=region,
        )

    # Case 2: role_arn provided — assume role via STS then build session
    elif connection.get("role_arn"):
        base_session = boto3.Session(region_name=region)
        sts = base_session.client("sts")
        assumed = sts.assume_role(
            RoleArn=connection["role_arn"],
            RoleSessionName=connection.get("role_session_name", "LeastActionBedrockSession"),
        )
        creds = assumed["Credentials"]
        session = boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region,
        )

    # Case 3: Default credential chain (env vars, ~/.aws/credentials, instance profile, etc.)
    else:
        session = boto3.Session(region_name=region)

    return session.client("bedrock")


def initialize(connection, **kwargs):
    """
    Build the bedrock client and verify connectivity with a lightweight
    list_foundation_models call. Raises on any auth or connectivity failure.
    """
    client = None
    try:
        client = _build_bedrock_client(connection)
        client.list_foundation_models(maxResults=1)
        log_info("AWSBedrockStartBatchInference: bedrock client initialised and connectivity verified.")
        return {"client": client}
    except (BotoCoreError, ClientError) as exc:
        log_error(f"AWSBedrockStartBatchInference initialize failed: {exc}")
        if client:
            client.close()
        raise


def run(client, payload, **kwargs):
    """
    Start a Bedrock batch inference (model invocation) job.

    Payload fields:
        job_name             (str)       # required — unique name for the batch job
        role_arn             (str)       # required — IAM role ARN with S3 read/write and bedrock:InvokeModel
        model_id             (str)       # required — Bedrock model ID, e.g. "anthropic.claude-3-sonnet-20240229-v1:0"
        input_data_config    (dict)      # required — {"s3InputDataConfig": {"s3Uri": "s3://bucket/input/", "s3InputFormat": "JSONL"}}
        output_data_config   (dict)      # required — {"s3OutputDataConfig": {"s3Uri": "s3://bucket/output/"}}
        client_request_token (str)       # optional — idempotency token
        tags                 (list)      # optional — list of {"key": str, "value": str}
    """
    job_name = payload.get("job_name")                        # required
    role_arn = payload.get("role_arn")                        # required
    model_id = payload.get("model_id")                        # required
    input_data_config = payload.get("input_data_config")      # required — S3 input location + format
    output_data_config = payload.get("output_data_config")    # required — S3 output location
    client_request_token = payload.get("client_request_token") # optional — idempotency token
    tags = payload.get("tags")                                 # optional — list of {"key": str, "value": str}

    if not job_name:
        raise ValueError("payload.job_name is required")
    if not role_arn:
        raise ValueError("payload.role_arn is required")
    if not model_id:
        raise ValueError("payload.model_id is required")
    if not input_data_config:
        raise ValueError("payload.input_data_config is required")
    if not output_data_config:
        raise ValueError("payload.output_data_config is required")

    call_kwargs = {
        "jobName": job_name,
        "roleArn": role_arn,
        "modelId": model_id,
        "inputDataConfig": input_data_config,
        "outputDataConfig": output_data_config,
    }
    if client_request_token:
        call_kwargs["clientRequestToken"] = client_request_token
    if tags:
        call_kwargs["tags"] = tags

    try:
        response = client.create_model_invocation_job(**call_kwargs)
        job_arn = response.get("jobArn", "")
        log_info(f"AWSBedrockStartBatchInference: batch job started — job_name={job_name}, job_arn={job_arn}")
        return {
            "status": "pending",
            "execution_type": "async",
            "result": {
                "job_arn": job_arn,
                "job_name": job_name,
                "model_id": model_id,
            },
            "job_arn": job_arn,
        }
    except (BotoCoreError, ClientError) as exc:
        log_error(f"AWSBedrockStartBatchInference run failed: {exc}")
        raise


def check_completion(client, run_details, payload, **kwargs):
    """
    Poll the batch inference job status.

    Checks run_details.status == "failed" first, then polls AWS for the real state.
    AWS statuses: Submitted, InProgress, Stopping -> pending;
                  Completed -> success; Failed, Stopped, Expired -> failed.
    On success includes job_arn, job_name, model_id, status, and output_data_config.
    """
    if run_details.get("status") == "failed":
        return {"status": "failed", "result": run_details.get("result", {})}

    job_arn = run_details.get("job_arn") or run_details["result"]["job_arn"]

    try:
        response = client.get_model_invocation_job(jobIdentifier=job_arn)
        aws_status = response.get("status", "")
        log_info(f"AWSBedrockStartBatchInference: job status={aws_status}, job_arn={job_arn}")

        if aws_status == "Completed":
            return {
                "status": "success",
                "result": {
                    "job_arn": job_arn,
                    "job_name": run_details["result"]["job_name"],
                    "model_id": run_details["result"]["model_id"],
                    "status": aws_status,
                    "output_data_config": response.get("outputDataConfig", {}),
                },
            }
        elif aws_status in ("Failed", "Stopped", "Expired"):
            log_error(f"AWSBedrockStartBatchInference: job ended with status={aws_status}")
            return {
                "status": "failed",
                "result": {
                    "job_arn": job_arn,
                    "status": aws_status,
                    "message": response.get("message", ""),
                },
            }
        else:
            return {"status": "pending", "result": run_details.get("result", {})}
    except (BotoCoreError, ClientError) as exc:
        log_error(f"AWSBedrockStartBatchInference check_completion failed: {exc}")
        raise


def finish(least_action_task_object, client, completion_details, run_details):
    """
    Log final outcome and release any held resources. Never re-raises.

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
                log_info("task", "finish", "client_closed", "Bedrock boto3 client closed successfully")
            except Exception as close_error:
                log_error("task", "finish", "client_close_error", f"Error closing client: {str(close_error)}")

        if final_status == "success":
            output = completion_details.get("output", {})
            log_info("task", "finish", "operation_summary",
                     f"Batch inference job {output.get('job_arn')} completed — status={output.get('status')}")
        elif final_status == "failed":
            log_error("task", "finish", "operation_failed",
                      f"Batch inference failed: {completion_details.get('message')}")
        else:
            log_info("task", "finish", "operation_status",
                     f"status={final_status}, message={completion_details.get('message')}")

        log_info("task", "finish", "cleanup_complete", f"Cleanup complete for task: {task_laui}")

    except Exception as e:
        log_error("task", "finish", "cleanup_error", f"Error during finish/cleanup: {str(e)}")
        # Never re-raise from finish — allow graceful task completion
'''}

bashblock = {"main.sh": "#!/bin/bash\nset -euo pipefail\npip install --quiet boto3"}

connection = {"region": "us-east-1"}

payload = {
    "job_name": "my-batch-job-001",                                          # required
    "role_arn": "arn:aws:iam::123456789012:role/BedrockBatchRole",           # required
    "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",                  # required
    "input_data_config": {                                                   # required
        "s3InputDataConfig": {
            "s3Uri": "s3://my-bucket/input/",
            "s3InputFormat": "JSONL",
        }
    },
    "output_data_config": {                                                  # required
        "s3OutputDataConfig": {
            "s3Uri": "s3://my-bucket/output/",
        }
    },
    # "client_request_token": "unique-token-001",                           # optional — idempotency token
    # "tags": [{"key": "Project", "value": "MyProject"}],                   # optional
}

prompt = (
    "Start a Bedrock batch inference job to process a large JSONL dataset in S3. "
    "Provide job_name, role_arn, model_id, input_data_config, and output_data_config. "
    "Optional: client_request_token, tags. Async — polls until Completed/Failed/Stopped/Expired."
)

install_docs = """## Installation

Requires `boto3` (included in the base Lambda/EC2 environment).

```bash
pip install boto3
```

IAM permissions required for the LeastAction executor role:
- `bedrock:CreateModelInvocationJob`
- `bedrock:GetModelInvocationJob`
- `bedrock:ListFoundationModels`
- `iam:PassRole` (to pass role_arn to Bedrock)

IAM permissions required for the `role_arn` passed in the payload:
- `s3:GetObject` on the input S3 bucket/prefix
- `s3:PutObject` on the output S3 bucket/prefix
- `bedrock:InvokeModel` for the target model
"""

guide_docs = """## What it does

Starts a Bedrock batch inference job to run model invocations on a large JSONL dataset stored in S3, using the bedrock API (`create_model_invocation_job`). The call returns immediately with a `job_arn` — the operator then polls `get_model_invocation_job` in `check_completion` until the status reaches `Completed`, `Failed`, `Stopped`, or `Expired`. Output results are written back to S3 in JSONL format matching the order of the input records.

---

## Auth

1. **Explicit credentials** — set `aws_access_key_id` and `aws_secret_access_key` in the connection. An optional `aws_session_token` can be included for temporary credentials.
2. **Assume IAM role via STS** — set `role_arn` in the connection. The operator assumes the role via STS before calling bedrock.
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
  "role_arn": "arn:aws:iam::123456789012:role/LeastActionExecutorRole"
}
```

**Scenario 3: Default credential chain (EC2 / ECS / env)**
```json
{
  "region": "us-east-1"
}
```

| Field                 | Required | Description                                          |
|-----------------------|----------|------------------------------------------------------|
| region                | Yes      | AWS region where the batch job will run              |
| aws_access_key_id     | No       | Explicit access key (use with secret_access_key)     |
| aws_secret_access_key | No       | Explicit secret key                                  |
| aws_session_token     | No       | Session token for temporary credentials              |
| role_arn              | No       | IAM role ARN to assume via STS                       |

---

## Payload

| Field                | Required | Description                                                                                                           |
|----------------------|----------|-----------------------------------------------------------------------------------------------------------------------|
| job_name             | Yes      | Unique name for the batch job — must be unique per account and region                                                 |
| role_arn             | Yes      | IAM role ARN passed to Bedrock — needs `s3:GetObject`, `s3:PutObject`, `bedrock:InvokeModel`, and `iam:PassRole`      |
| model_id             | Yes      | Bedrock model ID — e.g. `anthropic.claude-3-sonnet-20240229-v1:0`                                                    |
| input_data_config    | Yes      | S3 input location and format — `{"s3InputDataConfig": {"s3Uri": "s3://bucket/input/", "s3InputFormat": "JSONL"}}`    |
| output_data_config   | Yes      | S3 output location — `{"s3OutputDataConfig": {"s3Uri": "s3://bucket/output/"}}`                                      |
| client_request_token | No       | Idempotency token — safe to resubmit if the network fails                                                             |
| tags                 | No       | List of `{"key": "...", "value": "..."}` tag pairs                                                                   |

---

## Output (on success)

```json
{
  "job_arn": "arn:aws:bedrock:us-east-1:123456789012:model-invocation-job/my-batch-job-001",
  "job_name": "my-batch-job-001",
  "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
  "status": "Completed",
  "output_data_config": {
    "s3OutputDataConfig": {"s3Uri": "s3://my-bucket/output/"}
  }
}
```

| Field             | Description                                                         |
|-------------------|---------------------------------------------------------------------|
| job_arn           | Full ARN of the batch inference job                                 |
| job_name          | Name of the job as provided in the payload                          |
| model_id          | Model used for inference                                            |
| status            | Final AWS job status (`Completed`)                                  |
| output_data_config| S3 location where result JSONL files were written                   |

---

## Scenarios and Edge Cases

**Not all models support batch inference** — Batch inference is only available for a subset of Bedrock models. Before running a job, verify support in the AWS Bedrock console under "Batch inference." Submitting an unsupported model ID will cause an immediate failure.

**JSONL format must match model's invoke_model body** — Each line in the input file must be a complete JSON object formatted exactly as the model expects in an `invoke_model` call. For Claude: `{"anthropic_version": "bedrock-2023-05-31", "max_tokens": 1024, "messages": [...]}`. Always test with a small file first.

**IAM role needs s3:GetObject + s3:PutObject + bedrock:InvokeModel + iam:PassRole** — The executor role (used by LeastAction) must have `iam:PassRole` permission to pass the `role_arn` to Bedrock. The `role_arn` itself must have S3 read/write and Bedrock InvokeModel permissions.

---

## What this operator does NOT do

- Does not validate JSONL format before submission — malformed input records will fail silently in the output JSONL
- Does not process or parse output files — results are written to S3 as JSONL and must be read separately after the job completes
"""

description = """Starts a Bedrock batch inference job to run model invocations on a large JSONL
dataset stored in S3. Async: polls until the job reaches Completed, Failed, Stopped, or Expired."""

publisher = "LeastActionLabs"

metadata = {
    "service": "Bedrock",
    "category": "AI/ML",
    "tags": ["bedrock", "batch-inference", "llm", "aws"],
    "airflow_equivalent": "BedrockStartBatchInferenceOperator",
}

version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False
status = "draft"

publisher_notes = """## Publisher Notes

**Input JSONL format:** Each line in the input file must be a complete JSON object formatted exactly
as the model expects in an `invoke_model` call. The format is model-specific — Claude requires
`anthropic_version`, `max_tokens`, and `messages`; Titan uses a different schema. Always test with
a small file first.

**Not all models support batch:** Batch inference is only available for a subset of Bedrock models.
Before running a job, verify support in the AWS Bedrock console under "Batch inference." Submitting
an unsupported model_id will result in an immediate failure.

**Cost savings:** Batch jobs are typically 50% cheaper than real-time on-demand invocations for
large datasets, making this the preferred approach for offline processing, evals, or document
enrichment pipelines.

**IAM PassRole requirement:** The executor role (used by LeastAction) must have `iam:PassRole`
permission to pass the `role_arn` to Bedrock. This is a common setup mistake — the PassRole policy
must restrict the resource to the specific role ARN being passed.

**Job naming uniqueness:** `job_name` must be unique within the account and region. Reusing an
existing name will cause a conflict error. Use a timestamp or run ID suffix to ensure uniqueness.

**Output structure:** The output S3 prefix will contain one JSONL file per input file, with
responses in the same order as the input. If a single record fails, the job may still complete
with a partial output — check the per-record error fields in the output JSONL.
"""
