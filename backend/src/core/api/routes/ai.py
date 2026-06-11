# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import traceback

from fastapi import APIRouter, Depends, HTTPException, Response

from src.common.context_vars.user_context import get_user_laui
from src.common.exceptions import LAException, PartialGenerationError
from src.common.logger.logger import log_error, log_info
from src.core.ai.schema import AgentRequest, AIResponse, GenerateRequest
from src.core.ai.service import get_ai_service

ai_router = APIRouter()


@ai_router.post("/generate")
async def generate(
    request: GenerateRequest, response: Response, ai_service=Depends(get_ai_service)
):
    """
    Generate output using Anthropic models based on connection config.
    """
    try:
        log_info(
            "api", "ai_router", "generate", f"user={get_user_laui()} payload={request.model_dump()}"
        )
        ai_result = await ai_service.generate(request)
        return ai_result.model_dump() if hasattr(ai_result, "model_dump") else ai_result

    except PartialGenerationError as e:
        response.status_code = 206
        ai_result = AIResponse(
            message=e.message,
            generated_content=e.detail.get("generated_content", {}),
            token_limit_exceeded=e.detail.get("token_limit_exceeded", False),
            partial_generation=e.detail.get("partial_generation", True),
            temp_file_path=e.detail.get("temp_file_path"),
        )
        return ai_result.model_dump()
    except LAException as e:
        log_error(
            "api_traceback",
            "ai_router",
            "generate",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "ai_router",
            "generate",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )


@ai_router.post("/agent")
async def agent(request: AgentRequest, ai_service=Depends(get_ai_service)):
    """
    Simple conversational agent using AI provider — no structured output.
    """
    try:
        log_info(
            "api", "ai_router", "chat", f"user={get_user_laui()} payload={request.model_dump()}"
        )
        result = await ai_service.agent(request)
        return result.model_dump()
    except LAException as e:
        log_error(
            "api_traceback",
            "ai_router",
            "chat",
            f"LAException: {e.detail if e.detail else e.message}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=e.http_status_code, detail={"message": e.message, "detail": e.detail}
        )
    except Exception as e:
        log_error(
            "api_traceback",
            "ai_router",
            "chat",
            f"Unexpected error: {str(e)}\n{traceback.format_exc()}",
        )
        raise HTTPException(
            status_code=500, detail={"message": "Internal server error", "detail": f"{str(e)}"}
        )
