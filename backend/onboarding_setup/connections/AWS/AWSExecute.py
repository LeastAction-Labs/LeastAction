# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
connection_type = "AWS"

connection = {
  "ec2_instance_id": "i-0123456789abcdef0",
  "region": "us-east-1",
  "aws_access_key_id": "",
  "aws_secret_access_key": "",
  "session_token": ""
}

prompt = "Configure AWS connection for EC2 shell command execution via SSM. Set ec2_instance_id to the target instance. Leave access keys empty to use IAM role."

install_docs = """# AWSExecute — Connection Setup

No Python packages required. Used with AWSEC2RunShellCommand operator.

## Fields

| Field                 | Required | Description                          |
|-----------------------|----------|--------------------------------------|
| ec2_instance_id       | Yes      | Target EC2 instance ID               |
| region                | Yes      | AWS region                           |
| aws_access_key_id     | No       | Leave empty to use IAM role          |
| aws_secret_access_key | No       | Leave empty to use IAM role          |
| session_token         | No       | For temporary STS credentials        |
"""

guide_docs = """# AWSExecute — Connection Guide

Used by the AWSEC2RunShellCommand operator to connect to a specific EC2 instance via SSM.
Leave access keys empty when running on an EC2 instance with an appropriate IAM role.
"""

description = "AWS connection with EC2 instance ID for SSM-based shell command execution via AWSEC2RunShellCommand."

publisher = "LeastAction"

metadata = {
    "service": "EC2, SSM",
    "category": "Compute",
    "tags": ["aws", "ec2", "ssm", "connection", "shell"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
