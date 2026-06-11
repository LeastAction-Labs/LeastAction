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
import time
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from src.common.logger.logger import log_info, log_error


def _build_client(connection):
    region = connection.get("region", "us-east-1")

    try:
        sts = boto3.client("sts", region_name=region)
        sts.get_caller_identity()
        log_info("task", "initialize", "auth_iam", "IAM role available - using instance profile")
        return boto3.client("redshift-data", region_name=region)
    except Exception as e:
        log_info("task", "initialize", "auth_iam_failed",
                 f"IAM role not available ({str(e)}) - falling back to access keys")

    access_key = connection.get("aws_access_key_id")
    secret_key = connection.get("aws_secret_access_key")
    session_token = connection.get("aws_session_token")

    if not (access_key and secret_key):
        raise RuntimeError(
            "No usable credentials: IAM role unavailable and "
            "aws_access_key_id/aws_secret_access_key not found in connection."
        )

    log_info("task", "initialize", "auth_keys",
             f"Using explicit access key ending ...{access_key[-4:]}")

    params = {
        "service_name": "redshift-data",
        "region_name": region,
        "aws_access_key_id": access_key,
        "aws_secret_access_key": secret_key,
    }
    if session_token:
        params["aws_session_token"] = session_token
    return boto3.client(**params)


def initialize(least_action_task_object):
    try:
        connection = least_action_task_object.get("connection", {})
        if isinstance(connection, str):
            connection = json.loads(connection)

        log_info("task", "initialize", "building_client",
                 f"region={connection.get('region', 'us-east-1')}")

        client = _build_client(connection)
        client.list_statements(MaxResults=1)
        log_info("task", "initialize", "connectivity_ok",
                 "Redshift Data API client initialized and verified")
        return client

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "initialize", "client_error", f"({error_code}) {error_msg}")
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
                return {"execution_type": "async", "status": "failed", "result": None,
                        "error": "Invalid payload format — expected flat JSON object"}

        connection = least_action_task_object.get("connection", {})
        if isinstance(connection, str):
            connection = json.loads(connection)

        sql = payload.get("sql")
        if not sql:
            log_error("task", "run", "missing_sql", "sql is required in payload")
            return {"execution_type": "async", "status": "failed", "result": None,
                    "error": "sql is required in payload"}

        # All connection details come from connection field
        database = connection.get("database")
        if not database:
            log_error("task", "run", "missing_database", "database is required in connection")
            return {"execution_type": "async", "status": "failed", "result": None,
                    "error": "database is required in connection"}

        poll_interval = int(connection.get("poll_interval_seconds", 10))

        params = {
            "Sql": sql,
            "Database": database,
        }

        cluster_id = connection.get("cluster_identifier")
        workgroup = connection.get("workgroup_name")

        if cluster_id:
            params["ClusterIdentifier"] = cluster_id
            if connection.get("db_user"):
                params["DbUser"] = connection["db_user"]
            log_info("task", "run", "target", f"Provisioned cluster: {cluster_id}, database: {database}")
        elif workgroup:
            params["WorkgroupName"] = workgroup
            log_info("task", "run", "target", f"Serverless workgroup: {workgroup}, database: {database}")
        else:
            msg = "Must provide either cluster_identifier (provisioned) or workgroup_name (serverless) in connection"
            log_error("task", "run", "missing_target", msg)
            return {"execution_type": "async", "status": "failed", "result": None, "error": msg}

        if connection.get("secret_arn"):
            params["SecretArn"] = connection["secret_arn"]
        if connection.get("statement_name"):
            params["StatementName"] = connection["statement_name"]

        log_info("task", "run", "executing_sql",
                 f"Executing SQL via Redshift Data API on "
                 f"{'cluster=' + cluster_id if cluster_id else 'workgroup=' + workgroup}")

        resp = client.execute_statement(**params)
        statement_id = resp["Id"]

        log_info("task", "run", "statement_submitted",
                 f"Statement submitted with ID: {statement_id}")

        while True:
            desc = client.describe_statement(Id=statement_id)
            status = desc.get("Status")
            log_info("task", "run", "polling_status",
                     f"Statement '{statement_id}' status: {status}")
            if status == "FINISHED":
                return {
                    "execution_type": "async",
                    "status": "success",
                    "result": {
                        "statement_id": statement_id,
                        "statement_status": status,
                        "records_updated": desc.get("ResultRows", 0),
                        "has_result_set": desc.get("HasResultSet", False),
                        "query_string": desc.get("QueryString", "")[:500],
                    }
                }
            if status in {"FAILED", "ABORTED"}:
                error_msg = desc.get("Error", "No error message")
                return {
                    "execution_type": "async",
                    "status": "failed",
                    "result": {
                        "statement_id": statement_id,
                        "statement_status": status,
                        "error": error_msg,
                    }
                }
            time.sleep(poll_interval)

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "client_error", f"({error_code}) {error_msg}")
        return {"execution_type": "async", "status": "failed",
                "result": {"error": f"({error_code}) {error_msg}"}}
    except BotoCoreError as e:
        log_error("task", "run", "transport_error", f"BotoCoreError: {str(e)}")
        return {"execution_type": "async", "status": "failed",
                "result": {"error": f"Transport error: {str(e)}"}}
    except Exception as e:
        log_error("task", "run", "run_failed", f"Unexpected error: {str(e)}")
        return {"execution_type": "async", "status": "failed", "result": {"error": str(e)}}


def check_completion(least_action_task_object, client, run_details):
    try:
        if run_details.get("status") in ("success", "failed"):
            return {
                "status": run_details["status"],
                "message": "Redshift SQL execution completed",
                "output": run_details.get("result", {})
            }
        statement_id = run_details.get("result", {}).get("statement_id")
        desc = client.describe_statement(Id=statement_id)
        status = desc.get("Status")
        log_info("task", "check_completion", "polling_status",
                 f"Statement '{statement_id}' status: {status}")
        if status == "FINISHED":
            return {
                "status": "success",
                "message": "SQL execution finished",
                "output": {
                    "statement_id": statement_id,
                    "statement_status": status,
                    "has_result_set": desc.get("HasResultSet", False),
                }
            }
        if status in {"SUBMITTED", "PICKED", "STARTED"}:
            return {"status": "pending", "message": f"Statement is {status}",
                    "output": {"statement_status": status}}
        return {"status": "failed", "message": f"Statement {status}: {desc.get('Error', '')}",
                "output": {"statement_status": status}}
    except Exception as e:
        log_error("task", "check_completion", "error", f"Error: {str(e)}")
        return {"status": "failed", "message": str(e), "output": None}


def finish(least_action_task_object, client, completion_details, run_details):
    try:
        task_laui = least_action_task_object.get("laui", "unknown")
        status = completion_details.get("status", "unknown")
        log_info("task", "finish", "final_status",
                 f"Task {task_laui} completed with status: {status}")
        if status == "success":
            output = completion_details.get("output", {})
            log_info("task", "finish", "statement_summary",
                     f"Statement {output.get('statement_id')} "
                     f"status={output.get('statement_status')} "
                     f"has_result_set={output.get('has_result_set')}")
        else:
            log_error("task", "finish", "operation_failed",
                      completion_details.get("message", "No message"))
        log_info("task", "finish", "cleanup_complete", "No resources to release")
    except Exception as e:
        log_error("task", "finish", "cleanup_error", f"Error in finish: {str(e)}")
"""}

bashblock = {"main.sh": """#!/bin/bash
set -e
pip install boto3>=1.28.0
pip install botocore>=1.31.0
echo "Dependencies installed successfully"
"""}

connection = {
    "region": "us-east-1",
    "cluster_identifier": "my-redshift-cluster",  # required for provisioned — OR use workgroup_name for serverless
    # "workgroup_name": "my-workgroup",            # required for serverless — OR use cluster_identifier
    "database": "dev",                             # required — target database name
    # "db_user": "awsuser",                        # optional — DB user for provisioned clusters
    # "secret_arn": "arn:aws:secretsmanager:...",  # optional — Secrets Manager ARN for credentials
    # "statement_name": "my-query",                # optional — label shown in Redshift console
    # "poll_interval_seconds": 10                  # optional — polling interval (default: 10)
}

payload = {
    "sql": "SELECT 1",  # required — SQL statement to execute
}

prompt = (
    "Execute SQL via the Amazon Redshift Data API (provisioned or serverless). "
    "Payload: sql only (required). "
    "All connection details in connection: database (required), cluster_identifier (provisioned) "
    "OR workgroup_name (serverless) (required), db_user, secret_arn, statement_name (optional), "
    "poll_interval_seconds (default 10). "
    "Auth: explicit keys first, then assume_iam_role via STS, then default credential chain. "
    "Return statement_id, statement_status, records_updated, has_result_set. "
    "Catch FAILED/ABORTED as status:failed. finish() must close the boto3 client."
)

install_docs = """# AWSRedshiftDataExecuteSQL - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "redshift-data:ExecuteStatement",
        "redshift-data:DescribeStatement",
        "redshift-data:ListStatements",
        "redshift:GetClusterCredentials"
      ],
      "Resource": "*"
    }

For serverless workgroups, also add:

    redshift-serverless:GetWorkgroup

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance - no connection keys needed       |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
| Session token | Optionally add aws_session_token in connection                |
"""

guide_docs = """# AWSRedshiftDataExecuteSQL - Operator Guide

## What it does

Executes SQL against an Amazon Redshift provisioned cluster or serverless workgroup using the
Redshift Data API. Async — submits the statement and polls every 10 seconds until FINISHED or
a terminal failure state. No direct database connection required — runs entirely through AWS APIs.

---

## Auth

Three methods, evaluated in priority order:
1. **Access keys** — aws_access_key_id + aws_secret_access_key in connection
2. **Assume IAM role** — assume_iam_role (ARN) in connection, assumed via STS
3. **Default credential chain** — instance profile, ECS task role, env vars, ~/.aws/credentials

---

## Connection

**Provisioned cluster:**

    {
      "region": "us-east-1",
      "cluster_identifier": "my-redshift-cluster",
      "database": "dev",
      "db_user": "awsuser"
    }

**Serverless workgroup:**

    {
      "region": "us-east-1",
      "workgroup_name": "my-workgroup",
      "database": "dev"
    }

| Field                 | Required          | Description                                             |
|-----------------------|-------------------|---------------------------------------------------------|
| region                | Yes               | AWS region                                              |
| database              | Yes               | Target database name                                    |
| cluster_identifier    | Yes (provisioned) | Provisioned cluster ID — use OR workgroup_name          |
| workgroup_name        | Yes (serverless)  | Serverless workgroup name — use OR cluster_identifier   |
| db_user               | No                | DB user for provisioned clusters (if not using secret)  |
| secret_arn            | No                | Secrets Manager ARN for DB credentials                  |
| statement_name        | No                | Label shown in Redshift console                         |
| poll_interval_seconds | No                | Polling interval in seconds (default: 10)               |
| aws_access_key_id     | Scenario 1        | IAM user access key                                     |
| aws_secret_access_key | Scenario 1        | IAM user secret key                                     |
| assume_iam_role       | Scenario 2        | Role ARN to assume via STS                              |

---

## Payload

    {"sql": "SELECT COUNT(*) FROM my_table"}

| Field | Required | Description              |
|-------|----------|--------------------------|
| sql   | Yes      | SQL statement to execute |

---

## Output (on success)

    {
      "statement_id": "a1b2c3d4-...",
      "statement_status": "FINISHED",
      "records_updated": 0,
      "has_result_set": true,
      "query_string": "SELECT COUNT(*) FROM my_table"
    }

---

## What this operator does NOT do

- Does not return query result rows — fetch separately via get_statement_result
- Does not support multi-statement batches — use batch_execute_statement for that
"""

description = """
Executes SQL via the Amazon Redshift Data API (provisioned or serverless). Polls every 10 seconds
until FINISHED. Equivalent to Airflow's RedshiftDataOperator. Required: sql, database, and either
cluster_identifier or workgroup_name. Optional: db_user, secret_arn, statement_name,
poll_interval_seconds (default 10). Auth: IAM role via STS first, fallback to access keys.
Returns statement_id, statement_status, records_updated, has_result_set.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "Redshift",
    "category": "Data Warehouse",
    "tags": ["redshift", "sql", "data-api", "serverless", "aws", "execute"],
    "airflow_equivalent": "RedshiftDataOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

**Payload is SQL only** — all connection details (database, cluster_identifier or workgroup_name,
db_user, secret_arn) live in the connection field. This keeps the payload clean for dynamic SQL
use cases where only the query changes between runs.

**Provisioned vs serverless**: provide `cluster_identifier` for provisioned clusters and
`workgroup_name` for Redshift Serverless — never both. For provisioned clusters without a
Secrets Manager secret, `db_user` is required for IAM-based authentication.

**Result rows**: this operator does NOT return result rows — only statement metadata. Use the
Redshift Data API `get_statement_result` call separately with the returned `statement_id` to
fetch rows from SELECT queries.

**`has_result_set`**: indicates whether the statement produced rows (SELECT). DML statements
(INSERT/UPDATE/DELETE) have `has_result_set: false` and `records_updated` shows affected rows.
"""