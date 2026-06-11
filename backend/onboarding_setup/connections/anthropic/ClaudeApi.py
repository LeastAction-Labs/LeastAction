# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import os
connection_type = "anthropic"

connection = {
    "api_key": os.getenv("CLAUDE_API_KEY", ""),
    "model": "claude-haiku-4-5-20251001",
    "token_limit": 10000
}

prompt = "Configure Anthropic Claude API connection. Set api_key to your Anthropic API key (or use CLAUDE_API_KEY env var). Choose model and token limit."

install_docs = """# ClaudeApi — Connection Setup

Get your API key from: https://console.anthropic.com/

Set the environment variable CLAUDE_API_KEY or enter the key directly in api_key.

## Fields

| Field       | Required | Description                                           |
|-------------|----------|-------------------------------------------------------|
| api_key     | Yes      | Anthropic API key (or set CLAUDE_API_KEY env var)     |
| model       | Yes      | Claude model ID (e.g. claude-haiku-4-5-20251001)      |
| token_limit | No       | Max tokens per request (default 10000)                |
"""

guide_docs = """# ClaudeApi — Connection Guide

Used by operators and actions that call the Anthropic Claude API for AI-powered tasks
such as data analysis, report generation, SQL generation, and natural language processing.

Current models:
- claude-haiku-4-5-20251001 — fastest, most cost-effective
- claude-sonnet-4-6 — balanced capability and speed
- claude-opus-4-7 — most capable
"""

description = "Anthropic Claude API connection with model selection and token limit configuration."

publisher = "LeastAction"

metadata = {
    "service": "Anthropic",
    "category": "AI",
    "tags": ["anthropic", "claude", "ai", "llm", "api", "connection"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
