"""
LLM service — wraps the OpenAI SDK to call chat-completion APIs.

This layer demonstrates:
- Chat messages with system / user / assistant roles
- Model parameter control (temperature, top_p, max_tokens)
- Streaming token-by-token responses
- Token usage reporting

A built-in **mock mode** allows the full pipeline (including RAG query
and LLM generate) to run without any API key. When ``mock_llm_mode``
is ``auto`` and no ``LLM_API_KEY`` is set, the service returns simulated
responses so learners can experiment locally for free.

The service is intentionally thin: it maps the app's internal schemas
to the OpenAI client and back, so learners can see the raw request/response
flow without hidden abstractions.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import AsyncIterator
from uuid import uuid4

from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from app.core.config import settings
from app.models.schemas import ChatMessage, LLMRequest, LLMResponse, MessageRole

logger = logging.getLogger(__name__)


def _is_mock_mode() -> bool:
    """Return True if the LLM service should use the built-in mock backend."""
    if settings.mock_llm_mode == "always":
        return True
    if settings.mock_llm_mode == "never":
        return False
    # "auto" — use mock only when no API key is configured
    return not settings.llm_api_key


def _to_openai_messages(messages: list[ChatMessage]) -> list[ChatCompletionMessageParam]:
    """Convert internal ChatMessage objects to OpenAI API message parameters."""
    converted: list[ChatCompletionMessageParam] = []
    for msg in messages:
        if msg.role == MessageRole.SYSTEM:
            converted.append(ChatCompletionSystemMessageParam(role="system", content=msg.content))
        elif msg.role == MessageRole.USER:
            converted.append(ChatCompletionUserMessageParam(role="user", content=msg.content))
        else:
            converted.append({"role": "assistant", "content": msg.content})
    return converted


def _build_mock_response(messages: list[ChatCompletionMessageParam]) -> str:
    """Generate a mock LLM response from the conversation messages.

    For RAG prompts (containing ``Context:`` and ``Question:``), the mock
    extracts the question and returns a response that references the
    provided context — simulating a grounded answer.

    For plain chat prompts, it echoes the last user message with a
    disclaimer that this is a simulated response.
    """
    # Find the last user message
    user_contents = [
        m.get("content", "")
        for m in messages
        if m.get("role") == "user" and isinstance(m.get("content"), str)
    ]
    if not user_contents:
        return "Hello! I'm a mock LLM. Ask me anything to see how the pipeline works."

    full_content = user_contents[-1]

    # Detect RAG-style prompt: "Context:\n...\n\nQuestion: ..."
    context_match = re.search(r"Context:\s*\n(.+?)(?:\n\nQuestion:|$)", full_content, re.DOTALL)
    question_match = re.search(r"Question:\s*(.+)", full_content)
    question = question_match.group(1).strip() if question_match else full_content.strip()

    if context_match:
        context = context_match.group(1).strip()
        # Extract source snippets to make the response look grounded
        lines = context.strip().split("\n")
        if lines:
            return (
                f"Based on the provided context, here is my answer:\n\n"
                f"{question}\n\n"
                f"The relevant information from the documents states:\n\n"
                + "\n".join(f"- {line}" for line in lines[:5])
            )

    # Non-RAG mock response
    return (
        f"[Mock LLM — no API key configured]\n\n"
        f'You asked: "{question[:200]}"\n\n'
        f"This is a simulated response to demonstrate the API flow. "
        f"To use a real LLM, set your `LLM_API_KEY` in `.env` or connect to "
        f"Ollama/LM Studio via `LLM_BASE_URL`."
    )


class LLMService:
    """Service for interacting with an LLM via the OpenAI-compatible API."""

    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None

    @property
    def is_mock(self) -> bool:
        """True if the service is running in mock mode (no real API calls)."""
        return _is_mock_mode()

    @property
    def client(self) -> AsyncOpenAI:
        """Lazily initialise the OpenAI client."""
        if self._client is None:
            if _is_mock_mode():
                logger.info(
                    "LLM service running in mock mode — no real API calls will be made. "
                    "Set LLM_API_KEY in .env or connect to a local LLM (Ollama/LM Studio) "
                    "to use real models.",
                )
                # Create a dummy client — it won't be used in mock mode
                self._client = AsyncOpenAI(
                    api_key="mock",
                    base_url=settings.llm_base_url,
                    timeout=settings.llm_timeout,
                )
            else:
                self._client = AsyncOpenAI(
                    api_key=settings.llm_api_key,
                    base_url=settings.llm_base_url,
                    timeout=settings.llm_timeout,
                )
            logger.info(
                "LLM client initialised — provider=%s, base_url=%s, model=%s, mock=%s",
                settings.llm_provider,
                settings.llm_base_url,
                settings.llm_model,
                _is_mock_mode(),
            )
        return self._client

    def _resolve_params(self, request: LLMRequest) -> dict:
        """Resolve model parameters, falling back to settings defaults."""
        return {
            "model": request.model or settings.llm_model,
            "messages": _to_openai_messages(request.messages),
            "temperature": request.temperature
            if request.temperature is not None
            else settings.llm_temperature,
            "max_tokens": request.max_tokens
            if request.max_tokens is not None
            else settings.llm_max_tokens,
            "top_p": request.top_p if request.top_p is not None else settings.llm_top_p,
        }

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a non-streaming chat completion."""
        params = self._resolve_params(request)
        model = params["model"]
        num_messages = len(params["messages"])
        logger.info(
            "LLM generate — model=%s, messages=%d, temperature=%.2f, top_p=%.2f, max_tokens=%d",
            model,
            num_messages,
            params["temperature"],
            params["top_p"],
            params["max_tokens"],
        )

        if _is_mock_mode():
            content = _build_mock_response(params["messages"])
            # Estimate token counts
            prompt_tokens = sum(len(m.get("content", "").split()) for m in params["messages"])
            completion_tokens = len(content.split())
            response = LLMResponse(
                id=f"mock-{uuid4()}",
                model=model,
                content=content,
                usage={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                },
                finish_reason="stop",
            )
            logger.info(
                "LLM generate (mock) complete — id=%s, tokens=%d",
                response.id,
                prompt_tokens + completion_tokens,
            )
            return response

        try:
            response = await self.client.chat.completions.create(stream=False, **params)
        except Exception as exc:
            logger.error("LLM generate failed — model=%s, error=%s", model, exc)
            raise

        choice = response.choices[0]
        usage = response.usage.model_dump(mode="python") if response.usage else None
        tokens_used = usage.get("total_tokens", "?") if usage else "?"
        logger.info(
            "LLM generate complete — id=%s, model=%s, finish=%s, tokens=%s",
            response.id,
            response.model,
            choice.finish_reason,
            tokens_used,
        )

        return LLMResponse(
            id=response.id,
            model=response.model,
            content=choice.message.content or "",
            usage=usage,
            finish_reason=choice.finish_reason,
        )

    async def generate_stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """Generate a streaming chat completion, yielding tokens one at a time."""
        params = self._resolve_params(request)
        model = params["model"]
        logger.info(
            "LLM stream — model=%s, messages=%d, temperature=%.2f",
            model,
            len(params["messages"]),
            params["temperature"],
        )

        if _is_mock_mode():
            content = _build_mock_response(params["messages"])
            # Simulate streaming by yielding the response word by word
            words = content.split()
            token_count = 0
            for i, word in enumerate(words):
                if i > 0:
                    yield " "
                yield word
                token_count += len(word)
                time.sleep(0.01)  # tiny delay to simulate streaming
            logger.info(
                "LLM stream (mock) complete — model=%s, tokens_yielded=%d",
                model,
                token_count,
            )
            return

        try:
            stream = await self.client.chat.completions.create(stream=True, **params)
        except Exception as exc:
            logger.error("LLM stream failed — model=%s, error=%s", model, exc)
            raise
        token_count = 0
        async for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta
                if delta.content:
                    token_count += 1
                    yield delta.content
        logger.info("LLM stream complete — model=%s, tokens_yielded=%d", model, token_count)

    async def generate_response(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
    ) -> LLMResponse | AsyncIterator[str]:
        """Convenience method used internally by the RAG pipeline.

        Accepts individual parameters instead of an LLMRequest, and optionally
        returns a streaming iterator.
        """
        request = LLMRequest(
            messages=messages,
            model=model,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stream=stream,
        )
        if stream:
            return self.generate_stream(request)
        return await self.generate(request)


# Module-level singleton so the API can import a ready instance.
llm_service = LLMService()
