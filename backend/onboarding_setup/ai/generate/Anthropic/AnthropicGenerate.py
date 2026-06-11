# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
bashblock = {
    "install_dependencies.sh": "pip install langchain-anthropic",
}

codeblock = {
    "main.py": '''
from langchain_anthropic import ChatAnthropic


def run(connection, messages, output_schema, **kwargs):
    api_key = connection.get("api_key", "")
    model = connection.get("model", "")
    token_limit = connection.get("token_limit", 8192)

    llm = ChatAnthropic(
        anthropic_api_key=api_key,
        model_name=model,
        max_tokens=token_limit,
        temperature=0.0,
        timeout=10000,
        stop=None,
    )
    llm_with_structured_output = llm.with_structured_output(output_schema, include_raw=True)
    return llm_with_structured_output.invoke(messages)
'''
}

connection = {
    "api_key": "YOUR-API-KEY-HERE",
    "model": "claude-haiku-4-5-20251001",
    "token_limit": 10000,
}

prompt = "LeastAction chat handler that invokes an Anthropic Claude model via LangChain with structured output. Accepts messages, output_schema, and connection config."

install_docs = """# AnthropicChat — Setup

Requires a ClaudeApi connection with api_key and model (e.g. claude-haiku-4-5-20251001).
Install dependency: pip install langchain-anthropic
"""

guide_docs = "Invokes Claude via LangChain ChatAnthropic with structured output. Pass messages as a list of LangChain message objects, output_schema as a Pydantic model or JSON schema. Returns raw + parsed response."

description = "LeastAction AI chat handler — invokes Claude via LangChain with structured output support for AI-powered pipeline tasks."

publisher = "LeastAction"

metadata = {
    "service": "Anthropic",
    "category": "AI Chat",
    "tags": ["anthropic", "claude", "langchain", "chat", "llm", "structured-output", "ai"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
