# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
payload = '''{
    "data": {
        "start_date":  "",
        "end_date":    "",
        "parent_laui": "",
        "report_name": "LeastAction Monitoring Report",
        "email_to":    ["you@example.com"],
        "email_from":  "you@gmail.com"
    }
}'''

# Notes:
# - start_date / end_date: ISO 8601 datetime strings, e.g. "2026-03-16T00:00:00"
#   Leave empty ("") to default to the last 24 hours.
# - parent_laui: LAUI of the catalog folder where the HTML report asset will be published.
# - report_name: name for the catalog asset (defaults to "Monitoring Report YYYY-MM-DD HH:MM").
# - email_to: list of Gmail addresses to receive the report.
# - email_from: must match smtp_user in the connection (your Gmail address).

prompt = "LeastAction monitoring report payload. Set date range (or leave empty for last 24h), parent_laui for catalog, and email delivery settings."

install_docs = """# LeastActionMonitoringPayload — Setup

Used with LeastActionMonitoring operator. Leave start_date/end_date empty to default to
the last 24 hours. Set parent_laui to publish the report to the LeastAction catalog.
"""

guide_docs = """# LeastActionMonitoringPayload — Guide

start_date / end_date: ISO 8601 strings (e.g. "2026-03-16T00:00:00"), or leave empty for last 24h
parent_laui: catalog folder LAUI for the HTML report asset
report_name: display name for the catalog asset
email_to: list of recipient addresses
email_from: must match smtp_user in connection
"""

description = "Payload for LeastAction performance monitoring report with configurable date range, catalog publish, and email delivery."

publisher = "LeastAction"

metadata = {
    "service": "LeastAction",
    "category": "Monitoring",
    "tags": ["monitoring", "performance", "report", "email", "catalog", "payload"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

