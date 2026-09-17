"""Tests for the LLM service."""

import pytest

from app.llm.service import LLMService, _build_mock_response, _is_mock_mode, _to_openai_messages
from app.models.schemas import ChatMessage, LLMRequest, MessageRole


class TestToOpenAiMessages:
    def test_converts_system_message(self):
        msgs = [ChatMessage(role=MessageRole.SYSTEM, content="You are helpful.")]
        result = _to_openai_messages(msgs)
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "You are helpful."

    def test_converts_user_message(self):
        msgs = [ChatMessage(role=MessageRole.USER, content="Hello")]
        result = _to_openai_messages(msgs)
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hello"

    def test_converts_assistant_message(self):
        msgs = [ChatMessage(role=MessageRole.ASSISTANT, content="Hi there")]
        result = _to_openai_messages(msgs)
        assert result[0]["role"] == "assistant"
        assert result[0]["content"] == "Hi there"

    def test_preserves_order(self):
        msgs = [
            ChatMessage(role=MessageRole.SYSTEM, content="System prompt"),
            ChatMessage(role=MessageRole.USER, content="First"),
            ChatMessage(role=MessageRole.ASSISTANT, content="Response"),
            ChatMessage(role=MessageRole.USER, content="Follow-up"),
        ]
        result = _to_openai_messages(msgs)
        assert len(result) == 4
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"
        assert result[2]["role"] == "assistant"
        assert result[3]["role"] == "user"

    def test_empty_list(self):
        result = _to_openai_messages([])
        assert result == []


class TestLLMService:
    def test_service_initializes(self):
        service = LLMService()
        assert service is not None

    def test_resolve_params_uses_defaults(self):
        from app.core.config import settings

        request = LLMRequest(messages=[ChatMessage(role=MessageRole.USER, content="Hi")])
        params = LLMService()._resolve_params(request)
        assert params["temperature"] == settings.llm_temperature
        assert params["max_tokens"] == settings.llm_max_tokens
        assert params["model"] == settings.llm_model

    def test_resolve_params_overrides(self):
        request = LLMRequest(
            messages=[ChatMessage(role=MessageRole.USER, content="Hi")],
            temperature=0.1,
            max_tokens=100,
            model="gpt-4",
        )
        params = LLMService()._resolve_params(request)
        assert params["temperature"] == 0.1
        assert params["max_tokens"] == 100
        assert params["model"] == "gpt-4"


class TestMockMode:
    """Tests for the built-in mock LLM that works without an API key."""

    def test_is_mock_mode_auto_no_key(self):
        """In auto mode with no API key, mock mode is active."""
        from app.core.config import settings

        original = settings.mock_llm_mode, settings.llm_api_key
        settings.mock_llm_mode = "auto"
        settings.llm_api_key = ""
        try:
            assert _is_mock_mode() is True
        finally:
            settings.mock_llm_mode, settings.llm_api_key = original

    def test_is_mock_mode_auto_with_key(self):
        """In auto mode with an API key, mock mode is inactive."""
        from app.core.config import settings

        original = settings.mock_llm_mode, settings.llm_api_key
        settings.mock_llm_mode = "auto"
        settings.llm_api_key = "sk-test-key"
        try:
            assert _is_mock_mode() is False
        finally:
            settings.mock_llm_mode, settings.llm_api_key = original

    def test_is_mock_mode_always(self):
        from app.core.config import settings

        original = settings.mock_llm_mode
        settings.mock_llm_mode = "always"
        try:
            assert _is_mock_mode() is True
        finally:
            settings.mock_llm_mode = original

    def test_is_mock_mode_never(self):
        from app.core.config import settings

        original = settings.mock_llm_mode, settings.llm_api_key
        settings.mock_llm_mode = "never"
        settings.llm_api_key = ""
        try:
            assert _is_mock_mode() is False
        finally:
            settings.mock_llm_mode, settings.llm_api_key = original


class TestMockResponse:
    """Tests for the mock response builder."""

    def test_mock_response_plain_chat(self):
        messages = [{"role": "user", "content": "Hello"}]
        response = _build_mock_response(messages)
        assert "[Mock LLM" in response
        assert "Hello" in response

    def test_mock_response_no_user_messages(self):
        messages = [{"role": "system", "content": "You are helpful"}]
        response = _build_mock_response(messages)
        assert "mock llm" in response.lower()

    def test_mock_response_rag_prompt(self):
        """Mock should extract context and question from RAG-style prompts."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": (
                    "Context:\n"
                    "RAG combines retrieval and generation.\n"
                    "It is useful for grounding responses.\n\n"
                    "Question: What is RAG?"
                ),
            },
        ]
        response = _build_mock_response(messages)
        assert "Based on the provided context" in response
        assert "RAG" in response


class TestMockGenerate:
    """Tests for the full mock generate flow."""

    @pytest.mark.asyncio
    async def test_generate_mock_returns_response(self):
        request = LLMRequest(
            messages=[ChatMessage(role=MessageRole.USER, content="What is AI?")],
        )
        service = LLMService()
        response = await service.generate(request)
        assert response.content
        assert "[Mock LLM" in response.content
        assert response.id.startswith("mock-")
        assert response.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_generate_mock_with_rag_context(self):
        request = LLMRequest(
            messages=[
                ChatMessage(role="system", content="You are helpful."),
                ChatMessage(
                    role="user",
                    content=("Context:\nAI is awesome.\n\n" "Question: What is AI?"),
                ),
            ],
        )
        service = LLMService()
        response = await service.generate(request)
        assert "Based on the provided context" in response.content

    @pytest.mark.asyncio
    async def test_generate_stream_mock(self):
        request = LLMRequest(
            messages=[ChatMessage(role=MessageRole.USER, content="Tell me a joke")],
        )
        service = LLMService()
        tokens = []
        async for token in service.generate_stream(request):
            tokens.append(token)
        content = "".join(tokens)
        assert len(tokens) > 0
        assert "Mock LLM" in content or "joke" in content.lower() or "mock" in content.lower()

    @pytest.mark.asyncio
    async def test_is_mock_property(self):
        from app.core.config import settings

        original = settings.mock_llm_mode, settings.llm_api_key
        settings.mock_llm_mode = "auto"
        settings.llm_api_key = ""
        try:
            service = LLMService()
            assert service.is_mock is True
        finally:
            settings.mock_llm_mode, settings.llm_api_key = original
