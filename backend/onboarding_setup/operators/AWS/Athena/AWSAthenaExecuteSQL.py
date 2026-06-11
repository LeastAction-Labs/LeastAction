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

codeblock = {"main.py": """
import json
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from src.common.logger.logger import log_info, log_error


def _build_athena_client(connection: dict):
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
        return session.client("athena")

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
        return session.client("athena")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info("task", "initialize", "auth_default",
             "Using default AWS credential chain (instance profile / ECS task role / env / config)")
    return boto3.Session(region_name=region).client("athena")


def initialize(least_action_task_object):
    try:
        connection = least_action_task_object.get("connection", {})
        if isinstance(connection, str):
            connection = json.loads(connection)
        log_info("task", "initialize", "building_client",
                 f"region={connection.get('region', 'us-east-1')}")
        client = _build_athena_client(connection)
        log_info("task", "initialize", "client_ready", "Athena client initialized")
        return client
    except ClientError as e:
        log_error("task", "initialize", "client_error",
                  f"{e.response['Error']['Code']}: {e.response['Error']['Message']}")
        raise
    except BotoCoreError as e:
        log_error("task", "initialize", "botocore_error", f"BotoCoreError: {str(e)}")
        raise
    except Exception as e:
        log_error("task", "initialize", "init_failed", f"Error: {str(e)}")
        raise


def run(least_action_task_object, client):
    try:
        payload = least_action_task_object.get("payload", {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                log_error("task", "run", "payload_parse_error", "Failed to parse payload as JSON")
                return {"status": "failed", "execution_type": "async", "result": None,
                        "error": "Invalid payload format - expected flat JSON object"}

        connection = least_action_task_object.get("connection", {})
        if isinstance(connection, str):
            connection = json.loads(connection)

        # sql comes from payload only
        sql = payload.get("sql") or payload.get("query")
        if not sql:
            log_error("task", "run", "missing_sql", "sql is required in payload")
            return {"status": "failed", "execution_type": "async", "result": None,
                    "error": "sql is required in payload"}

        # all other params come from connection
        output_location = connection.get("output_location")
        if not output_location:
            log_error("task", "run", "missing_output_location",
                      "output_location is required in connection")
            return {"status": "failed", "execution_type": "async", "result": None,
                    "error": "output_location is required in connection"}

        database = connection.get("database", "default")
        workgroup = connection.get("workgroup", "primary")
        client_request_token = connection.get("client_request_token")

        exec_params = {
            "QueryString": sql,
            "ResultConfiguration": {"OutputLocation": output_location},
            "QueryExecutionContext": {"Database": database},
            "WorkGroup": workgroup,
        }
        if client_request_token:
            exec_params["ClientRequestToken"] = client_request_token

        log_info("task", "run", "submitting_query",
                 f"Submitting Athena query, database: {database}, workgroup: {workgroup}, "
                 f"output: {output_location}")
        log_info("task", "run", "query_preview", f"Query (first 200 chars): {sql[:200]}")

        response = client.start_query_execution(**exec_params)
        query_execution_id = response["QueryExecutionId"]
        log_info("task", "run", "query_submitted", f"Query execution ID: {query_execution_id}")

        return {
            "status": "pending",
            "execution_type": "async",
            "result": {
                "query_execution_id": query_execution_id,
                "database": database,
                "workgroup": workgroup,
                "output_location": output_location,
            }
        }
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        log_error("task", "run", "client_error", f"Code: {error_code} - {error_message}")
        return {"status": "failed", "execution_type": "async",
                "result": {"error_code": error_code, "error_message": error_message}}
    except BotoCoreError as e:
        log_error("task", "run", "botocore_error", f"Transport error: {str(e)}")
        return {"status": "failed", "execution_type": "async", "result": {"error": str(e)}}
    except Exception as e:
        log_error("task", "run", "unexpected_error", f"Unexpected error: {str(e)}")
        return {"status": "failed", "execution_type": "async", "result": {"error": str(e)}}


def check_completion(least_action_task_object, client, run_details):
    try:
        if run_details.get("status") == "failed":
            return {"status": "failed", "message": "Query submission failed",
                    "output": run_details.get("result")}
        result = run_details.get("result", {})
        query_execution_id = result.get("query_execution_id")
        log_info("task", "check_completion", "polling_status",
                 f"Checking query execution: {query_execution_id}")
        response = client.get_query_execution(QueryExecutionId=query_execution_id)
        execution = response["QueryExecution"]
        state = execution["Status"]["State"]
        log_info("task", "check_completion", "current_status",
                 f"Query '{query_execution_id}' state: {state}")
        if state == "SUCCEEDED":
            stats = execution.get("Statistics", {})
            output_loc = execution.get("ResultConfiguration", {}).get(
                "OutputLocation", result.get("output_location"))
            data_scanned = stats.get("DataScannedInBytes", 0)
            execution_time_ms = stats.get("TotalExecutionTimeInMillis", 0)
            log_info("task", "check_completion", "query_succeeded",
                     f"Data scanned: {data_scanned} bytes, time: {execution_time_ms}ms")
            return {
                "status": "success",
                "message": f"Query succeeded in {execution_time_ms}ms, scanned {data_scanned} bytes",
                "output": {
                    "query_execution_id": query_execution_id,
                    "state": state,
                    "output_location": output_loc,
                    "data_scanned_bytes": data_scanned,
                    "execution_time_ms": execution_time_ms,
                }
            }
        if state == "FAILED":
            reason = execution["Status"].get("StateChangeReason", "Unknown reason")
            log_error("task", "check_completion", "query_failed", f"Query failed: {reason}")
            return {"status": "failed", "message": f"Query failed: {reason}",
                    "output": {"query_execution_id": query_execution_id, "state": state,
                               "reason": reason}}
        if state == "CANCELLED":
            return {"status": "failed", "message": "Query was cancelled",
                    "output": {"query_execution_id": query_execution_id, "state": state}}
        return {"status": "pending", "message": f"Query is {state}",
                "output": {"query_execution_id": query_execution_id, "state": state}}
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        log_error("task", "check_completion", "client_error",
                  f"Code: {error_code} - {error_message}")
        return {"status": "failed", "message": error_message, "output": None}
    except Exception as e:
        log_error("task", "check_completion", "unexpected_error", f"Error: {str(e)}")
        return {"status": "failed", "message": str(e), "output": None}


def finish(least_action_task_object, client, completion_details, run_details):
    'Log final outcome and release any held resources. Returns: None'
    try:
        task_laui = least_action_task_object.get("laui")
        log_info("task", "finish", "starting_cleanup", f"Starting cleanup for task: {task_laui}")
        final_status = completion_details.get("status", "unknown")
        log_info("task", "finish", "final_status", f"Task ended with status: {final_status}")
        if client:
            try:
                client.close()
                log_info("task", "finish", "client_closed", "Athena boto3 client closed successfully")
            except Exception as close_error:
                log_error("task", "finish", "client_close_error", f"Error closing client: {str(close_error)}")
        if final_status == "success":
            output = completion_details.get("output", {})
            log_info("task", "finish", "operation_summary",
                     f"Query '{output.get('query_execution_id')}' succeeded. "
                     f"Output: {output.get('output_location')}, scanned: {output.get('data_scanned_bytes')} bytes")
        elif final_status == "failed":
            log_error("task", "finish", "operation_failed", f"Operation failed: {completion_details.get('message')}")
        else:
            log_info("task", "finish", "operation_status", f"status={final_status}, message={completion_details.get('message')}")
        log_info("task", "finish", "cleanup_complete", f"Cleanup complete for task: {task_laui}")
    except Exception as e:
        log_error("task", "finish", "cleanup_error", f"Error during finish/cleanup: {str(e)}")
        # Never re-raise from finish
"""}

bashblock = {"main.sh": """#!/bin/bash
set -e
pip install boto3>=1.28.0
pip install botocore>=1.31.0
echo "Dependencies installed successfully"
"""}

connection = {
    "region": "us-east-1",
    "output_location": "s3://my-bucket/athena-results/",  # required - S3 path for query results
    # "database": "default",                              # optional - Glue database (default: "default")
    # "workgroup": "primary",                             # optional - Athena workgroup (default: "primary")
    # "client_request_token": "unique-token-123",         # optional - idempotency token
}

payload = {
    "sql": "SELECT 1",  # required - SQL query to execute
}

prompt = (
    "Execute an Athena SQL query and poll asynchronously until SUCCEEDED. "
    "Payload: sql only (required). "
    "All other config in connection: output_location (required), database (default 'default'), "
    "workgroup (default 'primary'), client_request_token (optional). "
    "Auth: explicit keys first, then assume_iam_role via STS, then default credential chain. "
    "Return query_execution_id, output_location, data_scanned_bytes, execution_time_ms. "
    "Catch FAILED/CANCELLED as status:failed. finish() must close the boto3 client."
)

install_docs = """# AWSAthenaExecuteSQL - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "athena:StartQueryExecution",
        "athena:GetQueryExecution",
        "s3:PutObject",
        "s3:GetObject",
        "s3:GetBucketLocation"
      ],
      "Resource": "*"
    }

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| Explicit keys | Set aws_access_key_id and aws_secret_access_key in connection |
| Assume role   | Set assume_iam_role ARN in connection                         |
| Default chain | EC2 instance profile, ECS task role, env vars, ~/.aws         |
"""

guide_docs = """# AWSAthenaExecuteSQL - Operator Guide

## What it does

Submits an SQL query to Amazon Athena and polls asynchronously until SUCCEEDED or a terminal
failure state. Payload contains only the SQL - all configuration lives in the connection field.
Equivalent to Airflow's AthenaOperator.

---

## Auth

Three methods, evaluated in priority order:
1. **Access keys** - aws_access_key_id + aws_secret_access_key in connection
2. **Assume IAM role** - assume_iam_role (ARN) in connection, assumed via STS
3. **Default credential chain** - instance profile, ECS task role, env vars, ~/.aws/credentials

---

## Connection

    {
      "region": "us-east-1",
      "output_location": "s3://my-bucket/athena-results/"
    }

| Field                 | Required   | Description                                              |
|-----------------------|------------|----------------------------------------------------------|
| region                | Yes        | AWS region                                               |
| output_location       | Yes        | S3 path for query result files                           |
| database              | No         | Glue database name (default: "default")                  |
| workgroup             | No         | Athena workgroup (default: "primary")                    |
| client_request_token  | No         | Idempotency token - same token reuses existing execution |
| aws_access_key_id     | Scenario 1 | IAM user access key                                      |
| aws_secret_access_key | Scenario 1 | IAM user secret key                                      |
| aws_session_token     | No         | Temporary session token for STS-issued credentials       |
| assume_iam_role       | Scenario 2 | Role ARN to assume via STS                               |

---

## Payload

    {"sql": "SELECT COUNT(*) FROM my_table"}

| Field | Required | Description                                    |
|-------|----------|------------------------------------------------|
| sql   | Yes      | SQL query to execute (also accepts key: query) |

---

## Output (on success)

    {
      "query_execution_id": "abc123...",
      "state": "SUCCEEDED",
      "output_location": "s3://my-bucket/athena-results/abc123.csv",
      "data_scanned_bytes": 1234,
      "execution_time_ms": 987
    }

---

## What this operator does NOT do

- Does not return query result rows (fetch separately via Athena GetQueryResults API)
- Does not create databases or tables
"""

description = """
Executes an Athena SQL query and polls asynchronously until SUCCEEDED. Equivalent to Airflow's
AthenaOperator. Required: sql, output_location (in payload or connection). Optional: database
(default 'default'), workgroup (default 'primary'), client_request_token. Auth: explicit keys,
assume IAM role, or default chain. Returns query_execution_id, output_location,
data_scanned_bytes, execution_time_ms.
"""

publisher = "LeastActionLabs"

verified = False
status = "draft"

publisher_notes = """## Publisher Notes

**Payload is SQL only** - all configuration (output_location, database, workgroup,
client_request_token) lives in the connection field. This keeps the payload clean for dynamic
SQL use cases where only the query changes between runs while the Athena environment stays constant.

**output_location** is required in connection - results are stored as CSV files in S3 at this
prefix, with the query execution ID as the filename. The calling IAM identity needs
`s3:PutObject` on this bucket.

**client_request_token** in connection enables query deduplication - if the same token is used
in two calls within 24 hours, the second call returns the existing execution ID without running
a second query. Useful for idempotent pipeline retries.

**Result rows**: this operator returns only query metadata (execution ID, bytes scanned, runtime).
To fetch actual rows from a SELECT, use the Athena `get_query_results` API with the returned
`query_execution_id`.
"""

metadata = {
    "service": "Athena",
    "category": "Analytics",
    "tags": ["athena", "sql", "query", "analytics", "aws"],
    "airflow_equivalent": "AthenaOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
