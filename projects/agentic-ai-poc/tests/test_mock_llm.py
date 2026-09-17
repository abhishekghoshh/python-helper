"""Tests for the Mock LLM service's decision-making logic."""

import json
import pytest

from app.llm.mock import MockLLMService
from app.models.schemas import (
    ConversationMessage,
    Role,
    ToolCall,
    ToolCallFunction,
    ToolDefinition,
    FunctionDef,
)


def _tool_def(name: str, description: str, params: dict | None = None) -> ToolDefinition:
    return ToolDefinition(
        type="function",
        function=FunctionDef(name=name, description=description, parameters=params or {"type": "object", "properties": {}, "required": []}),
    )


@pytest.fixture
def tools():
    return [
        _tool_def("calculator", "Calculate math expressions", {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}),
        _tool_def("datetime_now", "Get current date and time", {"type": "object", "properties": {}, "required": []}),
        _tool_def("web_search", "Search the web", {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}),
        _tool_def("rag_query", "Query knowledge base", {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]}),
        _tool_def("file_reader", "Read a file", {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}),
    ]


@pytest.mark.asyncio
class TestMockLLM:
    async def test_math_query_calls_calculator(self, tools):
        mock = MockLLMService()
        messages = [ConversationMessage(role=Role.USER, content="What is 2 + 2?")]
        resp = await mock.generate(messages, tools)
        assert resp.has_tool_calls
        assert resp.tool_calls[0].function.name == "calculator"
        import json
        args = json.loads(resp.tool_calls[0].function.arguments)
        assert "2 + 2" in args["expression"]

    async def test_time_query_calls_datetime(self, tools):
        mock = MockLLMService()
        messages = [ConversationMessage(role=Role.USER, content="What time is it now?")]
        resp = await mock.generate(messages, tools)
        assert resp.has_tool_calls
        assert resp.tool_calls[0].function.name == "datetime_now"

    async def test_search_query_calls_web_search(self, tools):
        mock = MockLLMService()
        messages = [ConversationMessage(role=Role.USER, content="What is the capital of France?")]
        resp = await mock.generate(messages, tools)
        assert resp.has_tool_calls
        # "What is the capital of France?" is a factual question.
        # If rag_query is available → rag_query; else → web_search
        assert resp.tool_calls[0].function.name in ("rag_query", "web_search")

    async def test_knowledge_query_calls_rag_or_search(self, tools):
        mock = MockLLMService()
        messages = [ConversationMessage(role=Role.USER, content="Tell me about Python programming")]
        resp = await mock.generate(messages, tools)
        assert resp.has_tool_calls
        assert resp.tool_calls[0].function.name in ("rag_query", "web_search")

    async def test_synthesizes_answer_after_tool_result(self, tools):
        mock = MockLLMService()
        messages = [
            ConversationMessage(role=Role.USER, content="What is 2 + 2?"),
            ConversationMessage(role=Role.ASSISTANT, content=None, tool_calls=[
                ToolCall(id="call_1", function=ToolCallFunction(name="calculator", arguments='{"expression": "2 + 2"}'))
            ]),
            ConversationMessage(role=Role.TOOL, content="4", tool_call_id="call_1", tool_name="calculator"),
        ]
        resp = await mock.generate(messages, tools)
        assert not resp.has_tool_calls
        assert resp.content is not None
        assert "4" in resp.content

    async def test_no_tools_returns_default_answer(self):
        mock = MockLLMService()
        messages = [ConversationMessage(role=Role.USER, content="Hello there")]
        resp = await mock.generate(messages, tools=None)
        assert not resp.has_tool_calls
        assert resp.content is not None

    async def test_force_tool(self, tools):
        mock = MockLLMService(force_tool="datetime_now")
        messages = [ConversationMessage(role=Role.USER, content="What is 2 + 2?")]
        resp = await mock.generate(messages, tools)
        assert resp.has_tool_calls
        assert resp.tool_calls[0].function.name == "datetime_now"

    async def test_force_response(self, tools):
        mock = MockLLMService(force_response="Forced answer here.")
        messages = [
            ConversationMessage(role=Role.USER, content="test"),
            ConversationMessage(role=Role.TOOL, content="result", tool_call_id="1", tool_name="x"),
        ]
        resp = await mock.generate(messages, tools)
        assert resp.content == "Forced answer here."

    async def test_streaming_yields_content(self, tools):
        mock = MockLLMService()
        messages = [ConversationMessage(role=Role.USER, content="Hello")]
        chunks = []
        async for chunk in mock.generate_stream(messages, tools):
            chunks.append(chunk)
        assert len(chunks) > 0
