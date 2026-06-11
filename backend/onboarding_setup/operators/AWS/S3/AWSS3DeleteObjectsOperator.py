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

codeblock = {"main.py": """import json
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from src.common.logger.logger import log_info, log_error


def _build_s3_client(connection: dict):
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
        return session.client("s3")

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
        return session.client("s3")

    # Case 3: Default credential chain (EC2 instance profile, ECS task role, env vars, ~/.aws)
    log_info("task", "initialize", "auth_default",
             "Using default AWS credential chain (instance profile / ECS task role / env / config)")
    return boto3.Session(region_name=region).client("s3")


def _filename(key):
    return key.rstrip('/').split('/')[-1] or key


def initialize(least_action_task_object):
    try:
        connection = least_action_task_object.get('connection', {})
        if isinstance(connection, str):
            connection = json.loads(connection)

        log_info('task', 'initialize', 'building_client',
                 f'region={connection.get("region", "us-east-1")}')

        client = _build_s3_client(connection)
        client.list_buckets()
        log_info('task', 'initialize', 'connectivity_ok', 'S3 client initialized and verified')
        return client

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        log_error('task', 'initialize', 'client_error', f'({error_code}) {error_msg}')
        raise
    except Exception as e:
        log_error('task', 'initialize', 'init_failed', f'Error: {str(e)}')
        raise


def run(least_action_task_object, client):
    try:
        payload = least_action_task_object.get('payload', '{}')
        if isinstance(payload, str):
            payload = json.loads(payload)
        if 'data' in payload and isinstance(payload['data'], dict):
            payload = payload['data']
            log_info('task', 'run', 'payload_unwrapped', 'Unwrapped payload data envelope')

        bucket = payload.get('bucket')
        keys = payload.get('keys', [])

        if not bucket:
            msg = 'Missing required payload field: bucket'
            log_error('task', 'run', 'payload_validation_failed', msg)
            return {'execution_type': 'sync', 'status': 'failed', 'result': {'error': msg}}

        if not keys:
            msg = 'Missing required payload field: keys (must be a non-empty list)'
            log_error('task', 'run', 'payload_validation_failed', msg)
            return {'execution_type': 'sync', 'status': 'failed', 'result': {'error': msg}}

        if len(keys) > 1000:
            msg = f'Too many keys: {len(keys)}. Maximum per run is 1000.'
            log_error('task', 'run', 'payload_validation_failed', msg)
            return {'execution_type': 'sync', 'status': 'failed', 'result': {'error': msg}}

        log_info('task', 'run', 'delete_start',
                 f'Deleting {len(keys)} object(s) from s3://{bucket}')

        for key in keys:
            log_info('task', 'run', 'delete_queued',
                     f'Queued: {_filename(key)} (full path: {key})')

        response = client.delete_objects(
            Bucket=bucket,
            Delete={
                'Objects': [{'Key': k} for k in keys],
                'Quiet': False
            }
        )

        deleted = response.get('Deleted', [])
        errors = response.get('Errors', [])

        for obj in deleted:
            key = obj['Key']
            log_info('task', 'run', 'deleted',
                     f'Deleted: {_filename(key)} (full path: s3://{bucket}/{key})')

        for err in errors:
            key = err['Key']
            log_error('task', 'run', 'delete_error',
                      f'Failed: {_filename(key)} (full path: s3://{bucket}/{key}) | '
                      f'Code: {err["Code"]} | Message: {err["Message"]}')

        log_info('task', 'run', 'delete_complete',
                 f'Done: {len(deleted)} deleted, {len(errors)} failed out of {len(keys)} total')

        if len(errors) == 0:
            status = 'success'
        elif len(deleted) == 0:
            status = 'failed'
        else:
            status = 'partial'

        return {
            'execution_type': 'sync',
            'status': status,
            'result': {
                'bucket': bucket,
                'total': len(keys),
                'deleted_count': len(deleted),
                'error_count': len(errors),
                'deleted': [{'key': obj['Key'], 'filename': _filename(obj['Key'])} for obj in deleted],
                'errors': [{'key': e['Key'], 'filename': _filename(e['Key']), 'code': e['Code'], 'message': e['Message']} for e in errors]
            }
        }

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        log_error('task', 'run', 'delete_client_error', f'({error_code}) {error_msg}')
        return {'execution_type': 'sync', 'status': 'failed',
                'result': {'error': f'({error_code}) {error_msg}'}}
    except BotoCoreError as e:
        log_error('task', 'run', 'delete_transport_error', f'BotoCoreError: {str(e)}')
        return {'execution_type': 'sync', 'status': 'failed',
                'result': {'error': f'Transport error: {str(e)}'}}
    except Exception as e:
        log_error('task', 'run', 'run_failed', f'Unexpected error: {str(e)}')
        return {'execution_type': 'sync', 'status': 'failed',
                'result': {'error': str(e)}}


def check_completion(least_action_task_object, client, run_details):
    log_info('task', 'check_completion', 'sync_complete',
             'S3 delete is synchronous - already complete')
    return {
        'status': run_details.get('status', 'success'),
        'message': 'Synchronous S3 delete operation completed',
        'output': run_details.get('result', {})
    }


def finish(least_action_task_object, client, completion_details, run_details):
    try:
        task_laui = least_action_task_object.get('laui', 'unknown')
        status = completion_details.get('status', 'unknown')
        log_info('task', 'finish', 'final_status',
                 f'Task {task_laui} completed with status: {status}')
        if status in ('success', 'partial'):
            output = completion_details.get('output', {})
            deleted_names = [d['filename'] for d in output.get('deleted', [])]
            log_info('task', 'finish', 'delete_summary',
                     f'Bucket: {output.get("bucket")} | '
                     f'Total: {output.get("total", 0)} | '
                     f'Deleted: {output.get("deleted_count", 0)} | '
                     f'Failed: {output.get("error_count", 0)} | '
                     f'Files: {deleted_names}')
        else:
            log_error('task', 'finish', 'operation_failed',
                      completion_details.get('message', 'No message'))
        log_info('task', 'finish', 'cleanup_complete', 'No resources to release')
    except Exception as e:
        log_error('task', 'finish', 'cleanup_error', f'Error in finish: {str(e)}')
"""}

bashblock = {"main.sh": """#!/bin/bash
set -e
pip install boto3>=1.28.0
pip install botocore>=1.31.0
echo "Dependencies installed successfully"
"""}

connection = {"region": "us-east-1"}

payload = '{"bucket": "my-bucket", "keys": ["data/file1.json", "data/file2.json"]}'

prompt = (
    "Delete one or more S3 objects from a bucket in a single batch call using delete_objects. "
    "Required payload: bucket (string) and keys (list of strings, max 1000). "
    "Auth: IAM role first via STS, fallback to access keys from connection. "
    "Log both full key path and filename for each key. "
    "Return deleted count, error count, deleted list, and error list. "
    "Status: success if all deleted, partial if some failed, failed if all failed."
)

install_docs = """# AWSS3DeleteObjects — Install Guide

## Dependencies

Installed automatically via main.sh:

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": ["s3:DeleteObject"],
      "Resource": ["arn:aws:s3:::your-bucket/*"]
    }

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2 instance — no keys needed in connection    |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
"""

guide_docs = """# AWSS3DeleteObjects — Operator Guide

## What it does

Deletes one or more S3 objects from a single bucket in a single batch delete_objects API call.
Supports up to 1000 keys per run. Returns a detailed breakdown of deleted keys and per-key errors.

For every key, logs both the filename (last segment) and full S3 path — e.g. for
`abc/123/file.json`, logs show `filename=file.json` and `full path=s3://bucket/abc/123/file.json`.

---

## Auth

| Priority | Method |
|---|---|
| 1st | IAM role — tried via STS. No keys needed in connection. |
| 2nd | aws_access_key_id + aws_secret_access_key from connection |

---

## Connection

Minimum (IAM role):

    {"region": "us-east-1"}

---

## Payload

    {
      "bucket": "my-bucket",
      "keys":   ["data/file1.json", "data/file2.json"]
    }

| Field  | Required | Description                            |
|--------|----------|----------------------------------------|
| bucket | Yes      | Bucket to delete from                  |
| keys   | Yes      | List of full S3 key paths. Max 1000.   |

---

## Output (on success)

    {
      "bucket":        "my-bucket",
      "total":         2,
      "deleted_count": 2,
      "error_count":   0,
      "deleted":       [{"key": "data/file1.json", "filename": "file1.json"}],
      "errors":        []
    }

Status values: success (all deleted), partial (some failed), failed (all failed or validation error)

---

## Edge Cases

- Key does not exist: AWS treats as success — appears in deleted list
- Partial failure: some keys may fail (e.g. AccessDenied) while others succeed
- More than 1000 keys: returns status:failed immediately — split into multiple tasks
- Versioned bucket: delete_objects creates a delete marker, not permanent deletion
"""

description = """
Deletes one or more S3 objects from a bucket in a single batch delete_objects call — efficient
for bulk cleanup, rolling retention, and pipeline teardown. Accepts up to 1000 keys per run and
returns a precise per-key breakdown of what succeeded and what failed, with status:partial for
mixed results. Logs both the filename and full S3 path for every key before deletion. Auth: IAM
role via STS first, fallback to flat access keys in connection.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "S3",
    "category": "Storage",
    "tags": ["s3", "objects", "delete", "batch", "aws"],
    "airflow_equivalent": "S3DeleteObjectsOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

S3 delete_objects is idempotent — deleting a non-existent key succeeds silently. For versioned buckets, this only deletes the current version (creates a delete marker); to permanently delete all versions, list and delete each version explicitly. Batch delete supports up to 1000 keys per call — for larger lists, split into chunks.
"""

