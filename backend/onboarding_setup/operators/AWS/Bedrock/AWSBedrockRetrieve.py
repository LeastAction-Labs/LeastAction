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
AWSBedrockRetrieve operator.
Retrieves relevant document chunks from a Bedrock Knowledge Base without generating a response.
Synchronous.
"""
import json
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from src.common.logger.logger import log_error, log_info


def _build_bedrock_agent_runtime_client(connection):
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
            RoleSessionName=connection.get("role_session_name", "LeastActionBedrockRuntimeSession"),
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

    return session.client("bedrock-agent-runtime")


def initialize(connection, **kwargs):
    """
    Build the bedrock-agent-runtime client.
    bedrock-agent-runtime has no cheap list call, so connectivity check is skipped.
    Raises on any auth or configuration failure.
    """
    client = None
    try:
        client = _build_bedrock_agent_runtime_client(connection)
        log_info("AWSBedrockRetrieve: bedrock-agent-runtime client built, skipping connectivity check.")
        return {"client": client}
    except (BotoCoreError, ClientError) as exc:
        log_error(f"AWSBedrockRetrieve initialize failed: {exc}")
        if client:
            client.close()
        raise


def run(client, payload, **kwargs):
    """
    Retrieve relevant document chunks from a Bedrock Knowledge Base.

    Payload fields:
        query_text        (str)   # required — the search query
        knowledge_base_id (str)   # required — ID of the Knowledge Base to search
        number_of_results (int)   # optional — how many results to return (default: 5)
        search_type       (str)   # optional — HYBRID or SEMANTIC (default: HYBRID)
        filter            (dict)  # optional — metadata filter expression
    """
    query_text = payload.get("query_text")                # required
    knowledge_base_id = payload.get("knowledge_base_id")  # required
    number_of_results = payload.get("number_of_results")  # optional — how many results to return (default: 5)
    search_type = payload.get("search_type")              # optional — HYBRID or SEMANTIC (default: HYBRID)
    filter_expr = payload.get("filter")                   # optional — metadata filter expression

    if not query_text:
        raise ValueError("payload.query_text is required")
    if not knowledge_base_id:
        raise ValueError("payload.knowledge_base_id is required")

    retrieval_config = {
        "vectorSearchConfiguration": {
            "numberOfResults": number_of_results or 5,
        }
    }
    if search_type:
        retrieval_config["vectorSearchConfiguration"]["overrideSearchType"] = search_type
    if filter_expr:
        retrieval_config["vectorSearchConfiguration"]["filter"] = filter_expr

    try:
        response = client.retrieve(
            knowledgeBaseId=knowledge_base_id,
            retrievalQuery={"text": query_text},
            retrievalConfiguration=retrieval_config,
        )
        results = [
            {
                "content": r["content"]["text"],
                "score": r.get("score", 0),
                "location": r.get("location", {}),
                "metadata": r.get("metadata", {}),
            }
            for r in response.get("retrievalResults", [])
        ]
        log_info(f"AWSBedrockRetrieve: retrieved {len(results)} results for query={query_text!r}")
        return {
            "status": "success",
            "execution_type": "sync",
            "result": {
                "results": results,
                "query_text": query_text,
                "count": len(results),
            },
        }
    except (BotoCoreError, ClientError) as exc:
        log_error(f"AWSBedrockRetrieve run failed: {exc}")
        raise


def check_completion(client, run_details, payload, **kwargs):
    """
    Sync passthrough — retrieve completes in a single API call.

    Checks run_details.status == "failed" first, then passes through the result.
    """
    if run_details.get("status") == "failed":
        return {"status": "failed", "result": run_details.get("result", {})}

    return {"status": run_details.get("status", "success"), "result": run_details.get("result", {})}


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
                log_info("task", "finish", "client_closed", "Bedrock Agent Runtime boto3 client closed successfully")
            except Exception as close_error:
                log_error("task", "finish", "client_close_error", f"Error closing client: {str(close_error)}")
        if final_status == "success":
            output = completion_details.get("output", {})
            log_info("task", "finish", "operation_summary",
                     f"Retrieve completed — {output.get('result_count', 0)} result(s) returned")
        elif final_status == "failed":
            log_error("task", "finish", "operation_failed", f"Retrieve failed: {completion_details.get('message')}")
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
    "query_text": "What is the refund policy?",  # required
    "knowledge_base_id": "XXXXXXXXXX",           # required
    # "number_of_results": 5,                    # optional — how many chunks to return (default: 5)
    # "search_type": "HYBRID",                   # optional — HYBRID or SEMANTIC (default: HYBRID)
    # "filter": {},                              # optional — metadata filter expression
}

prompt = (
    "Retrieve relevant document chunks from a Bedrock Knowledge Base without generating a response. "
    "Provide query_text and knowledge_base_id. "
    "Optional: number_of_results, search_type (HYBRID/SEMANTIC), filter."
)

install_docs = """## Installation

Requires `boto3` (included in the base Lambda/EC2 environment).

```bash
pip install boto3
```

IAM permissions required:
- `bedrock:Retrieve`
"""

guide_docs = """## What it does

Retrieves relevant document chunks from a Bedrock Knowledge Base without generating a response, using the bedrock-agent-runtime API. The operator is synchronous and returns a ranked list of results — each with the chunk content, a relevance score (0-1), the source location (S3 path or web URL), and metadata. Use this operator when you want to handle the generation step yourself, apply custom re-ranking, or display raw source passages to users.

---

## Auth

1. **Explicit credentials** — set `aws_access_key_id` and `aws_secret_access_key` in the connection. An optional `aws_session_token` can be included for temporary credentials.
2. **Assume IAM role via STS** — set `role_arn` in the connection. The operator assumes the role via STS before calling bedrock-agent-runtime.
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
  "role_arn": "arn:aws:iam::123456789012:role/BedrockRuntimeRole"
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
| region                | Yes      | AWS region where the Knowledge Base exists           |
| aws_access_key_id     | No       | Explicit access key (use with secret_access_key)     |
| aws_secret_access_key | No       | Explicit secret key                                  |
| aws_session_token     | No       | Session token for temporary credentials              |
| role_arn              | No       | IAM role ARN to assume via STS                       |

---

## Payload

| Field              | Required | Description                                                                                  |
|--------------------|----------|----------------------------------------------------------------------------------------------|
| query_text         | Yes      | The search query to run against the Knowledge Base                                           |
| knowledge_base_id  | Yes      | ID of the Knowledge Base to search                                                           |
| number_of_results  | No       | Number of chunks to return (default: 5)                                                      |
| search_type        | No       | `HYBRID` (default) or `SEMANTIC` — controls the retrieval algorithm                         |
| filter             | No       | Metadata filter expression to restrict results to a subset of documents                      |

---

## Output (on success)

```json
{
  "query_text": "What is the refund policy?",
  "results": [
    {
      "content": "Items may be returned within 30 days of purchase...",
      "score": 0.87,
      "location": {"s3Location": {"uri": "s3://my-bucket/docs/returns.pdf"}},
      "metadata": {"page": "3", "department": "customer-service"}
    }
  ],
  "result_count": 1
}
```

| Field        | Description                                                                  |
|--------------|------------------------------------------------------------------------------|
| query_text   | The search query as provided in the payload                                  |
| results      | Ranked list of document chunks with content, score, location, and metadata   |
| result_count | Number of results returned                                                   |

---

## Scenarios and Edge Cases

**Empty KB returns empty list** — If the Knowledge Base has no ingested data, `results` will be an empty list and `result_count` will be 0. Ingest data using AWSBedrockIngestData first.

**HYBRID vs SEMANTIC trade-offs** — `HYBRID` combines semantic vector similarity with BM25 keyword matching and is recommended for most enterprise use cases. `SEMANTIC` uses vector similarity only — better for conceptual queries but may miss exact keyword lookups.

**Score threshold filtering** — The `score` field is a relevance score from 0 to 1. Scores above 0.5 are generally reliable; below 0.3 may be noise. There is no universal cutoff — tune based on your data and use case.

---

## What this operator does NOT do

- Does not generate a response — pass the returned chunks to AWSBedrockInvokeModel or your own LLM call for generation
- Does not update or ingest into the Knowledge Base
- Does not support keyword-only (BM25-only) search — minimum search mode is HYBRID
"""

description = """Retrieves relevant document chunks from a Bedrock Knowledge Base without
generating a response. Returns ranked results with content, score, location, and metadata.
Synchronous."""

publisher = "LeastActionLabs"

metadata = {
    "service": "Bedrock",
    "category": "AI/ML",
    "tags": ["bedrock", "retrieve", "knowledge-base", "search", "aws"],
    "airflow_equivalent": "BedrockRetrieveOperator",
}

version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False
status = "draft"

publisher_notes = """## Publisher Notes

**Retrieve vs RetrieveAndGenerate:** Use this operator when you want the raw document chunks without
an LLM generation step — e.g. to feed them into your own prompt, post-filter them, or display them
directly to users. Use AWSBedrockRetrieveAndGenerate when you want a ready-made answer.

**HYBRID vs SEMANTIC search:** HYBRID search combines semantic vector similarity with BM25 keyword
matching, giving better results for most enterprise workloads. SEMANTIC-only is faster but can miss
exact-match queries. Default is HYBRID.

**Score interpretation:** The `score` field is a relevance score between 0 and 1. Scores above 0.5
are generally reliable; below 0.3 may be noise. There is no universal cutoff — tune based on your
data and use case.

**Pagination:** The Bedrock Retrieve API does not support pagination in the same call. To retrieve
more chunks, increase `number_of_results`. The maximum is determined by the KB configuration
(typically 100).

**Metadata filters:** The `filter` field accepts a metadata filter expression as defined in the
Bedrock API docs. Use this to restrict results to specific document subsets (e.g. by department,
date range, or document type).
"""
