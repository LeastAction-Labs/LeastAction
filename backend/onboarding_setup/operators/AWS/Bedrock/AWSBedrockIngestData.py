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
AWSBedrockIngestData operator.
Starts an ingestion job to sync a data source into a Bedrock Knowledge Base vector store.
"""
import json
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from src.common.logger.logger import log_error, log_info


def _build_bedrock_agent_client(connection):
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
            RoleSessionName=connection.get("role_session_name", "LeastActionBedrockAgentSession"),
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

    return session.client("bedrock-agent")


def initialize(connection, **kwargs):
    """
    Build the bedrock-agent client and verify connectivity with a lightweight
    list_knowledge_bases call. Raises on any auth or connectivity failure.
    """
    client = None
    try:
        client = _build_bedrock_agent_client(connection)
        client.list_knowledge_bases(maxResults=1)
        log_info("AWSBedrockIngestData: bedrock-agent client initialised and connectivity verified.")
        return {"client": client}
    except (BotoCoreError, ClientError) as exc:
        log_error(f"AWSBedrockIngestData initialize failed: {exc}")
        if client:
            client.close()
        raise


def run(client, payload, **kwargs):
    """
    Start an ingestion job for a Bedrock Knowledge Base data source.

    Payload fields:
        knowledge_base_id (str)  # required — ID of the Knowledge Base
        data_source_id    (str)  # required — ID of the data source to ingest
        client_token      (str)  # optional — idempotency token
        description       (str)  # optional — description of this ingestion job
    """
    knowledge_base_id = payload.get("knowledge_base_id")  # required
    data_source_id = payload.get("data_source_id")         # required
    client_token = payload.get("client_token")              # optional — idempotency token
    description = payload.get("description")                # optional — description of this ingestion job

    if not knowledge_base_id:
        raise ValueError("payload.knowledge_base_id is required")
    if not data_source_id:
        raise ValueError("payload.data_source_id is required")

    call_kwargs = {
        "knowledgeBaseId": knowledge_base_id,
        "dataSourceId": data_source_id,
    }
    if client_token:
        call_kwargs["clientToken"] = client_token
    if description:
        call_kwargs["description"] = description

    try:
        response = client.start_ingestion_job(**call_kwargs)
        ingestion_job_id = response["ingestionJob"]["ingestionJobId"]
        log_info(f"AWSBedrockIngestData: ingestion job started — job_id={ingestion_job_id}")
        return {
            "status": "pending",
            "execution_type": "async",
            "result": {
                "ingestion_job_id": ingestion_job_id,
                "knowledge_base_id": knowledge_base_id,
                "data_source_id": data_source_id,
            },
            "ingestion_job_id": ingestion_job_id,
        }
    except (BotoCoreError, ClientError) as exc:
        log_error(f"AWSBedrockIngestData run failed: {exc}")
        raise


def check_completion(client, run_details, payload, **kwargs):
    """
    Poll the ingestion job status.

    Checks run_details.status == "failed" first, then polls AWS for the real state.
    AWS statuses: STARTING, IN_PROGRESS -> pending; COMPLETE -> success; FAILED -> failed.
    On success includes ingestion statistics (numberOfDocumentsScanned, etc.).
    """
    if run_details.get("status") == "failed":
        return {"status": "failed", "result": run_details.get("result", {})}

    knowledge_base_id = run_details["result"]["knowledge_base_id"]
    data_source_id = run_details["result"]["data_source_id"]
    ingestion_job_id = run_details.get("ingestion_job_id") or run_details["result"]["ingestion_job_id"]

    try:
        response = client.get_ingestion_job(
            knowledgeBaseId=knowledge_base_id,
            dataSourceId=data_source_id,
            ingestionJobId=ingestion_job_id,
        )
        job = response["ingestionJob"]
        aws_status = job.get("status", "")

        if aws_status == "COMPLETE":
            return {
                "status": "success",
                "result": {
                    "ingestion_job_id": ingestion_job_id,
                    "knowledge_base_id": knowledge_base_id,
                    "data_source_id": data_source_id,
                    "statistics": job.get("statistics", {}),
                },
            }
        elif aws_status == "FAILED":
            failure_reasons = job.get("failureReasons", [])
            log_error(f"AWSBedrockIngestData: ingestion job FAILED — reasons={failure_reasons}")
            return {
                "status": "failed",
                "result": {
                    "ingestion_job_id": ingestion_job_id,
                    "failure_reasons": failure_reasons,
                },
            }
        else:
            log_info(f"AWSBedrockIngestData: ingestion job still running — aws_status={aws_status}")
            return {"status": "pending", "result": run_details.get("result", {})}
    except (BotoCoreError, ClientError) as exc:
        log_error(f"AWSBedrockIngestData check_completion failed: {exc}")
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
                log_info("task", "finish", "client_closed", "Bedrock Agent boto3 client closed successfully")
            except Exception as close_error:
                log_error("task", "finish", "client_close_error", f"Error closing client: {str(close_error)}")
        if final_status == "success":
            output = completion_details.get("output", {})
            log_info("task", "finish", "operation_summary",
                     f"Ingestion job {output.get('ingestion_job_id')} completed — status={output.get('ingestion_job_status')}")
        elif final_status == "failed":
            log_error("task", "finish", "operation_failed", f"Ingestion failed: {completion_details.get('message')}")
        else:
            log_info("task", "finish", "operation_status", f"status={final_status}, message={completion_details.get('message')}")
        log_info("task", "finish", "cleanup_complete", f"Cleanup complete for task: {task_laui}")
    except Exception as e:
        log_error("task", "finish", "cleanup_error", f"Error during finish/cleanup: {str(e)}")
        # Never re-raise from finish — allow graceful task completion
'''}

bashblock = {"main.sh": "#!/bin/bash\nset -euo pipefail\npip install --quiet boto3"}

connection = {"region": "us-east-1"}

payload = {
    "knowledge_base_id": "XXXXXXXXXX",  # required
    "data_source_id": "XXXXXXXXXX",      # required
    # "client_token": "unique-token",    # optional — idempotency token
    # "description": "Nightly sync",     # optional — description of this ingestion job
}

prompt = "Ingest a Bedrock Knowledge Base data source and poll until the job completes."

install_docs = """## Installation

Requires `boto3` (included in the base Lambda/EC2 environment).

```bash
pip install boto3
```

IAM permissions required:
- `bedrock:StartIngestionJob`
- `bedrock:GetIngestionJob`
- `bedrock:ListKnowledgeBases`
"""

guide_docs = """## What it does

Starts an ingestion job to sync a data source into a Bedrock Knowledge Base vector store using the bedrock-agent API. The call returns immediately with an `ingestion_job_id` — the operator then polls `get_ingestion_job` in `check_completion` until the status reaches `COMPLETE` or `FAILED`. On success the output includes ingestion statistics showing how many documents were scanned, failed, or deleted.

---

## Auth

1. **Explicit credentials** — set `aws_access_key_id` and `aws_secret_access_key` in the connection. An optional `aws_session_token` can be included for temporary credentials.
2. **Assume IAM role via STS** — set `role_arn` in the connection. The operator assumes the role via STS before calling bedrock-agent.
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
  "role_arn": "arn:aws:iam::123456789012:role/BedrockAgentRole"
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
| region                | Yes      | AWS region where the Knowledge Base exists       |
| aws_access_key_id     | No       | Explicit access key (use with secret_access_key) |
| aws_secret_access_key | No       | Explicit secret key                              |
| aws_session_token     | No       | Session token for temporary credentials          |
| role_arn              | No       | IAM role ARN to assume via STS                   |

---

## Payload

| Field              | Required | Description                                                                    |
|--------------------|----------|--------------------------------------------------------------------------------|
| knowledge_base_id  | Yes      | ID of the Knowledge Base to ingest into                                        |
| data_source_id     | Yes      | ID of the data source to sync from                                             |
| client_token       | No       | Idempotency token — safe to resubmit if the network fails                      |
| description        | No       | Human-readable description for this ingestion job                              |

---

## Output (on success)

```json
{
  "ingestion_job_id": "IJB1234567890",
  "knowledge_base_id": "KB1234567890",
  "data_source_id": "DS1234567890",
  "statistics": {
    "numberOfDocumentsScanned": 150,
    "numberOfDocumentsFailed": 0,
    "numberOfDocumentsDeleted": 0,
    "numberOfMetadataDocumentsScanned": 150,
    "numberOfMetadataDocumentsModified": 10
  }
}
```

| Field                          | Description                                                        |
|--------------------------------|--------------------------------------------------------------------|
| ingestion_job_id               | Unique ID of the ingestion job                                     |
| knowledge_base_id              | ID of the Knowledge Base that was updated                          |
| data_source_id                 | ID of the data source that was synced                              |
| statistics                     | Document-level counters for the ingestion run                      |

---

## Scenarios and Edge Cases

**Large source takes 30+ minutes** — Ingestion of large S3 buckets with many documents can take 30 minutes or more. Set LeastAction task timeouts accordingly. The async polling loop handles this automatically.

**Partial failure** — Some documents may fail while others succeed. The job still reaches `COMPLETE` status. Inspect `statistics.numberOfDocumentsFailed` and check CloudWatch Logs for per-document error details.

**Re-ingesting unchanged data is idempotent** — If the underlying S3 data has not changed since the last ingestion, Bedrock scans the source but skips unchanged documents. Statistics will show 0 documents added.

---

## What this operator does NOT do

- Does not create the Knowledge Base or data source — both must exist before calling this operator
- Does not query the KB after ingestion — use AWSBedrockRetrieve or AWSBedrockRetrieveAndGenerate for that
"""

description = """Starts an ingestion job to sync a data source into a Bedrock Knowledge Base vector store.
Async: polls until the job reaches COMPLETE or FAILED, then returns ingestion statistics."""

publisher = "LeastActionLabs"

metadata = {
    "service": "Bedrock",
    "category": "AI/ML",
    "tags": ["bedrock", "knowledge-base", "ingestion", "rag", "aws"],
    "airflow_equivalent": "BedrockIngestDataOperator",
}

version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False
status = "draft"

publisher_notes = """## Publisher Notes

**Eventual consistency:** Newly ingested data may take a few seconds to appear in query results even after the job shows COMPLETE. Do not assume the KB is immediately queryable the moment the job finishes.

**Idempotency:** Re-ingesting the same data source when the underlying S3 data has not changed is safe. Bedrock will scan the source but skip documents that are unchanged, so statistics may show 0 documents added.

**Large data sources:** Jobs over millions of documents can take 30+ minutes. Set LeastAction task timeouts accordingly and rely on the async polling loop rather than a fixed wait.

**Statistics fields returned on success:**
- `numberOfDocumentsScanned` — total docs examined
- `numberOfDocumentsFailed` — docs that could not be processed (check CloudWatch for reasons)
- `numberOfDocumentsDeleted` — docs removed from the vector store because they no longer exist in the source
- `numberOfMetadataDocumentsScanned`, `numberOfMetadataDocumentsModified`

**Failure reasons:** When status is FAILED, the `failure_reasons` list in the output contains human-readable strings explaining what went wrong (e.g. S3 permission denied, unsupported file type).
"""
