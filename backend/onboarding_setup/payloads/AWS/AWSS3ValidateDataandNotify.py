# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
payload={
    "ticker": "MSFT",
    "interval": 30,
    "s3_bucket": "my-data-bucket",
    "date_range_start": "",
    "date_range_end":   "",
    "notify_always": False
}

prompt = "S3 data validation payload. Set ticker, interval (minutes), s3_bucket, and date range. notify_always=true sends Slack notification even when data is present."

install_docs = """# AWSS3ValidateDataandNotify Payload — Setup

Used with AWSS3ValidateDataExists operator. Set ticker and interval to match your S3 partition
structure (ticker={ticker}/interval={interval}min/...). Provide date_range_start and
date_range_end, or use logical_date for a single-day check.
"""

guide_docs = """# AWSS3ValidateDataandNotify Payload — Guide

ticker: stock/data ticker symbol
interval: data interval in minutes (e.g. 30 for 30-minute bars)
s3_bucket: S3 bucket name
date_range_start / date_range_end: ISO date strings (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
notify_always: if false, only notifies on missing data
"""

description = "S3 data existence validation payload for ticker/interval partition structure with Slack notification on missing data."

publisher = "LeastAction"

metadata = {
    "service": "S3",
    "category": "Storage",
    "tags": ["s3", "validate", "ticker", "payload", "notification"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
