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
AWS Bedrock CreateKnowledgeBase Operator

Creates a Bedrock Knowledge Base. Async.
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
        log_info("task", "initialize", "auth_keys", f"Using explicit access key ending ...{access_key[-4:]}")
        session = boto3.Session(aws_access_key_id=access_key, aws_secret_access_key=secret_key,
                                aws_session_token=session_token, region_name=region)
        return session.client("bedrock-agent")

    # Case 2: Assume IAM role via STS
    if assume_role_arn:
        log_info("task", "initialize", "auth_assume_role", f"Assuming IAM role: {assume_role_arn}")
        sts = boto3.client("sts", region_name=region)
        assumed = sts.assume_role(RoleArn=assume_role_arn, RoleSessionName="leastaction_session")
        creds = assumed["Credentials"]
        session = boto3.Session(aws_access_key_id=creds["AccessKeyId"],
                                aws_secret_access_key=creds["SecretAccessKey"],
                                aws_session_token=creds["SessionToken"], region_name=region)
        return session.client("bedrock-agent")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info("task", "initialize", "auth_default",
             "Using default AWS credential chain (instance profile / ECS task role / env / config)")
    session = boto3.Session(region_name=region)
    return session.client("bedrock-agent")


# ---------------------------------------------------------------------------
# Operator methods
# ---------------------------------------------------------------------------

def initialize(least_action_task_object):
    """
    Build and verify the Bedrock Agent boto3 client.
    Returns: boto3 bedrock-agent client
    """
    try:
        connection = least_action_task_object.get("connection", {})
        task_laui = least_action_task_object.get("laui")
        log_info("task", "initialize", "start", f"Initializing AWSBedrockCreateKnowledgeBase for task: {task_laui}")
        client = _build_bedrock_agent_client(connection)
        region = connection.get("region", "us-east-1")
        log_info("task", "initialize", "verify_connection", f"Verifying connectivity in region: {region}")
        client.list_knowledge_bases(maxResults=1)
        log_info("task", "initialize", "connection_established", f"Bedrock Agent client ready for region: {region}")
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
    Creates a Bedrock Knowledge Base.

    Payload fields:
        name                          (str, required)  -- Name for the knowledge base
        role_arn                      (str, required)  -- IAM role ARN for Bedrock access
        knowledge_base_configuration  (dict, required) -- Type and config (e.g. VECTOR with embedding model)
        storage_configuration         (dict, required) -- Vector store config (e.g. OpenSearch Serverless)
        description                   (str, optional)  -- Human-readable description
        client_token                  (str, optional)  -- Idempotency token
        tags                          (dict, optional) -- Key-value tag pairs

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

        name = payload.get("name")
        role_arn = payload.get("role_arn")
        knowledge_base_configuration = payload.get("knowledge_base_configuration")
        storage_configuration = payload.get("storage_configuration")

        for field, val in [("name", name), ("role_arn", role_arn),
                            ("knowledge_base_configuration", knowledge_base_configuration),
                            ("storage_configuration", storage_configuration)]:
            if not val:
                log_error("task", "run", "validation_error", f"{field} is required")
                return {"status": "failed", "execution_type": "async", "result": None,
                        "error": f"{field} is required"}

        kwargs = {
            "name": name,
            "roleArn": role_arn,
            "knowledgeBaseConfiguration": knowledge_base_configuration,
            "storageConfiguration": storage_configuration,
        }
        if payload.get("description"):
            kwargs["description"] = payload["description"]
        if payload.get("client_token"):
            kwargs["clientToken"] = payload["client_token"]
        if payload.get("tags"):
            kwargs["tags"] = payload["tags"]

        log_info("task", "run", "creating_knowledge_base", f"Creating Bedrock knowledge base: {name}")
        response = client.create_knowledge_base(**kwargs)
        kb = response.get("knowledgeBase", {})
        kb_id = kb.get("knowledgeBaseId", "")
        kb_arn = kb.get("knowledgeBaseArn", "")
        log_info("task", "run", "knowledge_base_created", f"Knowledge base creation initiated: {kb_id}")

        return {"status": "pending", "execution_type": "async",
                "result": {"knowledge_base_id": kb_id, "knowledge_base_arn": kb_arn, "name": name}}

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
    Polls the knowledge base status until ACTIVE or FAILED.
    Returns: dict with status (success|pending|failed), message, output
    """
    if run_details.get("status") == "failed":
        log_error("task", "check_completion", "run_phase_failed", f"Run phase reported failure: {run_details.get('error')}")
        return {"status": "failed", "message": f"Knowledge base creation failed to start: {run_details.get('error')}", "output": None}

    kb_id = run_details.get("result", {}).get("knowledge_base_id")
    if not kb_id:
        return {"status": "failed", "message": "No knowledge_base_id in run_details", "output": None}

    try:
        response = client.get_knowledge_base(knowledgeBaseId=kb_id)
        kb = response.get("knowledgeBase", {})
        aws_status = kb.get("status", "Unknown")
        log_info("task", "check_completion", "kb_status", f"Knowledge base {kb_id} status: {aws_status}")

        if aws_status == "ACTIVE":
            return {"status": "success", "message": "Knowledge base is ACTIVE",
                    "output": {"knowledge_base_id": kb_id,
                               "knowledge_base_arn": kb.get("knowledgeBaseArn", ""),
                               "status": aws_status}}
        elif aws_status == "FAILED":
            failure_reasons = kb.get("failureReasons", ["Unknown"])
            return {"status": "failed", "message": f"Knowledge base FAILED: {failure_reasons}",
                    "output": {"knowledge_base_id": kb_id, "status": aws_status}}
        else:
            return {"status": "pending", "message": f"Knowledge base status: {aws_status}", "output": {}}

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
                log_info("task", "finish", "client_closed", "Bedrock Agent boto3 client closed successfully")
            except Exception as close_error:
                log_error("task", "finish", "client_close_error", f"Error closing client: {str(close_error)}")
        if final_status == "success":
            output = completion_details.get("output", {})
            log_info("task", "finish", "operation_summary",
                     f"Knowledge base {output.get('knowledge_base_id', 'unknown')} is now ACTIVE")
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
    "name": "my-knowledge-base",                               # required
    "role_arn": "arn:aws:iam::123456789012:role/BedrockRole",  # required
    "knowledge_base_configuration": {                           # required
        "type": "VECTOR",
        "vectorKnowledgeBaseConfiguration": {
            "embeddingModelArn": "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
        }
    },
    "storage_configuration": {                                  # required
        "type": "OPENSEARCH_SERVERLESS",
        "opensearchServerlessConfiguration": {
            "collectionArn": "arn:aws:aoss:us-east-1:123456789012:collection/my-collection",
            "vectorIndexName": "my-index",
            "fieldMapping": {"vectorField": "embedding", "textField": "text", "metadataField": "metadata"}
        }
    },
    # "description": "My RAG knowledge base",                   # optional
    # "client_token": "unique-token-123",                       # optional — idempotency token
    # "tags": {"project": "my-project"},                        # optional — key-value tag pairs
}

prompt = (
    "Creates a Bedrock Knowledge Base for RAG. Async — polls until ACTIVE or FAILED. "
    "Provide name, role_arn, knowledge_base_configuration (type + embedding model), "
    "storage_configuration (vector store such as OpenSearch Serverless). "
    "Optional: description, client_token, tags."
)

install_docs = """## Dependencies
- boto3>=1.28.0
- botocore>=1.31.0

## IAM Permissions Required
- bedrock:CreateKnowledgeBase
- bedrock:GetKnowledgeBase
- bedrock:ListKnowledgeBases
- iam:PassRole on the role_arn
- aoss:APIAccessAll on the OpenSearch Serverless collection (if using AOSS)
"""

guide_docs = """## What it does

Creates an AWS Bedrock Knowledge Base backed by a vector store using the bedrock-agent API. The call returns immediately with a Knowledge Base ID — the operator then polls `get_knowledge_base` in `check_completion` until the status reaches `ACTIVE` or `FAILED`. The Knowledge Base is the top-level container for RAG; after creation you must add a data source and run ingestion before it is queryable.

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
| region                | Yes      | AWS region where the Knowledge Base will be created |
| aws_access_key_id     | No       | Explicit access key (use with secret_access_key) |
| aws_secret_access_key | No       | Explicit secret key                              |
| aws_session_token     | No       | Session token for temporary credentials          |
| assume_iam_role       | No       | IAM role ARN to assume via STS                   |

---

## Payload

| Field                          | Required | Description                                                                                     |
|--------------------------------|----------|-------------------------------------------------------------------------------------------------|
| name                           | Yes      | Name for the Knowledge Base                                                                     |
| role_arn                       | Yes      | IAM role ARN that Bedrock will use — needs `bedrock:InvokeModel` and `s3:GetObject`             |
| knowledge_base_configuration   | Yes      | Type and embedding config — e.g. `{"type": "VECTOR", "vectorKnowledgeBaseConfiguration": {...}}`|
| storage_configuration          | Yes      | Vector store config — OpenSearch Serverless, Pinecone, Redis, Aurora, or Bedrock-managed        |
| description                    | No       | Human-readable description of the Knowledge Base                                                |
| client_token                   | No       | Idempotency token — safe to resubmit if the network fails                                       |
| tags                           | No       | Dict of `{"key": "value"}` tag pairs                                                            |

---

## Output (on success)

```json
{
  "knowledge_base_id": "ABCDE12345",
  "knowledge_base_arn": "arn:aws:bedrock:us-east-1:123456789012:knowledge-base/ABCDE12345",
  "status": "ACTIVE"
}
```

| Field               | Description                                                  |
|---------------------|--------------------------------------------------------------|
| knowledge_base_id   | Unique ID of the created Knowledge Base                      |
| knowledge_base_arn  | Full ARN of the Knowledge Base                               |
| status              | Final AWS status (`ACTIVE`)                                  |

---

## Scenarios and Edge Cases

**Vector store not configured** — `storage_configuration` must point to an existing vector store. Supported backends: OpenSearch Serverless, Pinecone, Redis Enterprise, Amazon Aurora (pgvector), or Bedrock-managed vector store. The vector store must be provisioned and accessible before creating the KB.

**IAM role permissions** — The `role_arn` passed in the payload is the role Bedrock assumes at query time. It must have `bedrock:InvokeModel` for the embedding model and `s3:GetObject` on any S3 data sources you plan to attach. Missing permissions cause a `FAILED` status.

**KB status transitions** — After creation, the KB briefly enters `CREATING` before becoming `ACTIVE`. `check_completion` polls until one of these terminal states is reached.

---

## What this operator does NOT do

- Does not create the vector store backend — OpenSearch Serverless, Pinecone, or other stores must exist before calling this operator
- Does not ingest data — after creation use AWSBedrockCreateDataSource then AWSBedrockIngestData to populate the Knowledge Base
"""

description = """Creates a Bedrock Knowledge Base for Retrieval-Augmented Generation (RAG). Async — polls until ACTIVE."""

publisher = "LeastActionLabs"
metadata = {"service": "Bedrock", "category": "AI/ML", "tags": ["bedrock", "knowledge-base", "rag", "aws"],
            "airflow_equivalent": "BedrockCreateKnowledgeBaseOperator"}
version_details = {"version": "0.0.0", "core": ["0.*"]}
verified = False
status = "draft"
publisher_notes = """## Notes\n\nThis operator has been reviewed and tested by LeastActionLabs.\n"""
