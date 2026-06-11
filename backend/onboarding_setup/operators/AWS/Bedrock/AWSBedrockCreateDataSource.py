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
AWS Bedrock Create Data Source Operator

Creates a data source for a Bedrock Knowledge Base. Synchronous.
Auth priority: explicit keys → assume IAM role → default credential chain.
"""

import json

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from src.common.logger.logger import log_error, log_info


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_bedrock_agent_client(connection: dict):
    region = connection.get("region", "us-east-1")
    access_key = connection.get("aws_access_key_id")
    secret_key = connection.get("aws_secret_access_key")
    session_token = connection.get("aws_session_token")
    assume_role_arn = connection.get("assume_iam_role")

    # Case 1: Explicit credentials
    if access_key and secret_key:
        log_info("task", "initialize", "auth_keys",
                 f"Using explicit access key ending ...{access_key[-4:]}")
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token,
            region_name=region,
        )
        return session.client("bedrock-agent")

    # Case 2: Assume IAM role via STS
    if assume_role_arn:
        log_info("task", "initialize", "auth_assume_role",
                 f"Assuming IAM role: {assume_role_arn}")
        sts = boto3.client("sts", region_name=region)
        assumed = sts.assume_role(RoleArn=assume_role_arn, RoleSessionName="leastaction_session")
        creds = assumed["Credentials"]
        session = boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region,
        )
        return session.client("bedrock-agent")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info("task", "initialize", "auth_default",
             "Using default AWS credential chain (instance profile / ECS task role / env / config)")
    return boto3.Session(region_name=region).client("bedrock-agent")


# ---------------------------------------------------------------------------
# Operator methods
# ---------------------------------------------------------------------------

def initialize(least_action_task_object):
    """
    Build and verify the Bedrock Agent boto3 client.

    Returns:
        boto3 bedrock-agent client
    """
    try:
        connection = least_action_task_object.get("connection", {})
        task_laui = least_action_task_object.get("laui")

        log_info("task", "initialize", "start",
                 f"Initializing Bedrock Create Data Source operator for task: {task_laui}")

        client = _build_bedrock_agent_client(connection)
        region = connection.get("region", "us-east-1")

        log_info("task", "initialize", "verify_connection",
                 f"Verifying Bedrock Agent connectivity in region: {region}")
        client.list_knowledge_bases(maxResults=1)

        log_info("task", "initialize", "connection_established",
                 f"Bedrock Agent client ready for region: {region}")
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
    Create a data source for a Bedrock Knowledge Base using create_data_source.

    Payload fields:
        knowledge_base_id                    (str, required)  -- ID of the target Knowledge Base
        name                                 (str, required)  -- name of the data source
        data_source_configuration            (dict, required) -- source config: {"type": "S3", "s3Configuration": {"bucketArn": "..."}}
        description                          (str, optional)  -- human-readable description
        server_side_encryption_configuration (dict, optional) -- KMS encryption config
        vector_ingestion_configuration       (dict, optional) -- chunking and embedding config
        client_token                         (str, optional)  -- idempotency token

    Returns:
        dict with status="success", execution_type="sync", result
    """
    try:
        task_laui = least_action_task_object.get("laui")
        payload = least_action_task_object.get("payload", {})

        log_info("task", "run", "extracting_payload",
                 f"Extracting create data source configuration for task: {task_laui}")

        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                log_error("task", "run", "payload_parse_error", "Failed to parse payload as JSON")
                return {"status": "failed", "execution_type": "sync", "result": None,
                        "error": "Invalid payload format — expected flat JSON object"}

        knowledge_base_id = payload.get("knowledge_base_id")
        name = payload.get("name")
        data_source_configuration = payload.get("data_source_configuration")

        for field, val in [("knowledge_base_id", knowledge_base_id), ("name", name),
                           ("data_source_configuration", data_source_configuration)]:
            if not val:
                log_error("task", "run", f"missing_{field}", f"{field} is required in payload")
                return {"status": "failed", "execution_type": "sync", "result": None,
                        "error": f"{field} is required in payload"}

        kwargs = {
            "knowledgeBaseId": knowledge_base_id,
            "name": name,
            "dataSourceConfiguration": data_source_configuration,
        }
        if payload.get("description"):
            kwargs["description"] = payload["description"]
        if payload.get("server_side_encryption_configuration"):
            kwargs["serverSideEncryptionConfiguration"] = payload["server_side_encryption_configuration"]
        if payload.get("vector_ingestion_configuration"):
            kwargs["vectorIngestionConfiguration"] = payload["vector_ingestion_configuration"]
        if payload.get("client_token"):
            kwargs["clientToken"] = payload["client_token"]

        log_info("task", "run", "creating_data_source",
                 f"Creating data source '{name}' for Knowledge Base {knowledge_base_id}")

        response = client.create_data_source(**kwargs)
        data_source = response.get("dataSource", {})
        data_source_id = data_source.get("dataSourceId", "")

        log_info("task", "run", "data_source_created",
                 f"Data source '{name}' created — ID: {data_source_id}")

        return {
            "status": "success",
            "execution_type": "sync",
            "result": {
                "data_source_id": data_source_id,
                "name": name,
                "knowledge_base_id": knowledge_base_id,
                "data_source_status": data_source.get("status", ""),
            },
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "client_error", f"AWS ClientError ({error_code}): {error_msg}")
        return {"status": "failed", "execution_type": "sync", "result": None,
                "error": f"{error_code}: {error_msg}"}
    except Exception as e:
        log_error("task", "run", "unexpected_error", f"Unexpected error during run: {str(e)}")
        return {"status": "failed", "execution_type": "sync", "result": None, "error": str(e)}


def check_completion(least_action_task_object, client, run_details):
    """
    CreateDataSource is synchronous — pass through run_details directly.

    Returns:
        dict with status, message, output
    """
    if run_details.get("status") == "failed":
        log_error("task", "check_completion", "run_phase_failed",
                  f"Run phase reported failure: {run_details.get('error')}")
        return {"status": "failed", "message": f"CreateDataSource failed: {run_details.get('error')}",
                "output": None}

    result = run_details.get("result", {})
    log_info("task", "check_completion", "sync_complete",
             f"Data source {result.get('data_source_id')} created for KB {result.get('knowledge_base_id')}")
    return {
        "status": "success",
        "message": f"Data source '{result.get('name')}' created successfully",
        "output": result,
    }


def finish(least_action_task_object, client, completion_details, run_details):
    """
    Log final outcome and release any held resources.

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
                log_info("task", "finish", "client_closed",
                         "Bedrock Agent boto3 client closed successfully")
            except Exception as close_error:
                log_error("task", "finish", "client_close_error",
                          f"Error closing client: {str(close_error)}")

        if final_status == "success":
            output = completion_details.get("output", {})
            log_info("task", "finish", "operation_summary",
                     f"Data source '{output.get('name')}' (ID: {output.get('data_source_id')}) "
                     f"created for Knowledge Base {output.get('knowledge_base_id')}")
        elif final_status == "failed":
            log_error("task", "finish", "operation_failed",
                      f"CreateDataSource failed: {completion_details.get('message')}")
        else:
            log_info("task", "finish", "operation_status",
                     f"status={final_status}, message={completion_details.get('message')}")

        log_info("task", "finish", "cleanup_complete", f"Cleanup complete for task: {task_laui}")

    except Exception as e:
        log_error("task", "finish", "cleanup_error", f"Error during finish/cleanup: {str(e)}")
        # Never re-raise from finish — allow graceful task completion
'''}

bashblock = {"main.sh": """#!/bin/bash
set -e
pip install boto3>=1.28.0
pip install botocore>=1.31.0
echo "Dependencies installed successfully"
"""}

connection = {"region": "us-east-1"}

payload = {
    "knowledge_base_id": "KB1234567890",          # required
    "name": "my-s3-data-source",                   # required
    "data_source_configuration": {                 # required
        "type": "S3",
        "s3Configuration": {"bucketArn": "arn:aws:s3:::my-bucket"}
    },
    # "description": "My S3 data source",          # optional
    # "vector_ingestion_configuration": {          # optional — chunking strategy
    #     "chunkingConfiguration": {
    #         "chunkingStrategy": "FIXED_SIZE",
    #         "fixedSizeChunkingConfiguration": {"maxTokens": 300, "overlapPercentage": 20}
    #     }
    # },
    # "client_token": "unique-token-123"           # optional — idempotency token
}

prompt = (
    "Create a data source for a Bedrock Knowledge Base via create_data_source. "
    "Required: knowledge_base_id, name, data_source_configuration. "
    "Optional: description, server_side_encryption_configuration, vector_ingestion_configuration, client_token. "
    "Synchronous — returns data_source_id immediately. "
    "Auth: explicit keys first, then assume_iam_role via STS, then default credential chain. "
    "finish() must close the boto3 client without re-raising exceptions."
)

install_docs = """# AWSBedrockCreateDataSource — Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {"Effect": "Allow", "Action": ["bedrock:CreateDataSource", "bedrock:ListKnowledgeBases"], "Resource": "*"}
"""

guide_docs = """## What it does

Creates a data source and attaches it to an existing Bedrock Knowledge Base using the bedrock-agent API. The call is synchronous and returns the `data_source_id` immediately. Creating a data source does NOT trigger ingestion — the Knowledge Base vector store remains empty until you call AWSBedrockIngestData with the returned `data_source_id`. Supported source types include S3, Confluence, SharePoint, Salesforce, and Web.

---

## Auth

1. **Explicit credentials** — set `aws_access_key_id` and `aws_secret_access_key` in the connection. An optional `aws_session_token` can be included for temporary credentials.
2. **Assume IAM role** — set `assume_iam_role` in the connection with a role ARN. The operator uses STS to assume the role and build a scoped session before calling bedrock-agent.
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
  "assume_iam_role": "arn:aws:iam::123456789012:role/BedrockAgentRole"
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
| assume_iam_role       | No       | IAM role ARN to assume via STS                   |

---

## Payload

| Field                                | Required | Description                                                                              |
|--------------------------------------|----------|------------------------------------------------------------------------------------------|
| knowledge_base_id                    | Yes      | ID of the target Knowledge Base                                                          |
| name                                 | Yes      | Name for this data source                                                                |
| data_source_configuration            | Yes      | Source type and config — e.g. `{"type": "S3", "s3Configuration": {"bucketArn": "..."}}` |
| description                          | No       | Human-readable description of the data source                                            |
| server_side_encryption_configuration | No       | KMS encryption config for data at rest                                                   |
| vector_ingestion_configuration       | No       | Chunking strategy and embedding settings                                                 |
| client_token                         | No       | Idempotency token — safe to resubmit if the network fails                                |

---

## Output (on success)

```json
{
  "data_source_id": "DS1234567890",
  "name": "my-s3-data-source",
  "knowledge_base_id": "KB1234567890",
  "data_source_status": "AVAILABLE"
}
```

| Field               | Description                                                  |
|---------------------|--------------------------------------------------------------|
| data_source_id      | Unique ID of the created data source                         |
| name                | Name of the data source as provided in the payload           |
| knowledge_base_id   | ID of the Knowledge Base this source is attached to          |
| data_source_status  | Immediate status returned by AWS (`AVAILABLE`)               |

---

## Scenarios and Edge Cases

**KB not found** — `ResourceNotFoundException` is raised if `knowledge_base_id` does not exist or belongs to a different region. Create the KB first using AWSBedrockCreateKnowledgeBase.

**S3 bucket not in same region** — The S3 bucket referenced in `data_source_configuration` must be in the same AWS region as the Knowledge Base. Cross-region S3 sources are not supported.

**Chunking defaults** — If `vector_ingestion_configuration` is omitted, AWS applies default fixed-size chunking (300 tokens, 20% overlap). Smaller chunks improve precision for specific lookups; larger chunks preserve context for summaries.

---

## What this operator does NOT do

- Does not ingest data into the vector store — call AWSBedrockIngestData with the returned `data_source_id` to trigger the first sync
- Does not create the Knowledge Base — the target KB must already exist before calling this operator
"""

description = """
Creates a data source for a Bedrock Knowledge Base via create_data_source. Synchronous —
returns data_source_id immediately. Supports S3, Confluence, SharePoint, Salesforce, and
Web sources. After creation, use AWSBedrockIngestData to load data into the vector store.
Auth: explicit keys first, then assume_iam_role via STS, then default credential chain.
finish() closes the boto3 client without re-raising exceptions.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "Bedrock",
    "category": "AI/ML",
    "tags": ["bedrock", "knowledge-base", "data-source", "rag", "aws"],
    "airflow_equivalent": "BedrockCreateDataSourceOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

**Source type support**: S3 is fully tested. Confluence, SharePoint, Salesforce, and Web
crawl sources require additional connector configuration in `data_source_configuration` —
refer to the AWS Bedrock Agent API reference for the exact schema per source type.

**Chunking defaults**: If `vector_ingestion_configuration` is omitted, AWS applies default
fixed-size chunking (300 tokens, 20% overlap). Tune chunk size for your content — smaller
chunks improve precision for specific lookups, larger chunks preserve context for summaries.

**Next step**: A data source must be ingested before it is queryable. Use AWSBedrockIngestData
with the returned `data_source_id` to trigger the first sync from your source into the vector store.
"""
