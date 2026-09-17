"""
Shared test fixtures.

Provides pre-configured instances of the mock LLM, tool registry, and
agent that tests can reuse. All fixtures avoid external dependencies
(no API keys, no Qdrant, no model downloads).
"""

from __future__ import annotations

import pytest

from app.agents.react_agent import ReActAgent
from app.llm.mock import MockLLMService
from app.memory.short_term import ConversationBuffer
from app.memory.working import InMemoryWorkingMemory
from app.models.schemas import AgentConfig
from app.tools.base import ToolRegistry
from app.tools.calculator import CalculatorTool
from app.tools.datetime_tool import DateTimeTool
from app.tools.file_reader import FileReaderTool
from app.tools.web_search import WebSearchTool
from app.observability.trace import ExecutionTrace


@pytest.fixture
def mock_llm() -> MockLLMService:
    return MockLLMService()


@pytest.fixture
def tool_registry() -> ToolRegistry:
    """A registry with all non-RAG tools (no heavy deps needed)."""
    reg = ToolRegistry()
    reg.register(CalculatorTool())
    reg.register(DateTimeTool())
    reg.register(FileReaderTool())
    reg.register(WebSearchTool())
    return reg


@pytest.fixture
def agent(mock_llm, tool_registry) -> ReActAgent:
    """A fully wired ReAct agent using the mock LLM."""
    config = AgentConfig(max_iterations=5, trace_enabled=True)
    memory = ConversationBuffer(max_chars=10000)
    working = InMemoryWorkingMemory()
    trace = ExecutionTrace()
    return ReActAgent(
        llm=mock_llm,
        tools=tool_registry,
        config=config,
        memory=memory,
        working_memory=working,
        trace=trace,
    )


@pytest.fixture
def data_dir(tmp_path):
    """A temporary data directory for the file_reader tool."""
    d = tmp_path / "data"
    d.mkdir()
    (d / "sample.txt").write_text("Hello from the data directory!")
    return str(d)
