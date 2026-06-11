# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from enum import StrEnum
from typing import Any

from pydantic import BaseModel
from pydantic_mongo import PydanticObjectId

from src.core.ai.prompts import (
    ACTION_SYSTEM_PROMPT,
    AGENT_SYSTEM_PROMPT,
    GENERATE_SYSTEM_PROMPT,
    OPERATOR_SYSTEM_PROMPT,
    PAYLOAD_SYSTEM_PROMPT,
)
from src.core.validation.schema import ValidationResult


class AIProvider(StrEnum):
    """Supported AI service providers."""

    ANTHROPIC = "anthropic"


class ItemType(StrEnum):
    """Supported content categories for AI generation."""

    ACTION = "action"
    GENERATE = "generate"
    AGENT = "agent"
    PAYLOAD = "payload"
    OPERATOR = "operator"


class ChatMessage(BaseModel):
    """A single message in conversation history."""

    role: str
    content: str


class GenerateRequest(BaseModel):
    """Request model for AI generation endpoint."""

    prompt: str
    chat_laui: PydanticObjectId
    item_type: ItemType
    ai_provider: str
    include_guide_doc: bool = False
    include_install_guide: bool = False
    messages: list[ChatMessage] | None = None
    generated_content: dict[str, Any] | None = None
    skill_content: str | None = None
    session_id: PydanticObjectId | None = None
    connection_laui: PydanticObjectId | None = None


class AIResponse(BaseModel):
    """Response model for AI generation endpoint."""

    message: str
    generated_content: dict[str, Any]
    token_limit_exceeded: bool = False
    partial_generation: bool = False
    temp_file_path: str | None = None
    validation: ValidationResult | None = None


class AgentRequest(BaseModel):
    """Request model for AI agent endpoint."""

    prompt: str
    chat_laui: PydanticObjectId
    messages: list[ChatMessage] | None = None
    connection_laui: PydanticObjectId | None = None
    enable_tools: bool = True
    skill_content: str | None = None


class AgentResponse(BaseModel):
    """Response model for AI agent endpoint."""

    message: str
    tool_calls_made: list[str] | None = None
    content_type: str | None = "text"


class GeneratedContent(BaseModel):
    completed: bool  # REQUIRED: Must be true if generation was successful

    class Config:
        extra = "allow"


class ActionPromptSchema(BaseModel):
    """Schema for AI-generated action content."""

    codeblock: GeneratedContent | None = None
    bashblock: GeneratedContent | None = None
    connection: GeneratedContent | None = None
    action_variables: GeneratedContent | None = None
    guide: GeneratedContent | None = None
    install_guide: GeneratedContent | None = None


class OperatorPromptSchema(BaseModel):
    """Schema for AI-generated operator content."""

    codeblock: GeneratedContent | None = None
    bashblock: GeneratedContent | None = None
    payload: GeneratedContent | None = None
    connection: GeneratedContent
    guide: GeneratedContent | None = None
    install_guide: GeneratedContent | None = None


class PayloadPromptSchema(BaseModel):
    """Schema for AI-generated payload content."""

    payload: GeneratedContent | None = None


# Schema mapping based on item type
SCHEMA_MAP: dict[ItemType, type[BaseModel]] = {
    ItemType.OPERATOR: OperatorPromptSchema,
    ItemType.ACTION: ActionPromptSchema,
    ItemType.GENERATE: ActionPromptSchema,
    ItemType.AGENT: ActionPromptSchema,
    ItemType.PAYLOAD: PayloadPromptSchema,
}

REQUIRED_FIELDS_MAP: dict[ItemType, set[str]] = {
    ItemType.ACTION: {
        "codeblock",
        "bashblock",
    },
    ItemType.GENERATE: {
        "codeblock",
        "bashblock",
    },
    ItemType.AGENT: {
        "codeblock",
        "bashblock",
    },
    ItemType.OPERATOR: {
        "codeblock",
        "bashblock",
        "payload",
        "connection",
    },
    ItemType.PAYLOAD: {
        "payload",
    },
}


def get_system_prompt_map() -> dict[ItemType, str]:
    return {
        ItemType.OPERATOR: OPERATOR_SYSTEM_PROMPT,
        ItemType.ACTION: ACTION_SYSTEM_PROMPT,
        ItemType.GENERATE: GENERATE_SYSTEM_PROMPT,
        ItemType.AGENT: AGENT_SYSTEM_PROMPT,
        ItemType.PAYLOAD: PAYLOAD_SYSTEM_PROMPT,
    }
