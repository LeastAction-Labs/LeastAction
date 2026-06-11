# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
connection_type = "AWS"

connection={
        "region": "us-east-1",
        "aws_access_key_id": "",
        "aws_secret_access_key": "",
        "slack_webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    }

prompt = "Configure AWS S3 connection with Slack webhook for data validation and notification. Used with AWSS3ValidateDataExists operator."

install_docs = """# AWSS3ValidateAndNotify — Connection Setup

Used with AWSS3ValidateDataExists operator to check S3 data availability and send Slack
notifications. Leave access keys empty to use IAM role.

## Fields

| Field                 | Required | Description                             |
|-----------------------|----------|-----------------------------------------|
| region                | Yes      | AWS region                              |
| aws_access_key_id     | No       | Leave empty to use IAM role             |
| aws_secret_access_key | No       | Leave empty to use IAM role             |
| slack_webhook_url     | Yes      | Slack webhook URL for notifications     |
"""

guide_docs = """# AWSS3ValidateAndNotify — Connection Guide

Used with AWSS3ValidateDataExists to check S3 data partitions and notify via Slack.
Supports IAM role auth (leave access keys empty) or explicit key-based auth.
"""

description = "AWS S3 connection with Slack webhook for data existence validation and alert notifications."

publisher = "LeastAction"

metadata = {
    "service": "S3",
    "category": "Storage",
    "tags": ["aws", "s3", "validate", "slack", "notification", "connection"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
