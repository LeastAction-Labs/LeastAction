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


def run(connection, messages, tools=None):
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

    if tools:
        llm = llm.bind_tools(tools)

    response = llm.invoke(messages)

    result = {"content": response.content if isinstance(response.content, str) else ""}

    if hasattr(response, "tool_calls") and response.tool_calls:
        result["tool_calls"] = [
            {
                "name": tc["name"],
                "id": tc.get("id", ""),
                "arguments": tc.get("args", {}),
            }
            for tc in response.tool_calls
        ]

    return result
'''
}

connection = {
    "api_key": "YOUR-API-KEY-HERE",
    "model": "claude-haiku-4-5-20251001",
    "token_limit": 10000,
}

prompt = "Anthropic Claude conversational agent with optional MCP tool-calling support."

install_docs = """# AnthropicAgent — Setup

Requires a ClaudeApi connection with api_key and model (e.g. claude-haiku-4-5-20251001).
Install dependency: pip install langchain-anthropic
"""

guide_docs = "Conversational agent using Claude via LangChain. Optionally binds MCP tools via bind_tools(). Returns content string and tool_calls list if tools were invoked."

description = "Anthropic Claude conversational agent — supports MCP tool-calling for the chat widget."

publisher = "LeastAction"

metadata = {
    "service": "Anthropic",
    "category": "AI Agent",
    "tags": ["anthropic", "claude", "langchain", "agent", "chat", "mcp", "tools", "ai"]
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
