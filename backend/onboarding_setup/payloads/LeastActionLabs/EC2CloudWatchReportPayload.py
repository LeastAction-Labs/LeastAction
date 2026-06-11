# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
payload = '''{
    "data": {
        "instance_id":  "",
        "region":       "us-east-1",
        "hours":        24,
        "parent_laui":  "<your-parent-folder-laui>",
        "email_to":     ["you@example.com"],
        "email_from":   "you@gmail.com",
        "report_title": "EC2 CloudWatch Report"
    }
}'''

# Notes:
# - instance_id: leave empty ("") to auto-detect from EC2 instance metadata (IMDSv2).
#   Useful when the operator runs directly on the target EC2 instance.
# - region: AWS region where the EC2 instance lives.
# - hours: lookback window (default 24). CloudWatch free-tier uses 5-min resolution.
# - parent_laui: LAUI of the catalog folder for the HTML report asset.
# - email_to: list of recipient Gmail addresses.
# - email_from: must match smtp_user in the connection (your Gmail address).
# - report_title: name shown in the report header and catalog asset.
#
# Connection fields (set in EC2CloudWatchReportConnection.py):
#   region                 - AWS region
#   aws_access_key_id      - leave empty on EC2 (IAM role used automatically)
#   aws_secret_access_key  - leave empty on EC2
#   smtp_host / smtp_port  - smtp.gmail.com / 587
#   smtp_user              - your Gmail address
#   smtp_password          - Gmail App Password (16-char, from myaccount.google.com/apppasswords)
#
# IAM role permissions needed (attach to EC2 instance profile):
#   cloudwatch:GetMetricData, cloudwatch:ListMetrics, ec2:DescribeInstances

prompt = "EC2 CloudWatch report payload. Set instance_id (or leave empty for auto-detect), region, hours lookback, parent_laui for catalog, email_to/from for delivery."

install_docs = """# EC2CloudWatchReportPayload — Setup

Used with EC2CloudWatchReport operator. Leave instance_id empty when running on the EC2
instance itself (auto-detected via IMDSv2). Set parent_laui to publish to catalog.
"""

guide_docs = """# EC2CloudWatchReportPayload — Guide

instance_id: leave empty to auto-detect from EC2 metadata
region: AWS region (default us-east-1)
hours: lookback window in hours (default 24)
parent_laui: catalog folder LAUI for the HTML report
email_to: list of recipient addresses
email_from: must match smtp_user in connection
"""

description = "Payload for EC2 CloudWatch report generation with configurable lookback window, catalog publish, and email delivery."

publisher = "LeastAction"

metadata = {
    "service": "EC2, CloudWatch",
    "category": "Monitoring",
    "tags": ["ec2", "cloudwatch", "report", "email", "catalog", "payload"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

