# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
connection_type = "leastaction"

connection = {
    "smtp_host":     "smtp.gmail.com",
    "smtp_port":     587,
    "smtp_user":     "you@gmail.com",
    "smtp_password": "xxxx xxxx xxxx xxxx"
}

# Gmail setup (2 minutes):
# 1. Enable 2-Step Verification on your Google account
#    https://myaccount.google.com/security
# 2. Go to App Passwords -> create one for "Mail"
#    https://myaccount.google.com/apppasswords
# 3. Paste the 16-character password (spaces optional) into smtp_password above
#
# For other providers:
#   SendGrid: host=smtp.sendgrid.net  port=587  user=apikey  password=SG.xxxxx
#   Brevo:    host=smtp-relay.brevo.com  port=587  user=<your-brevo-login>  password=<smtp-key>

prompt = "Configure SMTP connection for LeastAction monitoring report email delivery. Used with LeastActionMonitoring operator."

install_docs = """# LeastActionMonitoringConnection — Connection Setup

Used by LeastActionMonitoring operator to send the HTML monitoring report via email.

## Gmail App Password Setup

1. Enable 2FA: myaccount.google.com/security
2. Create App Password: myaccount.google.com/apppasswords
3. Enter 16-character password as smtp_password
"""

guide_docs = """# LeastActionMonitoringConnection — Connection Guide

SMTP-only connection for the LeastActionMonitoring operator. Provides email credentials
for sending the HTML performance and monitoring report. No AWS credentials needed here —
the monitoring operator reads from local DuckDB log files.
"""

description = "SMTP connection for LeastAction monitoring report email delivery."

publisher = "LeastAction"

metadata = {
    "service": "LeastAction",
    "category": "Monitoring",
    "tags": ["smtp", "email", "monitoring", "leastaction", "connection"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

