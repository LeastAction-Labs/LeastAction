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
AWSBedrockRetrieveAndGenerate operator.
Queries a Bedrock Knowledge Base and generates a grounded response using RAG
(Retrieve and Generate). Synchronous.
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
        log_info("AWSBedrockRetrieveAndGenerate: bedrock-agent-runtime client built, skipping connectivity check.")
        return {"client": client}
    except (BotoCoreError, ClientError) as exc:
        log_error(f"AWSBedrockRetrieveAndGenerate initialize failed: {exc}")
        if client:
            client.close()
        raise


def run(client, payload, **kwargs):
    """
    Execute a Retrieve and Generate (RAG) query against a Bedrock Knowledge Base.

    Payload fields:
        input_text               (str)   # required — the user query or prompt
        knowledge_base_id        (str)   # required — ID of the Knowledge Base to retrieve from
        model_arn                (str)   # required — ARN of the foundation model for generation
        retrieval_configuration  (dict)  # optional — e.g. {"vectorSearchConfiguration": {"numberOfResults": 5}}
        generation_configuration (dict)  # optional — model inference parameters
        session_id               (str)   # optional — session ID for multi-turn conversations
    """
    input_text = payload.get("input_text")                          # required
    knowledge_base_id = payload.get("knowledge_base_id")            # required
    model_arn = payload.get("model_arn")                            # required
    retrieval_configuration = payload.get("retrieval_configuration") # optional — e.g. {"vectorSearchConfiguration": {"numberOfResults": 5}}
    generation_configuration = payload.get("generation_configuration") # optional — model inference parameters
    session_id = payload.get("session_id")                          # optional — session ID for multi-turn conversations

    if not input_text:
        raise ValueError("payload.input_text is required")
    if not knowledge_base_id:
        raise ValueError("payload.knowledge_base_id is required")
    if not model_arn:
        raise ValueError("payload.model_arn is required")

    kb_config = {
        "knowledgeBaseId": knowledge_base_id,
        "modelArn": model_arn,
    }
    if retrieval_configuration:
        kb_config["retrievalConfiguration"] = retrieval_configuration
    if generation_configuration:
        kb_config["generationConfiguration"] = generation_configuration

    call_kwargs = {
        "input": {"text": input_text},
        "retrieveAndGenerateConfiguration": {
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": kb_config,
        },
    }
    if session_id:
        call_kwargs["sessionId"] = session_id

    try:
        response = client.retrieve_and_generate(**call_kwargs)
        output_text = response["output"]["text"]
        citations = response.get("citations", [])
        returned_session_id = response.get("sessionId", "")
        log_info(
            f"AWSBedrockRetrieveAndGenerate: RAG complete — "
            f"citations={len(citations)}, session_id={returned_session_id}"
        )
        return {
            "status": "success",
            "execution_type": "sync",
            "result": {
                "output_text": output_text,
                "citations": citations,
                "session_id": returned_session_id,
            },
        }
    except (BotoCoreError, ClientError) as exc:
        log_error(f"AWSBedrockRetrieveAndGenerate run failed: {exc}")
        raise


def check_completion(client, run_details, payload, **kwargs):
    """
    Sync passthrough — retrieve_and_generate completes in a single API call.

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
            log_info("task", "finish", "operation_summary", "RetrieveAndGenerate completed successfully")
        elif final_status == "failed":
            log_error("task", "finish", "operation_failed", f"RetrieveAndGenerate failed: {completion_details.get('message')}")
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
    "input_text": "What is the return policy?",                                                     # required
    "knowledge_base_id": "XXXXXXXXXX",                                                              # required
    "model_arn": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",  # required
    # "retrieval_configuration": {"vectorSearchConfiguration": {"numberOfResults": 5}},             # optional — tune retrieval
    # "generation_configuration": {},                                                               # optional — model inference params
    # "session_id": "session-abc123",                                                               # optional — for multi-turn conversations
}

prompt = (
    "Query a Bedrock Knowledge Base and generate a grounded answer using RAG. "
    "Provide input_text, knowledge_base_id, and model_arn. "
    "Optional: retrieval_configuration, generation_configuration, session_id for multi-turn."
)

install_docs = """## Installation

Requires `boto3` (included in the base Lambda/EC2 environment).

```bash
pip install boto3
```

IAM permissions required:
- `bedrock:RetrieveAndGenerate`
- `bedrock:Retrieve`
"""

guide_docs = """## What it does

Queries a Bedrock Knowledge Base and generates a grounded response using Retrieval-Augmented Generation (RAG) via the bedrock-agent-runtime API. The operator is synchronous — it retrieves relevant document chunks from the Knowledge Base, feeds them to the specified foundation model, and returns the generated text along with citations showing exactly which source chunks were used. Pass `session_id` from a previous response to continue a multi-turn conversation.

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
| region                | Yes      | AWS region where the Knowledge Base and model exist  |
| aws_access_key_id     | No       | Explicit access key (use with secret_access_key)     |
| aws_secret_access_key | No       | Explicit secret key                                  |
| aws_session_token     | No       | Session token for temporary credentials              |
| role_arn              | No       | IAM role ARN to assume via STS                       |

---

## Payload

| Field                    | Required | Description                                                                                                              |
|--------------------------|----------|--------------------------------------------------------------------------------------------------------------------------|
| input_text               | Yes      | The user query or prompt to answer using the Knowledge Base                                                              |
| knowledge_base_id        | Yes      | ID of the Knowledge Base to retrieve from                                                                                |
| model_arn                | Yes      | Full ARN of the foundation model — e.g. `arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0` |
| retrieval_configuration  | No       | Tune retrieval — e.g. `{"vectorSearchConfiguration": {"numberOfResults": 5}}`                                           |
| generation_configuration | No       | Model inference parameters such as temperature or max tokens                                                             |
| session_id               | No       | Session ID from a previous response — pass to continue a multi-turn conversation                                         |

---

## Output (on success)

```json
{
  "output_text": "The return policy allows returns within 30 days of purchase...",
  "citations": [
    {
      "retrievedReferences": [
        {
          "content": {"text": "Items may be returned within 30 days..."},
          "location": {"s3Location": {"uri": "s3://my-bucket/docs/returns.pdf"}}
        }
      ]
    }
  ],
  "session_id": "session-abc123"
}
```

| Field       | Description                                                                |
|-------------|----------------------------------------------------------------------------|
| output_text | The generated answer grounded in the retrieved Knowledge Base content      |
| citations   | List of source chunks used — includes content snippet and S3/web location  |
| session_id  | Session ID to reuse for the next turn in a multi-turn conversation         |

---

## Scenarios and Edge Cases

**Model not enabled** — `AccessDeniedException` is raised if the foundation model has not been enabled in your account for the target region. Go to the Bedrock console → Model access → enable the model before use.

**KB is empty** — If no relevant chunks are found, the model answers from its training data alone and `citations` will be empty. Ingest data into the Knowledge Base first using AWSBedrockIngestData.

**Multi-turn conversations** — Pass the `session_id` returned from a previous call to continue a conversation. Bedrock maintains context server-side. Sessions expire after a period of inactivity.

**Model ARN format** — Must be the full ARN including region, not just the model ID. The region in the ARN must match the region where the Knowledge Base exists. Pattern: `arn:aws:bedrock:<region>::foundation-model/<model-id>`.

---

## What this operator does NOT do

- Does not update the Knowledge Base or ingest new documents
- Does not manage conversation history beyond passing `session_id` — prior turns are held server-side by Bedrock and are not returned in the response
"""

description = """Queries a Bedrock Knowledge Base and generates a grounded response using RAG
(Retrieve and Generate). Returns the output text, citations, and session ID. Synchronous."""

publisher = "LeastActionLabs"

metadata = {
    "service": "Bedrock",
    "category": "AI/ML",
    "tags": ["bedrock", "rag", "knowledge-base", "generate", "aws"],
    "airflow_equivalent": "BedrockRetrieveAndGenerateOperator",
}

version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False
status = "draft"

publisher_notes = """## Publisher Notes

**Model ARN format:** Must be the full ARN, not just the model ID. The region in the ARN must match
the region where the Knowledge Base exists. Cross-region ARNs are not supported for RetrieveAndGenerate.

**Model enablement:** The foundation model must be explicitly enabled in your AWS account for the
target region. Go to Bedrock -> Model access -> enable the model before use.

**Citations:** The `citations` list in the output contains the retrieved passage chunks used for
generation. Each citation includes the source location (S3 path or web URL) and the text snippet.
Use these for attribution and to debug unexpected answers.

**Multi-turn sessions:** Pass `session_id` from a previous response to continue a conversation.
Bedrock maintains context on the server side for a limited time. Sessions expire after inactivity.

**Billing:** This call incurs two types of charges — retrieval (KB query) and model invocation
(token-based pricing). For high-volume use cases, consider AWSBedrockRetrieve + your own generation
loop to batch and optimize costs.

**No streaming:** RetrieveAndGenerate is a blocking call that returns the full response at once.
For streaming output, use the InvokeModelWithResponseStream API instead.
"""
