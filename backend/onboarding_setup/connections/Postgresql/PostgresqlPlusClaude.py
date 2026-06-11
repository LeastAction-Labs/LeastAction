# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
connection_type = "postgresql"

connection = {
  "host": "localhost",
  "port": 5432,
  "database": "mydb",
  "user": "postgres",
  "password": "",
  "claude_api_key": "",
  "claude_model": "claude-haiku-4-5-20251001",
  "claude_token_limit": 4096
}

prompt = "Configure PostgreSQL + Claude API combined connection for AI-powered data analysis and reporting actions."

install_docs = """# PostgresqlPlusClaude — Connection Setup

Combined connection providing both PostgreSQL database access and Anthropic Claude API
credentials. Used by actions that query the database then analyze results with Claude.

## Fields

Standard PostgreSQL: host, port, database, user, password
Claude API: claude_api_key (from console.anthropic.com), claude_model, claude_token_limit
"""

guide_docs = """# PostgresqlPlusClaude — Connection Guide

Used by PostgresqlToClaudeChatToHtmlReportToAsset and similar actions that combine
database queries with AI-powered analysis. Provides both psycopg2 and Anthropic API
credentials in a single connection object.
"""

description = "Combined PostgreSQL database + Anthropic Claude API connection for AI-powered data analysis."

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL, Anthropic",
    "category": "AI Reporting",
    "tags": ["postgresql", "claude", "anthropic", "ai", "database", "connection"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

