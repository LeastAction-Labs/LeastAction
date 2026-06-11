# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import asyncio
import json
from typing import Any

from fastmcp import FastMCP

from src.common.logger.logger import log_error


async def get_tool_definitions(mcp_server: FastMCP) -> list[dict]:
    """Extract tool definitions from FastMCP server as JSON-schema dicts
    suitable for passing to LLM tool-calling APIs."""
    tool_list = mcp_server._tool_manager.list_tools()
    if asyncio.iscoroutine(tool_list):
        tool_list = await tool_list
    tools = []
    for tool in tool_list:
        tools.append(
            {
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.parameters
                if hasattr(tool, "parameters")
                else tool.input_schema,
            }
        )
    return tools


async def execute_tool(mcp_server: FastMCP, tool_name: str, arguments: dict) -> str:
    """Execute a tool on the MCP server and return the result as a string."""
    try:
        result = await mcp_server._tool_manager.call_tool(tool_name, arguments)

        # FastMCP returns a ToolResult/CallToolResult with a .content list of TextContent items
        if hasattr(result, "content"):
            parts = [item.text if hasattr(item, "text") else str(item) for item in result.content]
            return "\n".join(parts) if parts else "{}"

        # Older FastMCP returned a plain list of content items directly
        if isinstance(result, list):
            parts = []
            for item in result:
                if hasattr(item, "text"):
                    parts.append(item.text)
                elif isinstance(item, dict):
                    parts.append(json.dumps(item, default=str))
                else:
                    parts.append(str(item))
            return "\n".join(parts) if parts else "[]"

        if isinstance(result, dict):
            return json.dumps(result, default=str)

        return str(result)
    except Exception as e:
        log_error("mcp", "agent", "execute_tool", f"Tool '{tool_name}' failed: {e}")
        return json.dumps({"error": f"Tool execution failed: {str(e)}"})


async def run_agent_loop(
    module: Any,
    connection: dict,
    messages: list,
    mcp_server: FastMCP,
    max_iterations: int = 50,
    allowed_tools: list[str] | None = None,
) -> tuple[str, list[str]]:
    """Run the agent loop: call codeblock's run() → execute tool_calls → repeat.

    Args:
        module: Loaded Python module with run(connection, messages, tools) function
        connection: API credentials dict (api_key, model, token_limit, etc.)
        messages: List of message dicts [{"role": "system"|"user"|"assistant"|"tool", "content": ...}]
        mcp_server: FastMCP server instance for tool execution
        max_iterations: Safety cap to prevent runaway loops
        allowed_tools: If provided, only these tool names are exposed to the LLM. Empty list or None = all tools.

    Returns:
        (final_text_response, list_of_tool_names_called)
    """
    tool_defs = await get_tool_definitions(mcp_server)
    allowed_set = set(allowed_tools) if allowed_tools else None
    if allowed_set:
        tool_defs = [t for t in tool_defs if t["name"] in allowed_set]
    tools_called: list[str] = []

    for iteration in range(max_iterations):
        # Call the user's codeblock run() function (handle both sync and async)
        response = module.run(connection, messages, tools=tool_defs)
        if asyncio.iscoroutine(response):
            response = await response

        # Extract tool_calls from response
        tool_calls = response.get("tool_calls")

        if not tool_calls:
            # No tool calls — return final text
            final_content = response.get("content", "")
            return final_content, tools_called

        # Process tool calls
        # Normalize to "args" key — accepted by LangChain, and we read from
        # it below. Codeblocks can return either "args" or "arguments".
        normalized_tool_calls = []
        for tc in tool_calls:
            normalized_tool_calls.append(
                {
                    "name": tc["name"],
                    "id": tc.get("id", f"call_{tc['name']}_{iteration}"),
                    "args": tc.get("args") or tc.get("arguments", {}),
                }
            )

        # Append the assistant message with tool_calls to message history
        messages.append(
            {
                "role": "assistant",
                "content": response.get("content", ""),
                "tool_calls": normalized_tool_calls,
            }
        )

        # Execute each tool and append results
        for tool_call in normalized_tool_calls:
            tool_name = tool_call["name"]
            tool_id = tool_call["id"]
            arguments = tool_call["args"]

            # Parse arguments if they're a string
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}

            # Block tools not in the allowed list
            if allowed_set and tool_name not in allowed_set:
                log_error(
                    "mcp",
                    "agent",
                    "run_agent_loop",
                    f"Tool '{tool_name}' is not in allowed_tools list",
                )
                result = json.dumps(
                    {
                        "error": f"Tool '{tool_name}' is not allowed. You cannot perform this operation. Allowed tools: {sorted(allowed_set)}"
                    }
                )
            else:
                tools_called.append(tool_name)
                result = await execute_tool(mcp_server, tool_name, arguments)

            # Append tool result message
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": result,
                }
            )

    # Max iterations reached — return whatever we have
    log_error("mcp", "agent", "run_agent_loop", f"Max iterations ({max_iterations}) reached")
    return (
        "I've reached the maximum number of tool-calling steps. Here's what I found so far based on the tools I used.",
        tools_called,
    )
