# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
payload={
  "script_path": "path/to/your/script.py",
  "script_args": "ticker_name date interval alpaca_api_key alpaca_secret_key s3_bucket_name"
}

prompt = "Payload for running a ticker data script on EC2. Set script_path to the Python script location and script_args with all required arguments."

install_docs = """# AWSRunTickerScript Payload — Setup

Used with AWSEC2RunShellCommand or similar operator. Provide the path to the script
on the EC2 instance and the arguments string.
"""

guide_docs = """# AWSRunTickerScript Payload — Guide

script_path: absolute path to the Python script on the EC2 instance
script_args: space-separated arguments in order: ticker_name date interval alpaca_api_key alpaca_secret_key s3_bucket_name
"""

description = "Payload for executing a ticker data collection script on EC2 with Alpaca API credentials and S3 destination."

publisher = "LeastAction"

metadata = {
    "service": "EC2",
    "category": "Finance",
    "tags": ["ticker", "alpaca", "s3", "script", "ec2", "payload"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

