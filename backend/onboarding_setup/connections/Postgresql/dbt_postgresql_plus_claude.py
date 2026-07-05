# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
connection_type = "postgresql"

connection = {
  "host": "postgres-demo",
  "port": 5432,
  "database": "postgres_demo_db",
  "user": "postgres",
  "password": "postgres",
  "claude_api_key": "",
  "claude_model": "claude-haiku-4-5-20251001",
  "claude_token_limit": 4096
}

prompt = "Combined PostgreSQL + Claude API connection for AI-powered report generation. Points to the bundled postgres-demo database. Set claude_api_key to enable."

install_docs = """# dbt_postgresql_plus_claude — Connection Setup

Points to the `postgres-demo` container for database access and includes Anthropic Claude
API fields for AI-powered report generation.

## Fields
| Field | Value | Notes |
|---|---|---|
| host | postgres-demo | Internal docker hostname |
| port | 5432 | |
| database | postgres_demo_db | |
| user | postgres | |
| password | postgres | |
| claude_api_key | *(your key)* | Required — get from console.anthropic.com |
| claude_model | claude-haiku-4-5-20251001 | Model for report generation |
| claude_token_limit | 4096 | Max tokens per response |
"""

guide_docs = """# dbt_postgresql_plus_claude — Connection Guide

Combined PostgreSQL + Claude API connection. Used by PostgresClaudeReportDebug operator.
"""

description = "Combined PostgreSQL + Claude API connection for AI-powered data analysis — points to postgres-demo by default."

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL, Anthropic",
    "category": "Demo",
    "tags": ["postgresql", "claude", "anthropic", "dbt", "reporting", "connection", "demo"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
