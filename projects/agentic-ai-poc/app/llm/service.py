"""
LLM service layer — the interface between the agent and language models.

This module defines:

- ``LLMInterface`` — the abstract contract every LLM backend must implement.
  The agent depends on this interface, **not** on any specific provider.
- ``OpenAILLMService`` — a real implementation using the OpenAI SDK with
  native tool-calling support.

The contract is intentionally small:

    generate(messages, tools) -> LLMResponse

Where ``LLMResponse`` may contain text, tool calls, or both. This keeps the
agent loop provider-agnostic — swap OpenAI for a local model, a mock, or
another vendor without touching agent code.

### Why an interface?

In a real agentic system the LLM is just **one component** among many
(tools, memory, planning, guardrails). Decoupling the LLM behind an
interface lets us:

1. **Test** the agent loop deterministically with a mock LLM.
2. **Switch providers** (OpenAI → Anthropic → local) without refactoring.
3. **Observe** every LLM call through a single choke point.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from app.models.schemas import ConversationMessage, LLMResponse, ToolDefinition
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMInterface(ABC):
    """Abstract interface for LLM backends.

    The agent depends on this interface, not on any concrete provider.
    Concrete implementations (OpenAI, Mock, etc.) return ``LLMResponse``
    objects that may contain text, tool calls, or both.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """The model identifier (e.g. 'gpt-4o-mini')."""
        ...

    @abstractmethod
    async def generate(
        self,
        messages: list[ConversationMessage],
        tools: Optional[list[ToolDefinition]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate a completion from the LLM.

        Args:
            messages: The conversation history (system, user, assistant, tool).
            tools: Tool definitions the LLM may choose to call.
            temperature: Sampling temperature override.
            max_tokens: Max output tokens override.

        Returns:
            An ``LLMResponse`` with ``content`` and/or ``tool_calls``.
        """
        ...

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[ConversationMessage],
        tools: Optional[list[ToolDefinition]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """Generate a streaming completion, yielding text chunks."""
        ...


class OpenAILLMService(LLMInterface):
    """LLM service backed by the OpenAI SDK (or any OpenAI-compatible API).

    Supports native tool calling: when ``tools`` are provided, the LLM can
    respond with ``tool_calls`` instead of (or in addition to) text.

    The OpenAI SDK expects messages in a specific dict format and tool
    definitions in the OpenAI tools format. ``_to_openai_messages`` and
    ``_to_openai_tools`` handle the conversion.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 model: Optional[str] = None) -> None:
        from openai import AsyncOpenAI

        self._api_key = api_key or settings.llm_api_key
        self._base_url = base_url or settings.llm_base_url
        self._model = model or settings.llm_model
        self._client: Optional[AsyncOpenAI] = None

    @property
    def client(self) -> Any:
        """Lazily initialise the OpenAI client."""
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                api_key=self._api_key or "dummy-key",
                base_url=self._base_url,
                timeout=settings.llm_timeout,
            )
        return self._client

    @property
    def model_name(self) -> str:
        return self._model

    @staticmethod
    def _to_openai_messages(messages: list[ConversationMessage]) -> list[dict[str, Any]]:
        """Convert internal ConversationMessage objects to OpenAI dict format."""
        result: list[dict[str, Any]] = []
        for msg in messages:
            if msg.role.value == "system":
                result.append({"role": "system", "content": msg.content})
            elif msg.role.value == "user":
                result.append({"role": "user", "content": msg.content})
            elif msg.role.value == "assistant":
                entry: dict[str, Any] = {"role": "assistant", "content": msg.content}
                if msg.tool_calls:
                    entry["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ]
                result.append(entry)
            elif msg.role.value == "tool":
                result.append({
                    "role": "tool",
                    "content": msg.content,
                    "tool_call_id": msg.tool_call_id,
                    "name": msg.tool_name,
                })
        return result

    @staticmethod
    def _to_openai_tools(tools: list[ToolDefinition]) -> list[dict[str, Any]]:
        return [t.to_openai() for t in tools]

    async def generate(
        self,
        messages: list[ConversationMessage],
        tools: Optional[list[ToolDefinition]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate a non-streaming chat completion with optional tool calling."""
        params: dict[str, Any] = {
            "model": self._model,
            "messages": self._to_openai_messages(messages),
            "temperature": temperature if temperature is not None else settings.llm_temperature,
            "max_tokens": max_tokens if max_tokens is not None else settings.llm_max_tokens,
            "top_p": settings.llm_top_p,
        }
        if tools:
            params["tools"] = self._to_openai_tools(tools)
            params["tool_choice"] = "auto"

        response = await self.client.chat.completions.create(**params)
        choice = response.choices[0]

        tool_calls = None
        if choice.message.tool_calls:
            from app.models.schemas import ToolCall, ToolCallFunction

            tool_calls = [
                ToolCall(
                    id=tc.id or f"call_{i}",
                    type=tc.type or "function",
                    function=ToolCallFunction(
                        name=tc.function.name,
                        arguments=tc.function.arguments,
                    ),
                )
                for i, tc in enumerate(choice.message.tool_calls)
            ]

        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return LLMResponse(
            id=response.id,
            model=response.model,
            content=choice.message.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
            usage=usage,
        )

    async def generate_stream(
        self,
        messages: list[ConversationMessage],
        tools: Optional[list[ToolDefinition]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """Stream LLM tokens as they are generated (Server-Sent Events at the API layer)."""
        params: dict[str, Any] = {
            "model": self._model,
            "messages": self._to_openai_messages(messages),
            "temperature": temperature if temperature is not None else settings.llm_temperature,
            "max_tokens": max_tokens if max_tokens is not None else settings.llm_max_tokens,
            "top_p": settings.llm_top_p,
            "stream": True,
        }
        if tools:
            params["tools"] = self._to_openai_tools(tools)
            params["tool_choice"] = "auto"

        stream = await self.client.chat.completions.create(**params)
        async for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
