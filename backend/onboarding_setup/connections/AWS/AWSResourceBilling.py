# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
connection_type = "AWS"

connection = {
  "region": "us-east-1",
  "aws_access_key_id": "",
  "aws_secret_access_key": "",
  "session_token": "",
  "slack_webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
}

prompt = "Configure AWS connection for resource and billing monitoring with Slack notifications. Includes AWS credentials and a Slack webhook URL."

install_docs = """# AWSResourceBilling — Connection Setup

Used with GetResourceAndBillingOperator. Requires AWS credentials with Cost Explorer
and resource describe permissions, plus a Slack webhook for alerts.

## Fields

| Field                 | Required | Description                                    |
|-----------------------|----------|------------------------------------------------|
| region                | Yes      | AWS region                                     |
| aws_access_key_id     | No       | Leave empty to use IAM role                    |
| aws_secret_access_key | No       | Leave empty to use IAM role                    |
| session_token         | No       | For temporary STS credentials                  |
| slack_webhook_url     | Yes      | Slack Incoming Webhook URL for billing alerts  |
"""

guide_docs = """# AWSResourceBilling — Connection Guide

Used by GetResourceAndBillingOperator to fetch AWS cost and resource usage data and send
Slack alerts when thresholds are exceeded. Leave access keys empty when using an IAM role.
"""

description = "AWS connection for resource and billing monitoring with Slack webhook for cost alerts."

publisher = "LeastAction"

metadata = {
    "service": "Cost Explorer, EC2, S3",
    "category": "Billing",
    "tags": ["aws", "billing", "cost", "slack", "monitoring", "connection"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
