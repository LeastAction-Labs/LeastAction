# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
action_type = "AWS"

codeblock = {
    "main.py": '''import boto3
from botocore.exceptions import ClientError
from src.common.logger.logger import log_info, log_error


def run(least_action_action_object, **action_variables):
    task_id     = least_action_action_object.get('laui')
    user_token  = least_action_action_object.get('user_access_token')

    bucket      = action_variables.get('bucket_name')
    key         = action_variables.get('key')
    region      = action_variables.get('region', 'us-east-1')
    access_key  = action_variables.get('aws_access_key_id')
    secret_key  = action_variables.get('aws_secret_access_key')
    session_tok = action_variables.get('aws_session_token')
    role_arn    = action_variables.get('assume_iam_role')

    if not bucket or not key:
        log_error('action', 'run', 'missing_vars', f'[{task_id}] bucket_name and key are required')
        return False

    try:
        if access_key and secret_key:
            log_info('action', 'run', 'auth_keys', f'Using explicit access key ending ...{access_key[-4:]}')
            s3 = boto3.Session(
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                aws_session_token=session_tok,
                region_name=region,
            ).client('s3')
        elif role_arn:
            log_info('action', 'run', 'auth_assume_role', f'Assuming IAM role: {role_arn}')
            sts = boto3.client('sts', region_name=region)
            creds = sts.assume_role(RoleArn=role_arn, RoleSessionName='leastaction_action')['Credentials']
            s3 = boto3.Session(
                aws_access_key_id=creds['AccessKeyId'],
                aws_secret_access_key=creds['SecretAccessKey'],
                aws_session_token=creds['SessionToken'],
                region_name=region,
            ).client('s3')
        else:
            log_info('action', 'run', 'auth_default', 'Using default AWS credential chain')
            s3 = boto3.Session(region_name=region).client('s3')
    except Exception as e:
        log_error('action', 'run', 'auth_error', f'[{task_id}] Failed to build S3 client: {e}')
        return False

    # Prefix/folder check — key ends with /
    if key.endswith('/'):
        log_info('action', 'run', 'checking_prefix', f'[{task_id}] Checking prefix s3://{bucket}/{key}')
        try:
            resp = s3.list_objects_v2(Bucket=bucket, Prefix=key, MaxKeys=1)
            count = resp.get('KeyCount', 0)
            if count > 0:
                log_info('action', 'run', 'prefix_found',
                         f'[{task_id}] s3://{bucket}/{key} has {count} object(s) - gate open')
                return True
            else:
                log_info('action', 'run', 'prefix_empty',
                         f'[{task_id}] s3://{bucket}/{key} exists but is empty - will retry')
                return False
        except ClientError as e:
            code = e.response['Error']['Code']
            log_error('action', 'run', 'prefix_error', f'[{task_id}] S3 error ({code}): {e}')
            return False

    # Specific file check — head_object
    log_info('action', 'run', 'checking_key', f'[{task_id}] Checking s3://{bucket}/{key}')
    try:
        response = s3.head_object(Bucket=bucket, Key=key)
        size = response.get('ContentLength', 0)
        log_info('action', 'run', 'key_found',
                 f'[{task_id}] s3://{bucket}/{key} exists ({size} bytes) - gate open')
        return True
    except ClientError as e:
        code = e.response['Error']['Code']
        if code in ('404', 'NoSuchKey'):
            log_info('action', 'run', 'key_missing',
                     f'[{task_id}] s3://{bucket}/{key} not yet present - will retry')
            return False
        log_error('action', 'run', 'unexpected_error',
                  f'[{task_id}] S3 error ({code}): {e}')
        return False
'''
}

bashblock = {
    "install_dependencies.sh": "pip install boto3 botocore"
}

action_variables = {
    "bucket_name": "my-bucket",
    "key": "source/file.txt",
    "region": "us-east-1",
    "aws_access_key_id": "",
    "aws_secret_access_key": "",
    "aws_session_token": "",
    "assume_iam_role": ""
}

connection = {}

prompt = (
    "Pre-action sensor that checks whether an S3 key or prefix exists before allowing a task to execute. "
    "If key ends with '/' performs a prefix/folder check using list_objects_v2 — returns True if any object exists under the prefix. "
    "If key is a specific file performs a head_object check — returns True if the file exists. "
    "Supports all 3 auth methods: explicit access keys, assume IAM role via STS, or default credential chain. "
    "All key values support LeastAction template variables ({{ds}}, {{ts}}, {{ts[11:16]}} etc.) resolved at runtime from logical_date. "
    "Returns True to open the gate, False to hold the task and retry on next scheduler tick. "
    "Never raises — all errors return False except auth failures which also return False."
)

install_docs = """# AWSS3KeyExists — Install Guide

## Dependencies

    pip install boto3 botocore

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": ["s3:HeadObject", "s3:ListBucket"],
      "Resource": ["arn:aws:s3:::*", "arn:aws:s3:::*/*"]
    }

## Auth

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| Access keys   | Set aws_access_key_id and aws_secret_access_key in action_variables |
| IAM role      | Set assume_iam_role ARN in action_variables                   |
| Default chain | Leave all auth fields empty — uses instance profile / env vars |
"""

guide_docs = """# AWSS3KeyExists — Action Guide

## What it does

Pre-action sensor that gates task execution on S3 file or folder availability.
Attach as a pre_action on any task — the task only runs when this action returns True.
When False, the task stays scheduled and retries on the next scheduler tick.

Supports two check modes determined automatically from the key value:

- **File check** (`key` does not end with `/`): uses `head_object` — True if file exists
- **Prefix check** (`key` ends with `/`): uses `list_objects_v2` — True if any object exists under the prefix

---

## Action Variables

    {
      "bucket_name": "my-bucket",
      "key": "source/sales_{{ds}}.csv",
      "region": "us-east-1",
      "aws_access_key_id": "",
      "aws_secret_access_key": "",
      "aws_session_token": "",
      "assume_iam_role": ""
    }

| Field               | Required | Description                                              |
|---------------------|----------|----------------------------------------------------------|
| bucket_name         | Yes      | S3 bucket name                                           |
| key                 | Yes      | S3 key (file) or prefix (folder, must end with /)       |
| region              | No       | AWS region (default: us-east-1)                          |
| aws_access_key_id   | No       | Explicit access key                                      |
| aws_secret_access_key | No     | Explicit secret key                                      |
| aws_session_token   | No       | Session token for temporary credentials                  |
| assume_iam_role     | No       | IAM role ARN to assume via STS                           |

---

## Supported Key Templates

The `key` field supports LeastAction template variables resolved from `logical_date`:

| Template | Example output |
|---|---|
| `source/{{ds}}/file.csv` | `source/2026-05-29/file.csv` |
| `source/date={{ds}} {{ts[11:16]}}:00/file.txt` | `source/date=2026-05-29 06:05:00/file.txt` |
| `source/yyyy={{ds[:4]}}/mm={{ds[5:7]}}/dd={{ds[8:10]}}/hh={{ts[11:13]}}/mm={{ts[14:16]}}/file.txt` | `source/yyyy=2026/mm=05/dd=29/hh=06/mm=05/file.txt` |
| `source/` | prefix check — any file under source/ |

---

## Returns

- `True` — file/prefix exists, gate opens, task executes
- `False` — not yet present, task stays scheduled, retries next tick
"""

description = """
Pre-action sensor that gates S3-dependent tasks on file or folder availability.
Checks a specific S3 key (head_object) or prefix (list_objects_v2) and returns True
when the expected data has arrived. Supports LeastAction template variables in the key
field for date-partitioned paths. Auth: explicit keys, assume role via STS, or default chain.
Attach as pre_action with action_type="pre_actions" — task only runs when file is present.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "S3",
    "category": "Storage",
    "tags": ["s3", "sensor", "pre-action", "file-check", "aws", "gate"],
    "airflow_equivalent": "S3KeySensor"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"
