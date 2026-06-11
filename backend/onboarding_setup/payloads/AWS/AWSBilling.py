# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
payload = {
  "data": {
    "enable_cost_explorer": True,
    "cost_lookback_days": 30,
    "cost_start_date": "",
    "cost_end_date": "",
    "cost_use_current_month": False,
    "warning_limits": {
      "total_cost_warning_usd": 1,
      "total_cost_critical_usd": 100,
      "service_cost_limits": {
        "Amazon EC2": {
          "warning_usd": 200,
          "critical_usd": 400
        },
        "Amazon RDS": {
          "warning_usd": 100,
          "critical_usd": 200
        },
        "AWS Lambda": {
          "warning_usd": 50,
          "critical_usd": 100
        },
        "Amazon S3": {
          "warning_usd": 30,
          "critical_usd": 60
        }
      },
      "region_cost_limits": {
        "us-east-1": {
          "warning_usd": 300,
          "critical_usd": 600
        },
        "eu-west-1": {
          "warning_usd": 150,
          "critical_usd": 300
        }
      },
      "resource_count_limits": {
        "EC2": {
          "warning": 20,
          "critical": 40
        },
        "RDS": {
          "warning": 10,
          "critical": 20
        },
        "Lambda": {
          "warning": 50,
          "critical": 100
        },
        "DynamoDB": {
          "warning": 20,
          "critical": 40
        },
        "LoadBalancer": {
          "warning": 10,
          "critical": 20
        },
        "S3": {
          "warning": 30,
          "critical": 60
        }
      },
      "ec2_running_warning": 10,
      "ec2_running_critical": 25,
      "s3_total_warning": 20,
      "s3_total_critical": 50,
      "s3_unencrypted_warning": 1,
      "s3_unencrypted_critical": 5,
      "s3_public_warning": 1,
      "s3_public_critical": 3
    }
  }
}

prompt = "AWS billing and resource usage report payload. Configures thresholds for cost alerts by service/region, EC2 instance counts, and S3 security checks."

install_docs = """# AWSBilling Payload — Setup

Used with GetResourceAndBillingOperator. Set warning/critical thresholds per service and
resource type. All values in USD for cost limits, counts for resource limits.
"""

guide_docs = """# AWSBilling Payload — Guide

Defines thresholds for:
- Total cost (warning_usd, critical_usd)
- Per-service cost limits (EC2, RDS, Lambda, S3)
- Per-region cost limits
- Resource count limits (EC2, RDS, Lambda, DynamoDB, LoadBalancer, S3)
- S3 security (unencrypted/public buckets)

Set enable_cost_explorer=true and specify date range or use cost_use_current_month=true.
"""

description = "AWS billing report payload with configurable cost and resource count thresholds for Cost Explorer monitoring."

publisher = "LeastAction"

metadata = {
    "service": "Cost Explorer, EC2, S3",
    "category": "Billing",
    "tags": ["aws", "billing", "cost", "thresholds", "monitoring", "payload"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
