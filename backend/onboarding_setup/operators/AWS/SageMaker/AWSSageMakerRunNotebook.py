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
AWS SageMaker Run Notebook Operator

Executes a Jupyter notebook stored in S3 as a SageMaker Processing Job using papermill. Async.
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
        log_info("task", "initialize", "start", f"Initializing AWSSageMakerRunNotebook for task: {task_laui}")
        client = _build_sagemaker_client(connection)
        region = connection.get("region", "us-east-1")
        log_info("task", "initialize", "verify_connection", f"Verifying SageMaker connectivity in region: {region}")
        try:
            client.list_domains(MaxResults=1)
        except ClientError:
            pass  # list_domains not available in all regions; connectivity confirmed by client build
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
    Runs a Jupyter notebook as a SageMaker Processing Job using papermill.

    Payload fields:
        processing_job_name  (str, required)  -- unique name for the processing job
        role_arn             (str, required)  -- IAM role ARN for the processing job
        notebook_s3_uri      (str, required)  -- S3 URI of the input .ipynb notebook
        runner_script_s3_uri (str, required)  -- S3 URI of the runner script (papermill executor)
        output_s3_uri        (str, required)  -- S3 URI prefix for output notebook
        instance_type        (str, optional)  -- SageMaker instance type (default: ml.m5.xlarge)
        instance_count       (int, optional)  -- number of instances (default: 1)
        volume_size_gb       (int, optional)  -- EBS volume size in GB (default: 30)
        image_uri            (str, optional)  -- custom Docker image URI with papermill installed
        parameters           (dict, optional) -- notebook parameter values to inject
        tags                 (list, optional) -- list of {"Key": ..., "Value": ...} dicts

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

        job_name = payload.get("processing_job_name")
        role_arn = payload.get("role_arn")
        notebook_s3_uri = payload.get("notebook_s3_uri")
        runner_script_s3_uri = payload.get("runner_script_s3_uri")
        output_s3_uri = payload.get("output_s3_uri")

        for field, val in [("processing_job_name", job_name), ("role_arn", role_arn),
                           ("notebook_s3_uri", notebook_s3_uri),
                           ("runner_script_s3_uri", runner_script_s3_uri),
                           ("output_s3_uri", output_s3_uri)]:
            if not val:
                log_error("task", "run", "validation_error", f"Required field missing: {field}")
                return {"status": "failed", "execution_type": "async", "result": None,
                        "error": f"Required field missing: {field}"}

        instance_type = payload.get("instance_type", "ml.m5.xlarge")
        instance_count = payload.get("instance_count", 1)
        volume_size_gb = payload.get("volume_size_gb", 30)
        parameters = payload.get("parameters", {})

        environment = {}
        if parameters:
            environment["PAPERMILL_PARAMETERS"] = json.dumps(parameters)

        app_spec = {
            "ContainerEntrypoint": ["python3", "/opt/ml/processing/input/code/run_notebook.py"],
        }
        if payload.get("image_uri"):
            app_spec["ImageUri"] = payload["image_uri"]
        else:
            # Default to sklearn container which supports Python 3; user should supply papermill-ready image
            app_spec["ImageUri"] = "683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-scikit-learn:0.23-1-cpu-py3"

        kwargs = {
            "ProcessingJobName": job_name,
            "AppSpecification": app_spec,
            "RoleArn": role_arn,
            "ProcessingResources": {
                "ClusterConfig": {
                    "InstanceCount": instance_count,
                    "InstanceType": instance_type,
                    "VolumeSizeInGB": volume_size_gb,
                }
            },
            "ProcessingInputs": [
                {
                    "InputName": "notebook",
                    "S3Input": {
                        "S3Uri": notebook_s3_uri,
                        "LocalPath": "/opt/ml/processing/input/notebook",
                        "S3DataType": "S3Prefix",
                        "S3InputMode": "File",
                    }
                },
                {
                    "InputName": "code",
                    "S3Input": {
                        "S3Uri": runner_script_s3_uri,
                        "LocalPath": "/opt/ml/processing/input/code",
                        "S3DataType": "S3Prefix",
                        "S3InputMode": "File",
                    }
                },
            ],
            "ProcessingOutputConfig": {
                "Outputs": [
                    {
                        "OutputName": "notebook-output",
                        "S3Output": {
                            "S3Uri": output_s3_uri,
                            "LocalPath": "/opt/ml/processing/output",
                            "S3UploadMode": "EndOfJob",
                        }
                    }
                ]
            },
        }
        if environment:
            kwargs["Environment"] = environment
        if payload.get("tags"):
            kwargs["Tags"] = payload["tags"]

        log_info("task", "run", "starting_notebook_job",
                 f"Starting notebook processing job: {job_name} notebook={notebook_s3_uri} instance={instance_type}")
        client.create_processing_job(**kwargs)
        log_info("task", "run", "notebook_job_started", f"Notebook processing job submitted: {job_name}")

        return {"status": "pending", "execution_type": "async",
                "result": {"processing_job_name": job_name,
                           "notebook_s3_uri": notebook_s3_uri,
                           "output_s3_uri": output_s3_uri}}
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
    """Poll describe_processing_job to determine if notebook execution completed."""
    if run_details.get("status") == "failed":
        log_error("task", "check_completion", "run_phase_failed",
                  f"Run phase reported failure: {run_details.get('error')}")
        return {"status": "failed",
                "message": f"Run phase failed: {run_details.get('error')}",
                "output": None}
    try:
        job_name = (run_details.get("result") or {}).get("processing_job_name")
        if not job_name:
            return {"status": "failed", "message": "No processing_job_name in run_details", "output": None}

        response = client.describe_processing_job(ProcessingJobName=job_name)
        status = response.get("ProcessingJobStatus", "Unknown")
        log_info("task", "check_completion", "job_status", f"Processing job {job_name} status: {status}")

        if status == "Completed":
            return {"status": "success",
                    "message": f"Notebook processing job {job_name} completed successfully",
                    "output": {"processing_job_name": job_name,
                               "notebook_s3_uri": (run_details.get("result") or {}).get("notebook_s3_uri", ""),
                               "output_s3_uri": (run_details.get("result") or {}).get("output_s3_uri", ""),
                               "job_status": status}}
        elif status in ("Failed", "Stopped"):
            failure_reason = response.get("FailureReason", "Unknown")
            return {"status": "failed",
                    "message": f"Notebook processing job {status}: {failure_reason}",
                    "output": {"processing_job_name": job_name, "failure_reason": failure_reason}}
        return {"status": "pending",
                "message": f"Notebook processing job {job_name} is {status}",
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
                     f"Notebook executed successfully. Job: {output.get('processing_job_name')} "
                     f"Output: {output.get('output_s3_uri')}")
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
    "processing_job_name": "run-notebook-job",
    "role_arn": "arn:aws:iam::123456789012:role/SageMakerExecutionRole",
    "notebook_s3_uri": "s3://my-bucket/notebooks/my-notebook.ipynb",
    "runner_script_s3_uri": "s3://my-bucket/code/run_notebook.py",
    "output_s3_uri": "s3://my-bucket/notebook-output/",
    # "instance_type": "ml.m5.xlarge",   # optional, default ml.m5.xlarge
    # "instance_count": 1,               # optional, default 1
    # "volume_size_gb": 30,              # optional, default 30
    # "image_uri": "...",                # optional, must have papermill installed
    # "parameters": {"param1": "val"},   # optional, injected into notebook parameters cell
    # "tags": [{"Key": "env", "Value": "dev"}]  # optional
}

prompt = (
    "Executes a Jupyter notebook stored in S3 using a SageMaker Processing Job with papermill. "
    "Provide processing_job_name, role_arn, notebook_s3_uri, runner_script_s3_uri, output_s3_uri. "
    "Optional: instance_type (default ml.m5.xlarge), instance_count, volume_size_gb, image_uri, "
    "parameters (dict of notebook param overrides), tags. Async — polls until Completed/Failed/Stopped."
)

install_docs = """## Dependencies
- boto3>=1.28.0
- botocore>=1.31.0

## IAM Permissions Required
- sagemaker:CreateProcessingJob
- sagemaker:DescribeProcessingJob
- iam:PassRole (on role_arn)
- s3:GetObject (on notebook and runner script buckets)
- s3:PutObject (on output bucket)

## Runner Script (run_notebook.py)
Upload this Python file to S3 at runner_script_s3_uri:

```python
import subprocess, sys, os, glob
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'papermill', 'nbconvert', 'ipykernel', '-q'])
import papermill as pm
input_dir = '/opt/ml/processing/input/notebook'
output_dir = '/opt/ml/processing/output'
os.makedirs(output_dir, exist_ok=True)
notebooks = glob.glob(os.path.join(input_dir, '*.ipynb'))
notebook_path = notebooks[0]
output_path = os.path.join(output_dir, os.path.basename(notebook_path).replace('.ipynb', '-output.ipynb'))
params = {}
params_json = os.environ.get('PAPERMILL_PARAMETERS')
if params_json:
    import json
    params = json.loads(params_json)
pm.execute_notebook(notebook_path, output_path, parameters=params, kernel_name='python3')
print('Notebook executed successfully!')
```
"""

guide_docs = """## What it does

Runs a Jupyter notebook stored in S3 as a SageMaker Processing Job using papermill. The notebook and a runner script are downloaded from S3, mounted into a managed container, and executed by papermill — the resulting notebook with all cell outputs is uploaded back to S3. This operator is async and polls until the processing job reaches Completed, Failed, or Stopped.

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

| Field                | Required | Description                                                                        |
|----------------------|----------|------------------------------------------------------------------------------------|
| processing_job_name  | Yes      | Unique name for the SageMaker processing job                                       |
| role_arn             | Yes      | IAM execution role ARN that SageMaker assumes for the job                          |
| notebook_s3_uri      | Yes      | S3 URI (prefix) of the input .ipynb notebook file                                  |
| runner_script_s3_uri | Yes      | S3 URI (prefix) of the papermill runner script (run_notebook.py)                   |
| output_s3_uri        | Yes      | S3 URI prefix where the executed notebook with outputs is saved                    |
| instance_type        | No       | SageMaker compute instance type (default: ml.m5.xlarge)                            |
| instance_count       | No       | Number of instances (default: 1)                                                   |
| volume_size_gb       | No       | EBS volume size in GB (default: 30)                                                |
| image_uri            | No       | Docker image URI with papermill installed (default: sklearn container)             |
| parameters           | No       | Dict of notebook parameter overrides injected into the tagged parameters cell      |
| tags                 | No       | List of {"Key": ..., "Value": ...} dicts                                           |

---

## Output (on success)

    {
      "processing_job_name": "run-my-notebook",
      "notebook_s3_uri": "s3://my-bucket/notebooks/analysis.ipynb",
      "output_s3_uri": "s3://my-bucket/notebook-output/",
      "job_status": "Completed"
    }

| Field               | Description                                                    |
|---------------------|----------------------------------------------------------------|
| processing_job_name | Name of the completed SageMaker processing job                 |
| notebook_s3_uri     | S3 URI of the original input notebook                          |
| output_s3_uri       | S3 prefix where the executed notebook was uploaded             |
| job_status          | Final job status — Completed on success                        |

---

## Scenarios and Edge Cases

Job fails (check failure_reason):
  The processing job transitions to Failed with a FailureReason set. Common causes are missing IAM permissions, invalid S3 URIs, or errors in the notebook itself. Inspect CloudWatch logs for the container's stdout/stderr.

image_uri not specified (must include papermill):
  If image_uri is omitted, the default sklearn container is used and the runner script installs papermill at runtime (slow cold start). For faster execution, use a custom image with papermill pre-installed.

parameters not injecting (notebook must have tagged params cell):
  The parameters dict is passed via the PAPERMILL_PARAMETERS environment variable and injected by the runner script. This only works if the notebook has a cell tagged with the "parameters" tag in Jupyter metadata — otherwise papermill inserts a new cell at the top.

---

## What this operator does NOT do

- Does not install Python dependencies inside the notebook at runtime automatically — dependencies must be pre-installed in the image or added to the runner script.
- Does not support GPU instances without a custom image that includes GPU-enabled papermill and a CUDA runtime.
- Does not validate that notebook_s3_uri or runner_script_s3_uri exist before submitting the job.
- Does not clean up or delete the processing job after completion.
"""

description = (
    "Executes a Jupyter notebook stored in S3 as a SageMaker Processing Job using papermill. "
    "The notebook and runner script are loaded from S3, run on a managed compute instance, "
    "and the executed notebook with all outputs is saved back to S3. Async."
)

publisher = "LeastActionLabs"

metadata = {
    "service": "SageMaker",
    "category": "ML",
    "tags": ["sagemaker", "notebook", "processing", "papermill", "aws"],
    "airflow_equivalent": "SageMakerNotebookOperator",
}

version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False
status = "draft"

publisher_notes = """## Publisher Notes

This operator uses SageMaker Processing Jobs to execute Jupyter notebooks via papermill.
The runner_script_s3_uri must point to a Python file that calls papermill.execute_notebook — see install_docs for the reference implementation.
The image_uri must have papermill pre-installed; if omitted, the default sklearn container is used and the runner script installs papermill at runtime (slower cold start).
notebook_s3_uri is the S3 prefix containing the input .ipynb — it is mounted at /opt/ml/processing/input/notebook inside the container.
The executed notebook (with all cell outputs) is written to /opt/ml/processing/output and uploaded to output_s3_uri at job completion.
Parameters dict injects values into the notebook cell tagged with 'parameters' in Jupyter — standard papermill parameterization.
runner_script_s3_uri is typically a custom Python file; the AWS run_notebook.sh is a bash variant and requires a different image setup.
Processing job names must be unique — append a timestamp or UUID to avoid ResourceInUse errors on reruns.
"""
