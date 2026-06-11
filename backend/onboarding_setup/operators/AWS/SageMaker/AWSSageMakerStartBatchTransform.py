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
AWS SageMaker Start Batch Transform Operator

Starts a SageMaker batch transform job for offline inference on large S3 datasets. Async.
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
                 f"Initializing AWSSageMakerStartBatchTransform for task: {task_laui}")
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
    Starts a SageMaker batch transform job.

    Payload fields:
        transform_job_name      (str, required)   -- unique name for the transform job
        model_name              (str, required)   -- name of an existing SageMaker model
        transform_input         (dict, required)  -- input data config with DataSource and ContentType
        transform_output        (dict, required)  -- {"S3OutputPath": "s3://bucket/output/"}
        transform_resources     (dict, required)  -- {"InstanceType": "ml.m5.xlarge", "InstanceCount": 1}
        batch_strategy          (str, optional)   -- "MultiRecord" or "SingleRecord"
        max_concurrent_transforms (int, optional) -- max parallel transform requests
        max_payload_in_mb       (int, optional)   -- max payload size per request in MB
        environment             (dict, optional)  -- environment variables for the container
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

        transform_job_name = payload.get("transform_job_name")
        model_name = payload.get("model_name")
        transform_input = payload.get("transform_input")
        transform_output = payload.get("transform_output")
        transform_resources = payload.get("transform_resources")

        for field, val in [("transform_job_name", transform_job_name),
                           ("model_name", model_name),
                           ("transform_input", transform_input),
                           ("transform_output", transform_output),
                           ("transform_resources", transform_resources)]:
            if not val:
                log_error("task", "run", "validation_error", f"Required field missing: {field}")
                return {"status": "failed", "execution_type": "async", "result": None,
                        "error": f"Required field missing: {field}"}

        kwargs = {
            "TransformJobName": transform_job_name,
            "ModelName": model_name,
            "TransformInput": transform_input,
            "TransformOutput": transform_output,
            "TransformResources": transform_resources,
        }
        if payload.get("batch_strategy"):
            kwargs["BatchStrategy"] = payload["batch_strategy"]
        if payload.get("max_concurrent_transforms") is not None:
            kwargs["MaxConcurrentTransforms"] = payload["max_concurrent_transforms"]
        if payload.get("max_payload_in_mb") is not None:
            kwargs["MaxPayloadInMB"] = payload["max_payload_in_mb"]
        if payload.get("environment"):
            kwargs["Environment"] = payload["environment"]
        if payload.get("tags"):
            kwargs["Tags"] = payload["tags"]

        log_info("task", "run", "starting_transform_job",
                 f"Starting batch transform job: {transform_job_name} model={model_name}")
        response = client.create_transform_job(**kwargs)
        transform_job_arn = response.get("TransformJobArn", "")
        log_info("task", "run", "transform_job_started",
                 f"Batch transform job started. ARN: {transform_job_arn}")

        return {"status": "pending", "execution_type": "async",
                "result": {"transform_job_name": transform_job_name,
                           "transform_job_arn": transform_job_arn}}
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
    """Poll describe_transform_job until Completed, Failed, or Stopped."""
    if run_details.get("status") == "failed":
        log_error("task", "check_completion", "run_phase_failed",
                  f"Run phase reported failure: {run_details.get('error')}")
        return {"status": "failed",
                "message": f"Run phase failed: {run_details.get('error')}",
                "output": None}
    try:
        transform_job_name = (run_details.get("result") or {}).get("transform_job_name")
        if not transform_job_name:
            return {"status": "failed", "message": "No transform_job_name in run_details", "output": None}

        response = client.describe_transform_job(TransformJobName=transform_job_name)
        job_status = response.get("TransformJobStatus", "Unknown")
        log_info("task", "check_completion", "transform_status",
                 f"Transform job {transform_job_name} status: {job_status}")

        if job_status == "Completed":
            output_path = response.get("TransformOutput", {}).get("S3OutputPath", "")
            return {"status": "success",
                    "message": f"Transform job {transform_job_name} completed successfully",
                    "output": {"transform_job_name": transform_job_name,
                               "transform_job_arn": (run_details.get("result") or {}).get("transform_job_arn", ""),
                               "output_s3_path": output_path,
                               "job_status": job_status}}
        elif job_status == "Failed":
            failure_reason = response.get("FailureReason", "Unknown")
            return {"status": "failed",
                    "message": f"Transform job failed: {failure_reason}",
                    "output": {"transform_job_name": transform_job_name,
                               "failure_reason": failure_reason}}
        elif job_status == "Stopped":
            return {"status": "failed",
                    "message": f"Transform job {transform_job_name} was stopped",
                    "output": {"transform_job_name": transform_job_name}}
        return {"status": "pending",
                "message": f"Transform job {transform_job_name} is {job_status}",
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
                     f"Batch transform job {output.get('transform_job_name')} completed. "
                     f"Output: {output.get('output_s3_path')}")
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
    "transform_job_name": "my-batch-transform-job",
    "model_name": "my-inference-model",
    "transform_input": {
        "DataSource": {
            "S3DataSource": {
                "S3DataType": "S3Prefix",
                "S3Uri": "s3://my-bucket/input/"
            }
        },
        "ContentType": "text/csv",
        "SplitType": "Line"
    },
    "transform_output": {"S3OutputPath": "s3://my-bucket/output/"},
    "transform_resources": {"InstanceType": "ml.m5.xlarge", "InstanceCount": 1},
    # "batch_strategy": "MultiRecord",       # optional
    # "max_concurrent_transforms": 1,        # optional
    # "max_payload_in_mb": 6,                # optional
}

prompt = (
    "Starts a SageMaker batch transform job for offline inference on large datasets stored in S3. "
    "Provide transform_job_name, model_name, transform_input, transform_output, transform_resources. "
    "Optional: batch_strategy (MultiRecord/SingleRecord), max_concurrent_transforms, max_payload_in_mb, "
    "environment, tags. Async — polls until Completed/Failed/Stopped."
)

install_docs = """## Dependencies
- boto3>=1.28.0
- botocore>=1.31.0

## IAM Permissions Required
- sagemaker:CreateTransformJob
- sagemaker:DescribeTransformJob
- s3:GetObject (on input bucket)
- s3:PutObject (on output bucket)

## Prerequisites
- The model referenced by model_name must exist (use AWSSageMakerCreateModel first)
"""

guide_docs = """## What it does

Starts a SageMaker batch transform job that runs offline inference on large datasets stored in S3. The job reads input files from S3, passes them through the specified model container for inference, and writes the predictions back to S3. Compute instances are provisioned only for the duration of the job — there are no idle charges. This operator is async and polls until the job reaches Completed, Failed, or Stopped.

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

| Field                    | Required | Description                                                                      |
|--------------------------|----------|----------------------------------------------------------------------------------|
| transform_job_name       | Yes      | Unique name for the batch transform job                                          |
| model_name               | Yes      | Name of an existing SageMaker model to use for inference                         |
| transform_input          | Yes      | Dict with DataSource (S3), ContentType, and SplitType                            |
| transform_output         | Yes      | Dict with S3OutputPath for storing inference results                             |
| transform_resources      | Yes      | Dict with InstanceType and InstanceCount                                         |
| batch_strategy           | No       | "MultiRecord" or "SingleRecord" — controls batching behavior                     |
| max_concurrent_transforms| No       | Maximum number of parallel transform requests per instance                       |
| max_payload_in_mb        | No       | Maximum request payload size in MB                                               |
| environment              | No       | Dict of environment variables injected into the container                        |
| tags                     | No       | List of {"Key": ..., "Value": ...} dicts                                         |

---

## Output (on success)

    {
      "transform_job_name": "my-batch-transform",
      "transform_job_arn": "arn:aws:sagemaker:us-east-1:123456789012:transform-job/my-batch-transform",
      "output_s3_path": "s3://my-bucket/output/",
      "job_status": "Completed"
    }

| Field              | Description                                                      |
|--------------------|------------------------------------------------------------------|
| transform_job_name | Name of the completed batch transform job                        |
| transform_job_arn  | Full ARN of the transform job                                    |
| output_s3_path     | S3 path where inference output files were written                |
| job_status         | Final job status — Completed on success                          |

---

## Scenarios and Edge Cases

Model not found:
  If model_name does not refer to an existing SageMaker model, the job fails immediately. Create the model first with AWSSageMakerCreateModel.

Output S3 prefix already has files (new results appended):
  If output files with the same keys already exist at the transform_output S3 path, they are overwritten by the new results. There is no automatic cleanup of prior output.

SingleRecord vs MultiRecord batching:
  MultiRecord sends multiple records per request, improving throughput for small records — requires the container to handle batched input. SingleRecord sends one record at a time — simpler but slower. Use MultiRecord for production workloads.

---

## What this operator does NOT do

- Does not create the model — use AWSSageMakerCreateModel first.
- Does not clean up input files from S3 after the transform completes.
- Does not validate that the model container supports the specified batch_strategy before submitting.
"""

description = (
    "Starts a SageMaker batch transform job for offline inference on large S3 datasets. "
    "Instances are provisioned only during the job. Async — polls until Completed/Failed/Stopped."
)

publisher = "LeastActionLabs"

metadata = {
    "service": "SageMaker",
    "category": "ML",
    "tags": ["sagemaker", "batch-transform", "inference", "aws"],
    "airflow_equivalent": "SageMakerTransformOperator",
}

version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False
status = "draft"

publisher_notes = """## Publisher Notes

Batch transform is the preferred approach for offline/bulk inference — cheaper than real-time endpoints because compute is provisioned only during the job.
The model must exist before starting a transform job — use AWSSageMakerCreateModel first.
MultiRecord batch strategy sends multiple records per request, significantly improving throughput for small records — requires the model container to handle batched input.
Output files are written to transform_output.S3OutputPath with the same prefix structure as input, with ".out" appended to each file name.
SplitType: "Line" is correct for line-delimited CSV/JSON; use SplitType: "RecordIO" for protobuf; use SplitType: "None" to send entire files as single requests.
max_payload_in_mb limits the request payload size — for large records, reduce this and use SingleRecord strategy.
transform_job_name must be unique within the account.
"""
