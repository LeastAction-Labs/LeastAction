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


def _build_glue_client(connection: dict):
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
        return session.client("glue")

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
        return session.client("glue")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info("task", "initialize", "auth_default",
             "Using default AWS credential chain (instance profile / ECS task role / env / config)")
    return boto3.Session(region_name=region).client("glue")


def initialize(least_action_task_object):
    try:
        connection = least_action_task_object.get("connection", {})
        if isinstance(connection, str):
            connection = json.loads(connection)

        log_info("task", "initialize", "building_client",
                 f"region={connection.get('region', 'us-east-1')}")

        client = _build_glue_client(connection)
        client.list_data_quality_rulesets(MaxResults=1)
        log_info("task", "initialize", "connectivity_ok",
                 "Glue client initialized and verified")
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
                return {"status": "failed", "execution_type": "sync", "result": None,
                        "error": "Invalid payload format — expected flat JSON object"}

        database_name = payload.get("database_name")
        table_name = payload.get("table_name")
        role = payload.get("role")

        if not database_name:
            msg = "Missing required payload field: database_name"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}
        if not table_name:
            msg = "Missing required payload field: table_name"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}
        if not role:
            msg = "Missing required payload field: role"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        number_of_workers = payload.get("number_of_workers", 5)
        timeout = payload.get("timeout", 2880)
        created_ruleset_name = payload.get("created_ruleset_name")

        params = {
            "DataSource": {"GlueTable": {"DatabaseName": database_name, "TableName": table_name}},
            "Role": role,
            "NumberOfWorkers": number_of_workers,
            "Timeout": timeout,
        }
        if created_ruleset_name:
            params["CreatedRulesetName"] = created_ruleset_name

        log_info("task", "run", "starting_recommendation",
                 f"Starting Glue Data Quality rule recommendation run for {database_name}.{table_name}")

        response = client.start_data_quality_rule_recommendation_run(**params)
        run_id = response.get("RunId")

        log_info("task", "run", "recommendation_submitted",
                 f"Rule recommendation run {run_id} submitted, polling for completion...")

        terminal_states = {"SUCCEEDED", "FAILED", "STOPPED", "TIMEOUT"}
        while True:
            run_resp = client.get_data_quality_rule_recommendation_run(RunId=run_id)
            state = run_resp.get("Status")
            log_info("task", "run", "polling_recommendation_state", f"Run {run_id} status: {state}")
            if state in terminal_states:
                break
            time.sleep(20)

        recommended_ruleset = run_resp.get("RecommendedRuleset")
        op_status = "success" if state == "SUCCEEDED" else "failed"

        log_info("task", "run", "recommendation_complete",
                 f"Rule recommendation run {run_id} finished with status: {state}")

        result = {
            "run_id": run_id,
            "status": state,
            "recommended_ruleset": recommended_ruleset
        }
        if created_ruleset_name:
            result["created_ruleset_name"] = created_ruleset_name

        return {
            "execution_type": "sync",
            "status": op_status,
            "result": result
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        log_error("task", "run", "client_error", f"({error_code}) {error_msg}")
        return {"execution_type": "sync", "status": "failed",
                "result": {"error": f"({error_code}) {error_msg}"}}
    except BotoCoreError as e:
        log_error("task", "run", "transport_error", f"BotoCoreError: {str(e)}")
        return {"execution_type": "sync", "status": "failed",
                "result": {"error": f"Transport error: {str(e)}"}}
    except Exception as e:
        log_error("task", "run", "run_failed", f"Unexpected error: {str(e)}")
        return {"execution_type": "sync", "status": "failed", "result": {"error": str(e)}}


def check_completion(least_action_task_object, client, run_details):
    log_info("task", "check_completion", "sync_complete",
             "Glue DataQualityRuleRecommendationRun is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "Glue Data Quality rule recommendation run completed",
        "output": run_details.get("result", {})
    }


def finish(least_action_task_object, client, completion_details, run_details):
    try:
        task_laui = least_action_task_object.get("laui", "unknown")
        status = completion_details.get("status", "unknown")
        log_info("task", "finish", "final_status",
                 f"Task {task_laui} completed with status: {status}")
        if status == "success":
            output = completion_details.get("output", {})
            log_info("task", "finish", "recommendation_summary",
                     f"Run {output.get('run_id')} status={output.get('status')} "
                     f"ruleset={'saved as ' + output.get('created_ruleset_name') if output.get('created_ruleset_name') else 'returned inline'}")
        else:
            log_error("task", "finish", "operation_failed",
                      completion_details.get("message", "No message"))
        if client:
            try:
                client.close()
                log_info("task", "finish", "client_closed", "boto3 client closed successfully")
            except Exception as close_error:
                log_error("task", "finish", "client_close_error", f"Error closing client: {str(close_error)}")
        log_info("task", "finish", "cleanup_complete", "Cleanup complete")
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
}

payload = {
    "database_name": "my_database",
    "table_name": "my_table",
    "role": "arn:aws:iam::123456789012:role/GlueDataQualityRole"
}

prompt = (
    "Create an operator that starts an AWS Glue Data Quality rule recommendation run against a Glue table "
    "and waits for it to complete. "
    "Required payload fields: datasource (dict with DatabaseName + TableName), role (IAM role ARN). "
    "Optional: number_of_workers (default 5), timeout (default 2880), created_ruleset_name (saves recommendations as a new ruleset). "
    "Auth: try IAM role via STS first; if unavailable, fall back to access keys from connection. "
    "After calling start_data_quality_rule_recommendation_run, poll get_data_quality_rule_recommendation_run "
    "every 20 seconds until status is SUCCEEDED, FAILED, STOPPED, or TIMEOUT. "
    "Return run_id, status, and recommended_ruleset (DQDL string) on completion. "
    "Catch all AWS errors and return them as status:failed - never raise."
)

install_docs = """# AWSGlueDataQualityRuleRecommendationRun - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "glue:StartDataQualityRuleRecommendationRun",
        "glue:GetDataQualityRuleRecommendationRun",
        "glue:ListDataQualityRulesets"
      ],
      "Resource": "*"
    }

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance - no connection keys needed       |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
| Session token | Optionally add aws_session_token in connection                |
"""

guide_docs = """# AWSGlueDataQualityRuleRecommendationRun - Operator Guide

## What it does

Starts an AWS Glue Data Quality rule recommendation run that analyzes a Glue Data Catalog table
and automatically generates DQDL data quality rules suited to that data. Polls every 20 seconds
until the run completes and returns the recommended ruleset as a DQDL string. Optionally saves
the recommendations as a named ruleset in the Glue catalog.

---

## Auth

1. IAM role - tried first via STS. Used automatically if available. No keys needed in connection.
2. Access keys - fallback to aws_access_key_id + aws_secret_access_key from connection.

---

## Connection

    {
      "region": "us-east-1",
      "aws_access_key_id": "AKIA...",    //optional - omit to use IAM role
      "aws_secret_access_key": "...",    //optional - omit to use IAM role
      "aws_session_token": ""            //optional - for temporary credentials
    }

---

## Payload

    {
      "database_name": "my_database",
      "table_name": "my_table",
      "role": "arn:aws:iam::123456789012:role/GlueDataQualityRole"
    }

| Field               | Required | Description                                                         |
|---------------------|----------|---------------------------------------------------------------------|
| database_name       | Yes      | Glue database name                                                  |
| table_name          | Yes      | Glue table name                                                     |
| role                | Yes      | IAM role ARN that Glue assumes to run the recommendation            |
| number_of_workers   | No       | DPU workers for the run (default: 5)                                |
| timeout             | No       | Max run duration in minutes (default: 2880)                         |
| created_ruleset_name| No       | If set, saves the recommended rules as a new ruleset with this name |

---

## Output (on success)

    {
      "run_id": "dqrec-abc123",
      "status": "SUCCEEDED",
      "recommended_ruleset": "Rules = [\\n  IsComplete \\"column_name\\",\\n  ...\\n]"
    }

If `created_ruleset_name` was provided, the output also includes `"created_ruleset_name"`.

---

## What this operator does NOT do

- Does not evaluate existing rulesets (use AWSGlueDataQualityRun for that)
- Does not guarantee that all recommended rules are applicable — review before deploying
"""

description = """
Starts an AWS Glue Data Quality rule recommendation run that analyzes a Glue Data Catalog table
and automatically generates DQDL data quality rules. Polls every 20 seconds until SUCCEEDED,
FAILED, STOPPED, or TIMEOUT. Optionally saves the recommended rules as a named ruleset via
created_ruleset_name. Auth: IAM role via STS first, fallback to access keys. Returns run_id,
final status, and the recommended_ruleset DQDL string on success.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "Glue",
    "category": "Analytics",
    "tags": ["glue", "data-quality", "dq", "ruleset", "recommendation", "dqdl", "aws"],
    "airflow_equivalent": "GlueDataQualityRuleRecommendationRunOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

Analyzes a table and recommends a DQDL (Data Quality Definition Language) ruleset. The recommended ruleset is returned as a DQDL string and optionally saved to the Glue catalog as `created_ruleset_name`. Use this to bootstrap data quality rules for a new table before running evaluations.
"""

