"""
API dependencies — factory functions for wiring the agent and services.

These use FastAPI's dependency injection (``Depends``) so each request
gets the right LLM backend (mock or real), tools, and memory without
module-level global state bleeding between requests.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends

from app.agents.react_agent import ReActAgent
from app.agents.types import AlwaysApprove
from app.core.config import settings
from app.llm.mock import MockLLMService, mock_llm_service
from app.llm.service import LLMInterface, OpenAILLMService
from app.memory.short_term import ConversationBuffer
from app.memory.working import InMemoryWorkingMemory
from app.models.schemas import AgentConfig
from app.tools.base import ToolRegistry
from app.tools.factory import create_tool_registry


def get_llm_service() -> LLMInterface:
    """Return the configured LLM service.

    In simulated mode (default), returns the mock LLM — no API key needed.
    In production mode, returns the OpenAI-compatible service.
    """
    if settings.use_mock_llm:
        return mock_llm_service
    # Real LLM — create a fresh service (stateless per request is fine here)
    return OpenAILLMService()


def get_tool_registry(llm: LLMInterface = Depends(get_llm_service)) -> ToolRegistry:
    """Build a fresh tool registry for the request."""
    return create_tool_registry(
        llm_service=llm,
        allow_list=settings.tool_allowlist_set,
    )


def get_agent(
    llm: LLMInterface = Depends(get_llm_service),
    tools: ToolRegistry = Depends(get_tool_registry),
) -> ReActAgent:
    """Build a ReAct agent wired with LLM, tools, and memory."""
    config = AgentConfig(
        max_iterations=settings.agent_max_iterations,
        iteration_delay=settings.agent_iteration_delay,
        trace_enabled=settings.agent_trace_enabled,
        temperature=settings.llm_temperature,
        tool_allow_list=settings.tool_allowlist_set,
        human_in_the_loop=settings.hitl_enabled,
        required_approval_tools=settings.hitl_required_tools_set,
    )
    memory = ConversationBuffer(max_chars=settings.memory_max_history_chars)
    working = InMemoryWorkingMemory()
    approver = AlwaysApprove()

    return ReActAgent(
        llm=llm,
        tools=tools,
        config=config,
        memory=memory,
        working_memory=working,
        approver=approver,
    )
