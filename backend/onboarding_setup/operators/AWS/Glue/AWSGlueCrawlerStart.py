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
        client.list_crawlers(MaxResults=1)
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

        crawler_name = payload.get("crawler_name")
        if not crawler_name:
            msg = "Missing required payload field: crawler_name"
            log_error("task", "run", "payload_validation_failed", msg)
            return {"execution_type": "sync", "status": "failed", "result": {"error": msg}}

        log_info("task", "run", "starting_crawler", f"Starting Glue crawler: {crawler_name}")

        try:
            client.start_crawler(Name=crawler_name)
            log_info("task", "run", "crawler_started", f"Crawler {crawler_name} started successfully")
        except ClientError as e:
            if e.response["Error"]["Code"] == "CrawlerRunningException":
                log_info("task", "run", "already_running",
                         f"Crawler {crawler_name} is already running - will poll for completion")
            else:
                raise

        log_info("task", "run", "polling_crawler",
                 f"Polling crawler {crawler_name} until READY state...")

        while True:
            resp = client.get_crawler(Name=crawler_name)
            state = resp["Crawler"]["State"]
            log_info("task", "run", "polling_crawler_state", f"Crawler {crawler_name} state: {state}")
            if state == "READY":
                break
            time.sleep(15)

        last_crawl = resp["Crawler"].get("LastCrawl", {})
        last_status = last_crawl.get("Status", "UNKNOWN")
        error_message = last_crawl.get("ErrorMessage")

        log_info("task", "run", "crawler_done",
                 f"Crawler {crawler_name} finished with last crawl status: {last_status}")

        if last_status == "FAILED":
            return {
                "execution_type": "sync",
                "status": "failed",
                "result": {
                    "error": error_message or "Crawler last crawl failed",
                    "crawler_name": crawler_name,
                    "last_status": last_status
                }
            }

        return {
            "execution_type": "sync",
            "status": "success",
            "result": {
                "crawler_name": crawler_name,
                "last_status": last_status,
                "tables_created": last_crawl.get("TablesCreated", 0),
                "tables_updated": last_crawl.get("TablesUpdated", 0),
                "tables_deleted": last_crawl.get("TablesDeleted", 0),
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
             "Glue CrawlerStart is synchronous - already complete")
    return {
        "status": run_details.get("status", "success"),
        "message": "Glue crawler run completed",
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
            log_info("task", "finish", "crawler_summary",
                     f"Crawler {output.get('crawler_name')} last_status={output.get('last_status')} "
                     f"tables_created={output.get('tables_created')} "
                     f"tables_updated={output.get('tables_updated')}")
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
    "crawler_name": "my-glue-crawler"
}

prompt = (
    "Create an operator that starts an AWS Glue Crawler and waits for it to finish. "
    "Required payload field: crawler_name. "
    "Auth: try IAM role via STS first; if unavailable, fall back to access keys from connection. "
    "Call start_crawler; if CrawlerRunningException is raised, it is already running — continue polling. "
    "Poll get_crawler every 15 seconds until State is READY. "
    "After READY, check LastCrawl.Status — if FAILED, return status:failed with the error message. "
    "On success return crawler_name, last_status, tables_created, tables_updated, tables_deleted. "
    "Catch all AWS errors and return them as status:failed - never raise."
)

install_docs = """# AWSGlueCrawlerStart - Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "glue:StartCrawler",
        "glue:GetCrawler",
        "glue:ListCrawlers"
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

guide_docs = """# AWSGlueCrawlerStart - Operator Guide

## What it does

Starts an AWS Glue Crawler and polls synchronously every 15 seconds until it reaches READY state.
After completion, reports the last crawl status and the number of tables created, updated, and
deleted. If the crawler is already running when triggered, it will wait for the current run to
finish rather than failing.

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

    { "crawler_name": "my-glue-crawler" }

| Field        | Required | Description                       |
|--------------|----------|-----------------------------------|
| crawler_name | Yes      | Name of the Glue Crawler to start |

---

## Output (on success)

    {
      "crawler_name": "my-glue-crawler",
      "last_status": "SUCCEEDED",
      "tables_created": 3,
      "tables_updated": 1,
      "tables_deleted": 0
    }

---

## What this operator does NOT do

- Does not create or configure the crawler
- Does not modify crawler targets or schedule
- Does not delete tables discovered by the crawler
"""

description = """
Starts an AWS Glue Crawler and polls synchronously every 15 seconds until the crawler reaches
READY state. Handles the case where the crawler is already running by waiting for the current
run to finish. Reports crawl outcome including tables created, updated, and deleted. Auth: IAM
role via STS first, fallback to access keys. Returns crawler_name, last_status, and table
change counts on success.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "Glue",
    "category": "Analytics",
    "tags": ["glue", "crawler", "catalog", "metadata", "aws"],
    "airflow_equivalent": "GlueCrawlerOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

Handles `CrawlerRunningException` gracefully — if the crawler is already running, the operator waits for the current run to complete rather than failing. Returns `tables_created`, `tables_updated`, `tables_deleted` counts on success. The crawler must already exist in the Glue catalog.
"""

