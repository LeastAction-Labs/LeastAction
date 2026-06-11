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

codeblock = {'main.py': '''# AWSS3ValidateDataExists Operator
# This operator checks if data exists in S3 for a given date range
# and sends a Slack notification based on validation results.
# Supports both IAM role-based and credential-based authentication.
import json
import boto3
import requests
from botocore.exceptions import ClientError, BotoCoreError
from src.common.logger.logger import log_info, log_error
from datetime import datetime, timedelta
import ast

def initialize(least_action_task_object):
    try:
        connection = least_action_task_object.get('connection', {})
        task_laui = least_action_task_object.get('laui')

        log_info("task", "initialize", "extracting_connection_details", "Extracting connection details")

        region = connection.get('region', 'us-east-1')
        aws_access_key_id = connection.get('aws_access_key_id')
        aws_secret_access_key = connection.get('aws_secret_access_key')
        session_token = connection.get('aws_session_token')

        log_info("task", "initialize", "region_configuration", "Region configuration")

        # Use explicit credentials if provided, otherwise fall back to IAM role
        if aws_access_key_id and aws_secret_access_key:
            log_info("task", "initialize", "authentication_method",
                     "Using explicitly provided AWS credentials")
            client_params = {
                'service_name': 's3',
                'region_name': region,
                'aws_access_key_id': aws_access_key_id,
                'aws_secret_access_key': aws_secret_access_key
            }
            if session_token:
                client_params['aws_session_token'] = session_token
            client = boto3.client(**client_params)
        else:
            log_info("task", "initialize", "authentication_method",
                     "No explicit credentials provided, using IAM role")
            client = boto3.client('s3', region_name=region)

        log_info("task", "initialize", "testing_connection",
                 "Testing S3 client connection")

        client.list_buckets()

        log_info("task", "initialize", "connection_successful", "Connection successful")

        return client

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        log_error("task", "initialize", "client_error",
                  f"AWS ClientError ({error_code}): {error_message}")
        raise
    except BotoCoreError as e:
        log_error("task", "initialize", "botocore_error",
                  f"BotoCoreError during initialization: {str(e)}")
        raise
    except Exception as e:
        log_error("task", "initialize", "unexpected_error",
                  f"Unexpected error during initialization: {str(e)}")
        raise


def _parse_datetime(value, is_end=False):
    # Parse a date or datetime string. Accepted formats:
    #   "YYYY-MM-DD"                      -> 00:00:00 (or 23:59:59 if is_end)
    #   "YYYY-MM-DD HH:MM"                -> uses provided time
    #   "YYYY-MM-DDTHH:MM:SS"             -> uses provided time (ISO, no tz)
    #   "YYYY-MM-DDTHH:MM:SS+00:00"       -> strips timezone, uses UTC time as-is
    #   "YYYY-MM-DDTHH:MM:SSZ"            -> strips Z suffix, uses time as-is
    # Returns a naive datetime object (timezone info stripped).
    if not value:
        return None

    # Strip timezone suffix: +HH:MM, -HH:MM, or trailing Z
    import re
    cleaned = re.sub(r'(Z|[+-]\d{2}:\d{2})$', '', str(value).strip())

    for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            dt = datetime.strptime(cleaned, fmt)
            # If end boundary lands on midnight, push to end-of-day first
            if is_end and dt.hour == 0 and dt.minute == 0 and dt.second == 0:
                return dt.replace(hour=23, minute=59, second=59)
            return dt
        except ValueError:
            continue
    try:
        dt = datetime.strptime(cleaned, '%Y-%m-%d')
        if is_end:
            return dt.replace(hour=23, minute=59, second=59)
        return dt
    except ValueError:
        pass
    raise ValueError(f"Unrecognised date/time format: '{value}'. "
                     "Accepted: 'YYYY-MM-DD', 'YYYY-MM-DD HH:MM', "
                     "'YYYY-MM-DDTHH:MM:SS', 'YYYY-MM-DDTHH:MM:SS+00:00'.")


def _generate_datetime_range(start_dt, end_dt):
    # Generate list of date strings (YYYY-MM-DD) for every calendar day
    # between start_dt and end_dt inclusive.
    date_list = []
    current = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end_day = end_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    while current <= end_day:
        date_list.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    return date_list


def _filter_keys_by_time(json_keys, date_str, start_dt, end_dt):
    # Filter S3 keys to only those whose filename timestamp falls within
    # [start_dt, end_dt]. Filename format: YYYY-MM-DDTHH:MM:SS.json
    # On days that are strictly between start and end, all files pass.
    # On the start day, files must be >= start_dt time.
    # On the end day, files must be <= end_dt time.
    day = datetime.strptime(date_str, '%Y-%m-%d')
    start_day = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end_day   = end_dt.replace(hour=0, minute=0, second=0, microsecond=0)

    is_start_day = (day == start_day)
    is_end_day   = (day == end_day)

    if not is_start_day and not is_end_day:
        return json_keys  # middle day — all files qualify

    filtered = []
    for key in json_keys:
        filename = key.split('/')[-1].replace('.json', '')  # e.g. 2026-03-17T08:00:00
        try:
            file_dt = datetime.strptime(filename, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            filtered.append(key)  # non-standard name, include it
            continue
        if is_start_day and file_dt < start_dt:
            continue
        if is_end_day and file_dt > end_dt:
            continue
        filtered.append(key)
    return filtered


def _build_s3_prefix(ticker, interval, date_str):
    # Build the S3 partition prefix for a given date (no filename)
    # ticker=MSFT/interval=30min/yyyy=2025/mm=03/dd=01/
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        yyyy = date_obj.strftime('%Y')
        mm = date_obj.strftime('%m')
        dd = date_obj.strftime('%d')

        prefix = f"ticker={ticker}/interval={interval}min/yyyy={yyyy}/mm={mm}/dd={dd}/"
        return prefix
    except Exception as e:
        log_error("task", "run", "prefix_building_error",
                  f"Error building S3 prefix: {str(e)}")
        raise


def _list_json_files_for_date(client, bucket, prefix):
    # List all .json files under the partition prefix for a given date.
    # Each bar is stored as its own file named after its timestamp,
    # e.g. 2026-03-17T08:00:00.json, 2026-03-17T08:30:00.json, ...
    # Returns a list of matching S3 keys (empty list if none found).
    try:
        paginator = client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

        json_keys = []
        for page in pages:
            for obj in page.get('Contents', []):
                key = obj['Key']
                if key.endswith('.json'):
                    json_keys.append(key)

        return json_keys

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        log_error("task", "run", "list_objects_error",
                  f"Error listing S3 objects ({error_code}): {e.response.get('Error', {}).get('Message', str(e))}")
        return []
    except Exception as e:
        log_error("task", "run", "unexpected_error_list_objects",
                  f"Unexpected error listing S3 objects: {str(e)}")
        return []


def _send_slack_notification(webhook_url, message):
    # Send notification to Slack via webhook
    try:
        log_info("task", "run", "sending_slack_notification",
                 "Sending Slack notification")

        response = requests.post(
            webhook_url,
            json={'text': message},
            timeout=10
        )

        if response.status_code == 200:
            log_info("task", "run", "slack_notification_sent",
                     "Slack notification sent successfully")
            return True
        else:
            log_error("task", "run", "slack_notification_failed",
                      f"Slack notification failed with status code: {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        log_error("task", "run", "slack_timeout",
                  "Slack notification request timed out")
        return False
    except requests.exceptions.RequestException as e:
        log_error("task", "run", "slack_request_error",
                  f"Error sending Slack notification: {str(e)}")
        return False
    except Exception as e:
        log_error("task", "run", "slack_unexpected_error",
                  f"Unexpected error sending Slack notification: {str(e)}")
        return False


def run(least_action_task_object, client):
    try:
        payload = least_action_task_object.get('payload', {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except (json.JSONDecodeError, ValueError):
                try:
                    payload = ast.literal_eval(payload)
                except (ValueError, SyntaxError) as e:
                    log_error("task", "run", "payload_validation",
                            f"Failed to parse payload: {str(e)}")
                    payload = {}

        # Read directly from payload
        logical_date = payload.get('logical_date')
        ticker = payload.get('ticker')
        interval = payload.get('interval')
        date_range_start = payload.get('date_range_start')
        date_range_end = payload.get('date_range_end')
        notify_always = payload.get('notify_always', False)
        s3_bucket = payload.get('s3_bucket')

        # Extract from connection
        connection = least_action_task_object.get('connection', {})
        slack_webhook_url = connection.get('slack_webhook_url')

        log_info("task", "run", "parameters_extracted",
                 f"Ticker: {ticker}, Interval: {interval}, Notify Always: {notify_always}")

        # Validate required parameters
        if not all([s3_bucket, slack_webhook_url, ticker, interval]):
            log_error("task", "run", "missing_required_parameters",
                      "Missing required configuration or payload parameters")
            return {
                'status': 'failed',
                'execution_type': 'sync',
                'result': None,
                'error': 'Missing required parameters (s3_bucket, slack_webhook_url, ticker, interval)'
            }

        # Determine dates to check
        # date_range_start / date_range_end accept:
        #   "YYYY-MM-DD"               -> start=00:00:00, end=23:59:59
        #   "YYYY-MM-DD HH:MM"         -> uses provided time
        #   "YYYY-MM-DDTHH:MM:SS"      -> uses provided time; midnight end -> bumped to 23:59:59
        # _parse_datetime handles midnight end_dt by pushing to 23:59:59 when is_end=True
        dates_to_check = []
        start_dt = None
        end_dt = None

        if date_range_start and date_range_end:
            start_dt = _parse_datetime(date_range_start)
            end_dt   = _parse_datetime(date_range_end, is_end=True)
            dates_to_check = _generate_datetime_range(start_dt, end_dt)
            log_info("task", "run", "generating_date_range",
                     f"Generating date range from {start_dt} to {end_dt}")
        elif logical_date:
            start_dt = _parse_datetime(logical_date)
            end_dt   = _parse_datetime(logical_date, is_end=True)
            dates_to_check = [start_dt.strftime('%Y-%m-%d')]
            log_info("task", "run", "single_date_validation",
                     f"Validating single date: {logical_date}")
        else:
            log_error("task", "run", "missing_date_parameters",
                      "Either logical_date or (date_range_start and date_range_end) must be provided")
            return {
                'status': 'failed',
                'execution_type': 'sync',
                'result': None,
                'error': 'Either logical_date or (date_range_start and date_range_end) must be provided'
            }

        log_info("task", "run", "dates_to_check",
                 f"Total dates to check: {len(dates_to_check)}")

        # Check each date — a date is valid if at least one .json file exists
        # within the requested time window under its partition prefix.
        found_dates = []
        missing_dates = []
        files_per_date = {}  # date_str -> list of found S3 keys

        for date_str in dates_to_check:
            try:
                prefix = _build_s3_prefix(ticker, interval, date_str)

                log_info("task", "run", "checking_s3_prefix",
                         f"Listing JSON files under prefix for date {date_str}: {prefix}")

                json_keys = _list_json_files_for_date(client, s3_bucket, prefix)
                json_keys = _filter_keys_by_time(json_keys, date_str, start_dt, end_dt)

                if json_keys:
                    found_dates.append(date_str)
                    files_per_date[date_str] = json_keys
                    log_info("task", "run", "files_found",
                             f"Found {len(json_keys)} file(s) for date: {date_str}")
                else:
                    missing_dates.append(date_str)
                    files_per_date[date_str] = []
                    log_info("task", "run", "files_missing",
                             f"No JSON files found for date: {date_str}")

            except Exception as e:
                log_error("task", "run", "date_check_error",
                          f"Error checking date {date_str}: {str(e)}")
                missing_dates.append(date_str)
                files_per_date[date_str] = []

        # Prepare results
        total_checked = len(dates_to_check)
        all_data_found = len(missing_dates) == 0

        log_info("task", "run", "validation_complete",
                 f"Validation complete - Found: {len(found_dates)}, Missing: {len(missing_dates)}, Total: {total_checked}")

        # Slack notification logic
        should_notify = notify_always or len(missing_dates) > 0

        if should_notify:
            if all_data_found:
                total_files = sum(len(v) for v in files_per_date.values())
                slack_message = (
                    "[SUCCESS] S3 Data Validation Passed\\n"
                    f"Ticker: {ticker}\\n"
                    f"Interval: {interval}min\\n"
                    f"Dates checked: {total_checked}\\n"
                    f"Total files found: {total_files}\\n"
                    "All data found"
                )
            else:
                missing_dates_str = ', '.join(missing_dates)
                slack_message = (
                    "[FAILED] S3 Data Validation Failed\\n"
                    f"Ticker: {ticker}\\n"
                    f"Interval: {interval}min\\n"
                    f"Dates checked: {total_checked}\\n"
                    f"Found: {len(found_dates)}\\n"
                    f"Missing: {len(missing_dates)}\\n"
                    f"Missing dates: [{missing_dates_str}]"
                )

            log_info("task", "run", "slack_notification_prepared",
                     f"Slack notification prepared - Status: {'Success' if all_data_found else 'Failure'}")

            _send_slack_notification(slack_webhook_url, slack_message)
        else:
            log_info("task", "run", "slack_notification_skipped",
                     "Slack notification skipped - notify_always=False and all data found")

        return {
            'status': 'success' if all_data_found else 'failed',
            'execution_type': 'sync',
            'result': {
                'total_checked': total_checked,
                'found_count': len(found_dates),
                'missing_count': len(missing_dates),
                'found_dates': found_dates,
                'missing_dates': missing_dates,
                'files_per_date': files_per_date,
                'all_data_found': all_data_found,
                'ticker': ticker,
                'interval': interval,
                'notification_sent': should_notify
            }
        }

    except Exception as e:
        log_error("task", "run", "unexpected_error",
                  f"Unexpected error during run: {str(e)}")
        return {
            'status': 'failed',
            'execution_type': 'sync',
            'result': None,
            'error': str(e)
        }


def check_completion(least_action_task_object, client, run_details):
    try:
        log_info("task", "check_completion", "sync_operation",
                 "Synchronous operation - no status check needed")

        if run_details.get('status') == 'failed':
            return {
                'status': 'failed',
                'message': f"Validation failed: {run_details.get('error', 'Unknown error')}",
                'output': run_details.get('result')
            }

        result = run_details.get('result', {})
        all_data_found = result.get('all_data_found', False)

        if all_data_found:
            log_info("task", "check_completion", "validation_success",
                     "All data found in S3")
            return {
                'status': 'success',
                'message': 'All data found in S3',
                'output': result
            }
        else:
            log_info("task", "check_completion", "validation_failed",
                     f"Data missing for {result.get('missing_count', 0)} dates")
            return {
                'status': 'failed',
                'message': f"Data missing for {result.get('missing_count', 0)} dates",
                'output': result
            }

    except Exception as e:
        log_error("task", "check_completion", "unexpected_error",
                  f"Unexpected error during check_completion: {str(e)}")
        return {
            'status': 'failed',
            'message': f"Status check error: {str(e)}",
            'output': None
        }


def finish(least_action_task_object, client, completion_details, run_details):
    try:
        task_laui = least_action_task_object.get('laui')

        log_info("task", "finish", "starting_cleanup", "Starting cleanup")

        final_status = completion_details.get('status', 'unknown')
        log_info("task", "finish", "final_status",
                 f"Task completed with status: {final_status}")

        if final_status == 'success':
            output = completion_details.get('output', {})
            total_files = sum(len(v) for v in output.get('files_per_date', {}).values())
            log_info("task", "finish", "operation_summary",
                     f"S3 validation successful - {output.get('total_checked', 0)} date(s) checked, {total_files} file(s) found")
        elif final_status == 'failed':
            output = completion_details.get('output', {})
            log_error("task", "finish", "operation_failed",
                      f"S3 validation failed - {output.get('missing_count', 0)} date(s) missing data")

        log_info("task", "finish", "cleanup_completed", "Cleanup completed")

    except Exception as e:
        log_error("task", "finish", "cleanup_error",
                  f"Error during finish/cleanup: {str(e)}") '''}
bashblock = {'main.sh': 
            '''#!/bin/bash
pip install boto3>=1.28.0
pip install botocore>=1.31.0
pip install requests>=2.31.0

echo "Dependencies installed successfully"'''}
connection={
        "region": "us-east-1",
        "aws_access_key_id": "",  # optional — omit to use IAM role
        "aws_secret_access_key": "",  # optional — omit to use IAM role
        "slack_webhook_url": "https://hooks.slack.com/services/T00000/B00000/XXXXXX"
    }
payload={
    "ticker": "",
    "interval": 30,
    "s3_bucket": "",
    "date_range_start": "",
    "date_range_end":  "",
    "notify_always": False
}

prompt = (
    "Check whether S3 data files exist for a ticker/interval partition structure under a given date range. "
    "Required payload fields: ticker, interval, s3_bucket. Required: either logical_date or both date_range_start and date_range_end. "
    "Optional: notify_always (default False — only notifies on missing data). "
    "S3 key pattern: ticker={ticker}/interval={interval}min/yyyy={yyyy}/mm={mm}/dd={dd}/*.json. "
    "Sends a Slack webhook notification from connection.slack_webhook_url on failure (or always if notify_always=True). "
    "Auth: explicit aws_access_key_id/aws_secret_access_key from connection, fallback to IAM role. "
    "Returns found_dates, missing_dates, files_per_date, and notification_sent on success."
)

install_docs = """# AWSS3ValidateDataExists — Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0
    pip install requests>=2.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket", "s3:GetObject"],
      "Resource": ["arn:aws:s3:::your-bucket", "arn:aws:s3:::your-bucket/*"]
    }

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to instance — no connection keys needed           |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
"""

guide_docs = """# AWSS3ValidateDataExists — Operator Guide

## What it does

Validates whether JSON data files exist in S3 for a ticker/interval/date partition structure.
Checks each date in the range and filters by timestamp within [start_dt, end_dt]. Sends a
Slack notification on missing data (or always when notify_always=True).

---

## Connection

    {
      "region": "us-east-1",
      "aws_access_key_id": "...",
      "aws_secret_access_key": "...",
      "slack_webhook_url": "https://hooks.slack.com/services/..."
    }

---

## Payload

    {
      "ticker": "MSFT",
      "interval": 30,
      "s3_bucket": "my-data-bucket",
      "date_range_start": "2026-01-01",
      "date_range_end": "2026-01-07",
      "notify_always": false
    }

Use `logical_date` for a single-day check instead of date_range_start/end.

---

## Output (on success)

    {
      "total_checked": 7,
      "found_count": 6,
      "missing_count": 1,
      "found_dates": [...],
      "missing_dates": ["2026-01-04"],
      "files_per_date": {...},
      "all_data_found": false,
      "notification_sent": true
    }
"""

description = """
Checks if S3 JSON data files exist for a given ticker/interval/date partition. Validates
each calendar day in the requested range and filters file timestamps within the time window.
Sends a Slack webhook notification when data is missing or when notify_always=True.
Auth: explicit access keys from connection, fallback to IAM role.
"""

publisher = "LeastActionLabs"

metadata = {
    "service": "S3",
    "category": "Storage",
    "tags": ["s3", "validate", "data", "exists", "slack", "notification", "aws"],
    "airflow_equivalent": "S3KeySensor"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

The S3 partition structure is hardcoded as ticker={ticker}/interval={interval}min/yyyy={yyyy}/mm={mm}/dd={dd}/*.json — purpose-built for this layout. slack_webhook_url is read from connection. notify_always=false means Slack only triggers on missing data. Use aws_session_token (not session_token) for temporary credentials.
"""
