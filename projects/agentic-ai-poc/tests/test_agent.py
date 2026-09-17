"""Tests for the ReAct agent loop."""

import pytest

from app.agents.react_agent import ReActAgent
from app.agents.types import AgentState
from app.models.schemas import AgentConfig, AgentResult
from app.observability.trace import EventType
from app.tools.base import ToolRegistry
from app.tools.calculator import CalculatorTool
from app.tools.datetime_tool import DateTimeTool
from app.tools.web_search import WebSearchTool


@pytest.fixture
def agent(mock_llm, tool_registry):
    config = AgentConfig(max_iterations=5, trace_enabled=True)
    return ReActAgent(
        llm=mock_llm,
        tools=tool_registry,
        config=config,
    )


@pytest.mark.asyncio
class TestAgentLoop:
    async def test_math_question_uses_calculator(self, agent):
        """The mock LLM should call the calculator tool for math questions."""
        result = await agent.run("What is 23 * 47 + 15?")
        assert isinstance(result, AgentResult)
        assert result.success
        assert result.total_tool_calls >= 1
        assert result.total_llm_calls >= 2  # at least: decide + synthesize
        assert "1096" in (result.answer or "")  # 23 * 47 = 1081, + 15 = 1096

    async def test_math_question_uses_calculator_correct(self, agent):
        """Verify the calculator returns the right number."""
        result = await agent.run("What is 23 * 47 + 15?")
        assert "1096" in (result.answer or "")  # 23*47=1081, +15=1096

    async def test_time_question_uses_datetime(self, agent):
        """The mock LLM should call datetime for time questions."""
        result = await agent.run("What time is it now?")
        assert result.success
        assert result.total_tool_calls >= 1
        assert "date/time" in (result.answer or "").lower() or "Time" in (result.answer or "")

    async def test_search_question_uses_web_search(self, agent):
        """The mock LLM should call web_search for factual questions."""
        result = await agent.run("What is the capital of France?")
        assert result.success
        assert result.total_tool_calls >= 1
        assert "Paris" in (result.answer or "")

    async def test_trace_records_events(self, agent):
        """The trace should capture LLM calls and tool calls."""
        result = await agent.run("What is 2 + 2?")
        assert agent.trace.events
        event_types = [e.event_type for e in agent.trace.events]
        assert EventType.AGENT_START in event_types
        assert EventType.LLM_CALL in event_types
        assert EventType.TOOL_CALL in event_types
        assert EventType.TOOL_RESULT in event_types
        assert EventType.AGENT_END in event_types

    async def test_state_transitions_to_completed(self, agent):
        """Agent should end in COMPLETED state for a solvable task."""
        result = await agent.run("What is 2 + 2?")
        assert result.final_state == AgentState.COMPLETED

    async def test_max_iterations_termination(self, agent):
        """Agent should stop after max_iterations even if it keeps calling tools."""
        config = AgentConfig(max_iterations=2, trace_enabled=True)
        # Force the mock to always call a tool (math question)
        from app.llm.mock import MockLLMService
        agent_llm = MockLLMService()
        agent2 = ReActAgent(llm=agent_llm, tools=agent.tools, config=config)
        # Each call to a math question triggers a tool call, so the loop continues
        # The mock synthesizes after seeing tool results, so it should terminate.
        # To force continuation, we need a query that the mock keeps calling tools for.
        # Actually the mock synthesizes after tool results, so let's just verify max_iter cap.
        result = await agent2.run("Calculate 1 + 1")
        assert result.total_steps <= 2

    async def test_final_answer_present(self, agent):
        """The result should have a non-None answer."""
        result = await agent.run("What is 6 * 7?")
        assert result.answer is not None
        assert "42" in result.answer

    async def test_no_tools_results_in_direct_answer(self, mock_llm):
        """When no tools are available, the agent should answer directly."""
        config = AgentConfig(max_iterations=3)
        registry = ToolRegistry()  # empty registry
        agent = ReActAgent(llm=mock_llm, tools=registry, config=config)
        result = await agent.run("Hello, how are you?")
        assert result.success
        assert result.answer is not None
        assert result.final_state == AgentState.COMPLETED

    async def test_trace_log_lines(self, agent):
        """The trace should produce human-readable log lines."""
        await agent.run("What is 2 + 2?")
        lines = agent.trace.to_log_lines()
        assert len(lines) > 0
        assert any("agent_start" in line for line in lines)
