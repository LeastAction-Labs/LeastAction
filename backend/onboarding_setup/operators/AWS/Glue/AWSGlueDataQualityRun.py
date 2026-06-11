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
        ruleset_names = payload.get("ruleset_names")

        missing = []
        if not database_name:
            missing.append("database_name")
        if not table_name:
            missing.append("table_name")
        if not role:
            missing.append("role")
        if not ruleset_names:
            missing.append("ruleset_names")
        if missing:
            msg = f"Missing required payload fields: {missing}"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        datasource = {"GlueTable": {"DatabaseName": database_name, "TableName": table_name}}

        number_of_workers = payload.get("number_of_workers", 5)
        timeout = payload.get("timeout", 2880)

        log_info("task", "run", "starting_dq_run",
                 f"Starting Glue Data Quality evaluation run for rulesets: {ruleset_names}")

        response = client.start_data_quality_ruleset_evaluation_run(
            DataSource=datasource,
            Role=role,
            RulesetNames=ruleset_names,
            NumberOfWorkers=number_of_workers,
            Timeout=timeout,
        )
        run_id = response.get("RunId")

        log_info("task", "run", "dq_run_submitted",
                 f"Data Quality run {run_id} submitted, polling for completion...")

        terminal_states = {"SUCCEEDED", "FAILED", "STOPPED", "TIMEOUT"}
        while True:
            run_resp = client.get_data_quality_ruleset_evaluation_run(RunId=run_id)
            state = run_resp.get("Status")
            log_info("task", "run", "polling_dq_state", f"Run {run_id} status: {state}")
            if state in terminal_states:
                break
            time.sleep(20)

        result_ids = run_resp.get("ResultIds", [])
        results = []
        if result_ids:
            results_resp = client.batch_get_data_quality_result(ResultIds=result_ids)
            for r in results_resp.get("Results", []):
                results.append({
                    "result_id": r.get("ResultId"),
                    "score": r.get("Score"),
                    "rule_results": [
                        {
                            "name": rr.get("Name"),
                            "result": rr.get("Result"),
                            "description": rr.get("Description")
                        }
                        for rr in r.get("RuleResults", [])
                    ]
                })

        op_status = "success" if state == "SUCCEEDED" else "failed"
        log_info("task", "run", "dq_run_complete",
                 f"Data Quality run {run_id} finished with status: {state}, results: {len(results)}")

        return {
            "execution_type": "sync",
            "status": op_status,
            "result": {
                "run_id": run_id,
                "status": state,
                "ruleset_names": ruleset_names,
                "results": results
            }
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
             "Glue DataQualityRun is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "Glue Data Quality evaluation run completed",
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
            log_info("task", "finish", "dq_summary",
                     f"Run {output.get('run_id')} status={output.get('status')} "
                     f"results={len(output.get('results', []))}")
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
    "role": "arn:aws:iam::123456789012:role/GlueDataQualityRole",
    "ruleset_names": ["my-ruleset"]
}

prompt = (
    "Create an operator that runs an AWS Glue Data Quality ruleset evaluation against a Glue table "
    "and waits for it to complete. "
    "Required payload fields: datasource (dict with DatabaseName+TableName, or GlueTable wrapper), "
    "role (IAM role ARN), ruleset_names (list of ruleset names). "
    "Optional: number_of_workers (default 5), timeout (default 2880 minutes). "
    "Auth: try IAM role via STS first; if unavailable, fall back to access keys from connection. "
    "After calling start_data_quality_ruleset_evaluation_run, poll get_data_quality_ruleset_evaluation_run "
    "every 20 seconds until status is SUCCEEDED, FAILED, STOPPED, or TIMEOUT. "
    "Fetch result details using batch_get_data_quality_result. "
    "Return run_id, status, ruleset_names, and per-rule results on completion. "
    "Catch all AWS errors and return them as status:failed - never raise."
)

install_docs = """# AWSGlueDataQualityRun - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "glue:StartDataQualityRulesetEvaluationRun",
        "glue:GetDataQualityRulesetEvaluationRun",
        "glue:BatchGetDataQualityResult",
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

guide_docs = """# AWSGlueDataQualityRun - Operator Guide

## What it does

Runs an AWS Glue Data Quality ruleset evaluation against a Glue Data Catalog table and polls
synchronously every 20 seconds until the run completes. After completion, retrieves per-rule
pass/fail results with scores and descriptions. Returns the full evaluation outcome including
each rule's result.

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
      "role": "arn:aws:iam::123456789012:role/GlueDataQualityRole",
      "ruleset_names": ["my-ruleset"]
    }

| Field             | Required | Description                                                    |
|-------------------|----------|----------------------------------------------------------------|
| database_name     | Yes      | Glue database name                                             |
| table_name        | Yes      | Glue table name                                                |
| role              | Yes      | IAM role ARN that Glue assumes to run the evaluation           |
| ruleset_names     | Yes      | List of ruleset names to evaluate                              |
| number_of_workers | No       | DPU workers for the run (default: 5)                           |
| timeout           | No       | Max run duration in minutes (default: 2880)                    |

---

## Output (on success)

    {
      "run_id": "dqrun-abc123",
      "status": "SUCCEEDED",
      "ruleset_names": ["my-ruleset"],
      "results": [
        {
          "result_id": "dqresult-xyz",
          "score": 0.95,
          "rule_results": [
            {"name": "Rule_1", "result": "PASS", "description": "..."}
          ]
        }
      ]
    }

---

## What this operator does NOT do

- Does not create or modify rulesets (use Glue Studio or CLI)
- Does not store results beyond what is returned in the output
"""

description = """
Runs an AWS Glue Data Quality ruleset evaluation against a Glue Data Catalog table and polls
synchronously every 20 seconds until SUCCEEDED, FAILED, STOPPED, or TIMEOUT. After completion,
fetches per-rule pass/fail scores via batch_get_data_quality_result. Accepts datasource as
plain {DatabaseName, TableName} or the full {GlueTable: {...}} wrapper. Auth: IAM role via STS
first, fallback to access keys. Returns run_id, status, and detailed rule-level results.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "Glue",
    "category": "Analytics",
    "tags": ["glue", "data-quality", "dq", "ruleset", "evaluation", "aws"],
    "airflow_equivalent": "GlueDataQualityOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

`ruleset_names` must already exist in the Glue Data Catalog attached to the specified table. Results include per-rule pass/fail status fetched via `batch_get_data_quality_result`. The role must have Glue read permissions and S3 read access on the target table's data location.
"""

