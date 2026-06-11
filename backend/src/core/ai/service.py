# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import json
from pathlib import Path
from typing import Any

from anthropic import APIError, APIStatusError
from fastapi import Request
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, ValidationError

from src.common.exceptions import AIError, LAException, NotFoundError, PartialGenerationError
from src.common.logger.logger import log_error
from src.core.ai.prompts import AGENT_SYSTEM_PROMPT
from src.core.ai.schema import (
    REQUIRED_FIELDS_MAP,
    SCHEMA_MAP,
    AgentRequest,
    AgentResponse,
    AIResponse,
    GenerateRequest,
    ItemType,
    get_system_prompt_map,
)
from src.core.catalog.service import CatalogService
from src.core.celery.utils import create_module_from_codeblock, load_module
from src.core.validation.service import CodeblockValidator


def _parse_content_type_marker(content: str):
    """
    If the AI prefixes its response with [content_type:X] on the first line,
    strip the marker and return (content_type, cleaned_content).
    Otherwise return (None, original_content).
    """
    import re

    match = re.match(r"^\[content_type:(\w+)\]\n?", content)
    if match:
        return match.group(1), content[match.end() :]
    return None, content


def _detect_content_type(content: str) -> str:
    s = content.strip()
    if s.startswith("<!DOCTYPE html") or s.startswith("<html") or s.startswith("<!doctype html"):
        return "html"
    return "markdown"


class AIService:
    def __init__(
        self,
        catalog_service: CatalogService,
        codeblock_validator: CodeblockValidator,
        mcp_server=None,
    ) -> None:
        self.catalog_service = catalog_service
        self.codeblock_validator = codeblock_validator
        self.mcp_server = mcp_server
        self.schema_map = SCHEMA_MAP
        self.system_prompt_map = get_system_prompt_map()
        self.required_fields_map = REQUIRED_FIELDS_MAP
        self.ai_action_dir = Path("/tmp/leastaction_ai_actions")

    async def generate(self, request: GenerateRequest) -> AIResponse:
        try:
            # 1. Fetch ai_chat item -> extract codeblock and connection
            chat_item, e = await self.catalog_service.safe_find_item(item_laui=request.chat_laui)
            if not chat_item:
                if isinstance(e, LAException):
                    e.message = "Chat " + e.message
                raise e
            codeblock = chat_item.codeblock
            connection = chat_item.connection or {}

            if not codeblock:
                raise AIError(
                    message="Missing codeblock",
                    detail="The AI Chat item does not have a codeblock defined.",
                )

            # Merge with separate connection item if provided
            if request.connection_laui:
                conn_item, e = await self.catalog_service.safe_find_item(
                    item_laui=request.connection_laui
                )
                if not conn_item:
                    if isinstance(e, LAException):
                        e.message = "Connection " + e.message
                    raise e
                conn_content = (
                    conn_item.content if hasattr(conn_item, "content") and conn_item.content else {}
                )
                if isinstance(conn_content, str):
                    conn_content = json.loads(conn_content or "{}")
                connection = {**connection, **conn_content}

            if not connection:
                raise AIError(
                    message="Missing connection",
                    detail="The chat item does not have any connection",
                )

            api_key = connection.get("api_key", "")
            model = connection.get("model", "")
            if not api_key:
                raise NotFoundError(
                    message="API key missing",
                    detail="Could not find an API key in chat connection.",
                )
            if not model:
                raise NotFoundError(
                    message="Model missing", detail="No AI model was selected in chat connection."
                )

            # 2. Check session for cached temp_file_path or create new
            temp_file_path = None
            if request.session_id:
                session_item = await self.catalog_service.find_item(item_laui=request.session_id)
                if session_item:
                    temp_file_path = (
                        session_item.temp_file_path
                        if hasattr(session_item, "temp_file_path")
                        else None
                    )

            # Validate cached path still exists
            if temp_file_path and Path(temp_file_path).exists():
                module_path = Path(temp_file_path)
            else:
                created_files = create_module_from_codeblock(codeblock, self.ai_action_dir)
                module_path = created_files[0]
                temp_file_path = str(module_path)

            # 3. Load module and prepare invocation
            module = load_module(module_path)

            if not hasattr(module, "run"):
                raise AIError(
                    message="Missing run function",
                    detail="The chat codeblock is missing the required 'run()' function.",
                )

            # 4. Build system prompt and messages
            output_schema = self.schema_map.get(request.item_type)
            base_system_prompt = self.system_prompt_map.get(request.item_type)

            if not output_schema:
                raise NotFoundError(
                    message="Schema not found",
                    detail=f"There is no schema defined for the item type '{request.item_type}'.",
                )
            if not base_system_prompt:
                raise NotFoundError(
                    message="System prompt not found",
                    detail=f"There is no system prompt defined for the item type '{request.item_type}'.",
                )

            system_prompt = self._enhance_system_prompt(
                base_system_prompt, request.include_guide_doc, request.include_install_guide
            )

            if request.skill_content:
                system_prompt = request.skill_content + "\n\n" + system_prompt

            messages = [SystemMessage(content=system_prompt)]
            if request.messages:
                for msg in request.messages:
                    if msg.role == "user":
                        messages.append(HumanMessage(content=msg.content))
                    elif msg.role == "assistant":
                        messages.append(AIMessage(content=msg.content))
            if request.generated_content:
                messages.append(
                    AIMessage(
                        content=f"Previously generated content: {json.dumps(request.generated_content)}"
                    )
                )
            messages.append(HumanMessage(content=request.prompt))

            # 5. Call module.run() with connection, messages, output_schema
            response = module.run(connection, messages, output_schema)

            # 6. Process response (same logic as before)
            raw_response = response["raw"]
            validated_data = response["parsed"]
            stop_reason = raw_response.response_metadata.get("stop_reason")

            filtered_result, all_requested_completed = self._filter_completed_fields(
                validated_data,
                request.item_type,
                request.include_guide_doc,
                request.include_install_guide,
            )

            validation_result = self._validate_generated_codeblock(
                filtered_result, request.item_type
            )

            if stop_reason == "max_tokens" or stop_reason == "max_output_tokens":
                message = (
                    (
                        "User token limit reached - returning completed fields only. "
                        "Increase token_limit in connection configuration."
                    )
                    if filtered_result
                    else (
                        "User token limit reached - no fields completed. "
                        "Increase token_limit in connection configuration."
                    )
                )
                raise PartialGenerationError(
                    message=message,
                    detail={
                        "generated_content": filtered_result,
                        "token_limit_exceeded": True,
                        "partial_generation": True,
                        "temp_file_path": temp_file_path,
                    },
                )

            elif stop_reason == "model_context_window_exceeded":
                message = (
                    (
                        "Model context window exceeded - returning completed fields only. "
                        "Try shorter prompt for full generation."
                    )
                    if filtered_result
                    else (
                        "Model context window exceeded - no fields completed. "
                        "Try shorter prompt or reduce requested fields."
                    )
                )
                raise PartialGenerationError(
                    message=message,
                    detail={
                        "generated_content": filtered_result,
                        "token_limit_exceeded": True,
                        "partial_generation": True,
                        "temp_file_path": temp_file_path,
                    },
                )

            elif stop_reason == "end_turn" or stop_reason == "stop_sequence":
                return AIResponse(
                    message="Generation completed successfully",
                    generated_content=filtered_result,
                    token_limit_exceeded=False,
                    partial_generation=False,
                    temp_file_path=temp_file_path,
                    validation=validation_result,
                )

            else:
                partial = not all_requested_completed
                if partial:
                    message = "Partial generation - some requested fields incomplete"
                    raise PartialGenerationError(
                        message=message,
                        detail={
                            "generated_content": filtered_result,
                            "token_limit_exceeded": False,
                            "partial_generation": True,
                            "temp_file_path": temp_file_path,
                        },
                    )

                return AIResponse(
                    message="Generation completed successfully",
                    generated_content=filtered_result,
                    token_limit_exceeded=False,
                    partial_generation=False,
                    temp_file_path=temp_file_path,
                    validation=validation_result,
                )

        except ValidationError as ve:
            raise AIError(
                message="Validation failed",
                detail=f"Could not validate the AI response schema. Details: {str(ve)}",
            )
        except (APIError, APIStatusError) as api_error:
            error_message = str(api_error).lower()
            if "context" in error_message and (
                "limit" in error_message or "length" in error_message
            ):
                raise AIError(
                    "Input length and max_tokens exceed model's context window. "
                    "Reduce prompt length or decrease token_limit in connection configuration."
                )
            raise AIError(
                message="AI service provider error",
                detail=f"The AI platform returned an error: {str(api_error)}",
            )
        except LAException:
            raise
        except Exception as e:
            log_error("api", "ai_service", "generate", f"AI generation failed: {str(e)}")
            raise AIError(
                message="AI generation failed",
                detail=f"An unexpected error occurred during generation: {str(e)}",
            )

    async def agent(self, request: AgentRequest) -> AgentResponse:
        try:
            # 1. Fetch AI chat item -> extract codeblock and connection
            ai_chat_item, e = await self.catalog_service.safe_find_item(item_laui=request.chat_laui)
            if not ai_chat_item:
                if isinstance(e, LAException):
                    e.message = "AI Chat " + e.message
                raise e

            codeblock = ai_chat_item.codeblock
            connection = ai_chat_item.connection or {}

            if not codeblock:
                raise AIError(
                    message="Missing codeblock",
                    detail="The AI Chat item does not have a codeblock defined.",
                )

            # Merge with separate connection item if provided
            if request.connection_laui:
                conn_item, e = await self.catalog_service.safe_find_item(
                    item_laui=request.connection_laui
                )
                if not conn_item:
                    if isinstance(e, LAException):
                        e.message = "Connection " + e.message
                    raise e
                conn_content = (
                    conn_item.content if hasattr(conn_item, "content") and conn_item.content else {}
                )
                if isinstance(conn_content, str):
                    conn_content = json.loads(conn_content or "{}")
                connection = {**connection, **conn_content}

            if not connection:
                raise AIError(
                    message="Missing connection settings",
                    detail="The chat item does not have any connection settings defined.",
                )

            api_key = connection.get("api_key", "")
            model = connection.get("model", "")
            if not api_key:
                raise NotFoundError(
                    message="API key missing",
                    detail="Could not find an API key in your chat connection settings.",
                )
            if not model:
                raise NotFoundError(
                    message="Model missing",
                    detail="No AI model was selected in your chat connection settings.",
                )

            # 2. Load codeblock as module (same pattern as generate)
            created_files = create_module_from_codeblock(codeblock, self.ai_action_dir)
            module_path = created_files[0]
            module = load_module(module_path)

            if not hasattr(module, "run"):
                raise AIError(
                    message="Missing run function",
                    detail="The chat codeblock is missing the required 'run()' function.",
                )

            # 3. Build messages
            system_prompt = AGENT_SYSTEM_PROMPT
            if request.skill_content:
                system_prompt = request.skill_content + "\n\n" + system_prompt
            messages = [{"role": "system", "content": system_prompt}]
            if request.messages:
                for msg in request.messages:
                    messages.append({"role": msg.role, "content": msg.content})
            messages.append({"role": "user", "content": request.prompt})

            # 4. Run agent loop with MCP tools (or simple call without tools)
            if request.enable_tools and self.mcp_server:
                from src.core.mcp.agent import run_agent_loop

                allowed_tools = connection.get("allowed_tools") or None
                final_text, tools_called = await run_agent_loop(
                    module=module,
                    connection=connection,
                    messages=messages,
                    mcp_server=self.mcp_server,
                    allowed_tools=allowed_tools,
                )
                marker_type, cleaned_text = _parse_content_type_marker(final_text)
                return AgentResponse(
                    message=cleaned_text,
                    tool_calls_made=tools_called if tools_called else None,
                    content_type=marker_type or _detect_content_type(cleaned_text),
                )
            else:
                import asyncio

                response = module.run(connection, messages, output_schema=None)
                if asyncio.iscoroutine(response):
                    response = await response
                content = (
                    response.get("content", "") if isinstance(response, dict) else str(response)
                )
                content_type = response.get("content_type") if isinstance(response, dict) else None
                marker_type, cleaned_content = _parse_content_type_marker(content)
                return AgentResponse(
                    message=cleaned_content,
                    content_type=content_type
                    or marker_type
                    or _detect_content_type(cleaned_content),
                )

        except (AIError, NotFoundError):
            raise
        except (APIError, APIStatusError) as api_error:
            raise AIError(
                message="AI service provider error",
                detail=f"The AI platform returned an error: {str(api_error)}",
            )
        except Exception as e:
            log_error("api", "ai_service", "agent", f"AI chat failed: {str(e)}")
            raise AIError(
                message="AI agent failed",
                detail=f"An unexpected error occurred during your chat session: {str(e)}",
            )

    def _enhance_system_prompt(
        self, base_prompt: str, include_guide_doc: bool, include_install_guide: bool
    ) -> str:
        if not include_guide_doc and not include_install_guide:
            return base_prompt
        additional_instructions = "\n\nAlso generate:"
        if include_guide_doc:
            additional_instructions += " guide docs,"
        if include_install_guide:
            additional_instructions += " install_guide,"
        additional_instructions = additional_instructions.rstrip(",") + "."

        return base_prompt + additional_instructions

    def _filter_completed_fields(
        self,
        result: BaseModel,
        item_type: ItemType,
        include_guide_doc: bool,
        include_install_guide: bool,
    ) -> tuple[dict[str, Any], bool]:
        required_fields = self.required_fields_map.get(item_type, set())

        requested_fields = set(required_fields)
        if include_guide_doc:
            requested_fields.add("guide")
        if include_install_guide:
            requested_fields.add("install_guide")
        if hasattr(result, "connection") and result.connection is not None:
            requested_fields.add("connection")
        if hasattr(result, "action_variables") and result.action_variables is not None:
            requested_fields.add("action_variables")

        filtered_result = {}
        completed_count = 0

        for field_name in requested_fields:
            field_value = getattr(result, field_name, None)
            if field_value is None:
                filtered_result[field_name] = {}
                continue

            # Check if it's a GeneratedContent with completed flag
            if isinstance(field_value, BaseModel) and hasattr(field_value, "completed"):
                if field_value.completed:
                    # For 'payload' field, extract the "data" value
                    if field_name == "payload":
                        data_value = getattr(field_value, "data", None)
                        filtered_result[field_name] = data_value if data_value is not None else {}
                    else:
                        # For other fields, extract all fields except 'completed'
                        content_dict = field_value.model_dump(exclude={"completed"})
                        filtered_result[field_name] = content_dict if content_dict else {}
                    completed_count += 1
                else:
                    filtered_result[field_name] = {}
            else:
                # No "completed" marker, assume complete
                filtered_result[field_name] = field_value
                completed_count += 1

        all_requested_completed = completed_count == len(requested_fields)
        return filtered_result, all_requested_completed

    def _validate_generated_codeblock(self, filtered_result: dict[str, Any], item_type: ItemType):
        """Run static validator on the AI-generated codeblock (if any).

        Returns a ValidationResult or None. Never raises — errors/warnings
        are surfaced to the frontend so the user can paste them back into chat.
        """
        base = (item_type.value if hasattr(item_type, "value") else str(item_type)).split(".")[0]
        if base not in ("operator", "action"):
            return None
        codeblock = filtered_result.get("codeblock")
        if not codeblock or not isinstance(codeblock, dict):
            return None
        try:
            return self.codeblock_validator.validate(
                codeblock, str(item_type.value if hasattr(item_type, "value") else item_type)
            )
        except Exception as e:
            log_error(
                "api", "ai_service", "_validate_generated_codeblock", f"Validator failed: {e}"
            )
            return None


def get_ai_service(request: Request) -> AIService:
    return request.app.state.ai_service
