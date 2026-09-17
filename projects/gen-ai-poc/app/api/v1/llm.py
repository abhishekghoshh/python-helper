"""
LLM API endpoints — demonstrate how applications call LLMs.

Endpoints:
- POST /llm/generate     — Generate a chat completion (non-streaming)
- POST /llm/generate-stream — Generate with streaming (token-by-token)

These endpoints show the full chat message lifecycle:
system → user → assistant, with controllable parameters.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.llm.service import llm_service
from app.models.schemas import LLMRequest, LLMResponse, LLMStreamChunk

router = APIRouter(prefix="/llm", tags=["LLM"])
logger = logging.getLogger(__name__)


@router.post("/generate", response_model=LLMResponse)
async def generate_llm_response(request: LLMRequest) -> LLMResponse:
    """Generate a chat completion response from the LLM.

    Demonstrates:
    - Passing system, user, and assistant messages
    - Controlling temperature, top_p, max_tokens
    - Using a specific model
    """
    logger.info(
        "LLM generate endpoint — model=%s, messages=%d",
        request.model or settings.llm_model,
        len(request.messages),
    )
    try:
        response = await llm_service.generate(request)
        return response
    except Exception as e:
        logger.error("LLM generation failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post("/generate-stream")
async def generate_llm_stream(request: LLMRequest) -> StreamingResponse:
    """Stream LLM tokens as they are generated.

    Returns a Server-Sent Events (SSE) stream where each chunk
    contains one or more tokens from the model.
    """
    if not request.stream:
        request.stream = True

    async def event_stream() -> AsyncIterator[str]:
        async for token in await llm_service.generate_stream(request):
            yield f"data: {LLMStreamChunk(content=token).model_dump_json()}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/models")
async def list_models() -> dict[str, Any]:
    """List available models (placeholder — returns configured defaults)."""
    return {
        "llm_model": settings.llm_model,
        "embedding_model": settings.embedding_model,
        "embedding_dimensions": settings.embedding_dimensions,
    }
