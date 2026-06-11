# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
connection_type = "leastaction"

connection = {
    "region":        "us-east-1",
    # AWS credentials — leave empty on EC2 (IAM role used automatically)
    # Fill in for local/dev testing:
    "aws_access_key_id":     "",
    "aws_secret_access_key": "",
    "aws_session_token":     "",   # optional, only for temporary STS credentials
    # SMTP (Gmail)
    "smtp_host":     "smtp.gmail.com",
    "smtp_port":     587,
    "smtp_user":     "you@gmail.com",
    "smtp_password": "xxxx xxxx xxxx xxxx"
}

# region      - AWS region where your EC2 instance lives (used for CloudWatch + EC2 API calls).
#               IAM role on the instance is used automatically — no access keys needed.
#
# Gmail setup (2 minutes):
# 1. Enable 2-Step Verification on your Google account
#    https://myaccount.google.com/security
# 2. Go to App Passwords -> create one for "Mail"
#    https://myaccount.google.com/apppasswords
# 3. Paste the 16-character password (spaces optional) into smtp_password above
#
# IAM role required permissions (attach to EC2 instance profile):
#   cloudwatch:GetMetricData
#   cloudwatch:ListMetrics
#   ec2:DescribeInstances
#
# For other SMTP providers:
#   SendGrid: host=smtp.sendgrid.net  port=587  user=apikey  password=SG.xxxxx
#   Brevo:    host=smtp-relay.brevo.com  port=587  user=<login>  password=<smtp-key>

prompt = "Configure AWS CloudWatch + SMTP connection for the EC2CloudWatchReport operator. Includes region, optional AWS keys, and Gmail SMTP for email delivery."

install_docs = """# EC2CloudWatchReportConnection — Connection Setup

Used by EC2CloudWatchReport operator to fetch CloudWatch metrics and email the HTML report.

## AWS Permissions

Attach to EC2 instance profile:
  cloudwatch:GetMetricData, cloudwatch:ListMetrics, ec2:DescribeInstances

## Gmail App Password

1. Enable 2FA on Google account
2. Go to myaccount.google.com/apppasswords
3. Create App Password for "Mail"
4. Enter as smtp_password
"""

guide_docs = """# EC2CloudWatchReportConnection — Connection Guide

Provides AWS credentials (or IAM role) for CloudWatch API access, plus SMTP credentials
for emailing the generated HTML report. Used exclusively with EC2CloudWatchReport operator.
"""

description = "AWS CloudWatch + SMTP connection for EC2 monitoring report generation and email delivery."

publisher = "LeastAction"

metadata = {
    "service": "CloudWatch, EC2",
    "category": "Monitoring",
    "tags": ["cloudwatch", "ec2", "smtp", "email", "monitoring", "connection"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

