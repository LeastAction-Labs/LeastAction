# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
connection_type = "git"

connection =  {
  "git_connection": {
    "git_username": "github_username",
    "git_token": "github_personal_access_token"
  },
  "ec2_connection": {
    "ec2_instance_id": "i-0123456789abcdef0",
    "region": "us-east-1"
  }
}

prompt = "Configure combined GitHub + EC2 connection for Git pull and deploy to EC2 via SSM. Used with EC2GitPullAndInstall action."

install_docs = """# AWSEC2GitPull — Connection Setup

Combines GitHub authentication (username + PAT) with EC2 instance targeting for
the EC2GitPullAndInstall action.

## GitHub PAT Setup

1. Go to GitHub → Settings → Developer settings → Personal access tokens
2. Create a token with repo read access
3. Enter username and token below

## Fields

git_connection.git_username, git_connection.git_token: GitHub credentials
ec2_connection.ec2_instance_id, ec2_connection.region: Target EC2 instance
"""

guide_docs = """# AWSEC2GitPull — Connection Guide

Used with EC2GitPullAndInstall action to authenticate with GitHub and target a specific
EC2 instance for deployment via SSM Run Command.
"""

description = "Combined GitHub + EC2 connection for Git pull and install deployment to EC2 via SSM."

publisher = "LeastAction"

metadata = {
    "service": "GitHub, EC2, SSM",
    "category": "DevOps",
    "tags": ["github", "ec2", "git", "deploy", "connection", "ssm"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
