"""
Base agent — abstract foundation for all agent implementations.

Contains the shared machinery that every agent needs:

- **State management** — tracks and logs state transitions
- **Tool execution with guardrails** — allow-list check, HITL approval, timeout
- **Tracing** — logs every event to the execution trace
- **Memory management** — delegates to short-term and working memory

Subclasses (e.g. ``ReActAgent``) implement the ``run`` method, which
contains the actual agent loop.
"""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from app.agents.types import AgentState, HitlApprover, AlwaysApprove
from app.llm.service import LLMInterface
from app.memory.short_term import ConversationBuffer
from app.memory.working import InMemoryWorkingMemory
from app.models.schemas import (
    AgentConfig,
    AgentResult,
    ConversationMessage,
    LLMResponse,
    Role,
    ToolCall,
    ToolExecutionResult,
)
from app.observability.trace import ExecutionTrace, EventType
from app.tools.base import Tool, ToolRegistry, ToolResult

logger = logging.getLogger(__name__)

# Default system prompt for the agent. This is the "constitution" that tells
# the LLM how to behave. It is intentionally explicit so learners can see
# exactly what instructions the LLM receives.
DEFAULT_SYSTEM_PROMPT = """You are a helpful AI agent that can use tools to accomplish tasks.

You have access to tools. For each turn:

1. Think about what the user needs.
2. If a tool can help, call it. You can call multiple tools in the same turn
   if they are independent.
3. After tools execute, you will see their results. Use the results to
   inform your next action.
4. When you have enough information to answer the user's question, provide
   your final answer in the response content.

Guidelines:
- Only call tools when they are genuinely helpful.
- Never make up tool results or observations.
- If a tool fails, note the error and try a different approach or inform the user.
- Work step by step. Think before each action.
- Your goal is to be helpful, harmless, and honest.

Begin by thinking about the user's request and what tools (if any) you need.
"""


class BaseAgent(ABC):
    """Abstract base class for all agents.

    Subclasses implement ``run()`` — the agent loop. The base class provides:

    - ``_execute_tool``: safely execute a tool call with guardrails
    - ``_transition_state``: state machine with trace logging
    - ``_llm_call``: wrapper around LLM.generate with tracing
    - Memory management (short-term + working)
    """

    def __init__(
        self,
        llm: LLMInterface,
        tools: ToolRegistry,
        *,
        config: Optional[AgentConfig] = None,
        memory: Optional[ConversationBuffer] = None,
        working_memory: Optional[InMemoryWorkingMemory] = None,
        trace: Optional[ExecutionTrace] = None,
        approver: Optional[HitlApprover] = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        self.llm = llm
        self.tools = tools
        self.config = config or AgentConfig()
        self.memory = memory or ConversationBuffer()
        self.working = working_memory or InMemoryWorkingMemory()
        self.trace = trace or ExecutionTrace()
        self.approver = approver or AlwaysApprove()
        self.system_prompt = system_prompt
        self._state: AgentState = AgentState.IDLE

    @property
    def state(self) -> AgentState:
        return self._state

    def _transition(self, new_state: AgentState, label: str | None = None) -> None:
        """Transition to a new state, logging the change."""
        old = self._state
        self._state = new_state
        if old != new_state:
            self.trace.log(
                EventType.STATE_CHANGE,
                label=label or f"{old.value} → {new_state.value}",
                step=self.config.max_iterations,
                old_state=old.value,
                new_state=new_state.value,
            )

    # ------------------------------------------------------------------
    # Tool execution with guardrails
    # ------------------------------------------------------------------

    async def _execute_tool(self, tool_call: ToolCall) -> ToolExecutionResult:
        """Execute a single tool call with all guardrails applied.

        Guardrails:
        1. Allow-list check — only permitted tools can run
        2. Human-in-the-loop approval — for high-risk tools
        3. Timeout — tool execution cannot hang the agent
        4. Error catching — failures become observations, not crashes

        Returns a ``ToolExecutionResult`` that is fed back to the LLM.
        """
        tool_name = tool_call.function.name
        self.trace.log(
            EventType.TOOL_CALL,
            tool_name=tool_name,
            tool_call_id=tool_call.id,
            arguments=tool_call.function.arguments,
        )

        # 1. Allow-list check
        if not self.tools.is_allowed(tool_name):
            error_msg = f"Tool '{tool_name}' is not in the allow-list and has been blocked."
            self.trace.log(EventType.TOOL_ERROR, tool_name=tool_name, error=error_msg)
            return ToolExecutionResult(
                tool_call_id=tool_call.id,
                tool_name=tool_name,
                success=False,
                content=error_msg,
                error=error_msg,
            )

        # 2. Look up the tool
        tool = self.tools.get(tool_name)
        if tool is None:
            error_msg = f"Tool '{tool_name}' is not registered."
            self.trace.log(EventType.TOOL_ERROR, tool_name=tool_name, error=error_msg)
            return ToolExecutionResult(
                tool_call_id=tool_call.id,
                tool_name=tool_name,
                success=False,
                content=error_msg,
                error=error_msg,
            )

        # 3. Human-in-the-loop approval
        if self._requires_approval(tool_name):
            approved = await self.approver.approve(
                tool_name, self._parse_args(tool_call.function.arguments)
            )
            self.trace.log(EventType.HITL_APPROVAL, tool_name=tool_name, approved=approved)
            if not approved:
                error_msg = (
                    f"Tool '{tool_name}' was blocked by human-in-the-loop approval."
                )
                return ToolExecutionResult(
                    tool_call_id=tool_call.id,
                    tool_name=tool_name,
                    success=False,
                    content=error_msg,
                    error=error_msg,
                )

        # 4. Execute with timeout
        try:
            result: ToolResult = await asyncio.wait_for(
                tool.call(tool_call.function.arguments),
                timeout=self.config.tool_timeout,
            )
        except asyncio.TimeoutError:
            error_msg = f"Tool '{tool_name}' timed out after {self.config.tool_timeout}s"
            self.trace.log(EventType.TOOL_ERROR, tool_name=tool_name, error=error_msg)
            return ToolExecutionResult(
                tool_call_id=tool_call.id,
                tool_name=tool_name,
                success=False,
                content="",
                error=error_msg,
            )

        success = result.success
        self.trace.log(
            EventType.TOOL_RESULT,
            tool_name=tool_name,
            success=success,
            execution_time=getattr(result, 'execution_time', 0),
        )
        if not success:
            self.trace.log(EventType.TOOL_ERROR, tool_name=tool_name, error=result.error)

        return ToolExecutionResult(
            tool_call_id=tool_call.id,
            tool_name=tool_name,
            success=success,
            content=result.content if success else "",
            error=result.error if not success else None,
        )

    @staticmethod
    def _parse_args(arguments: str) -> dict:
        """Parse JSON tool arguments, with fallback."""
        if not arguments or arguments.strip() == "":
            return {}
        try:
            return json.loads(arguments)
        except json.JSONDecodeError:
            try:
                return json.loads(arguments + "}")
            except json.JSONDecodeError:
                return {}

    def _requires_approval(self, tool_name: str) -> bool:
        """Check if a tool requires human approval."""
        if not self.config.human_in_the_loop:
            return False
        required = self.config.required_approval_tools or set()
        return tool_name in required

    # ------------------------------------------------------------------
    # LLM call wrapper
    # ------------------------------------------------------------------

    async def _llm_call(
        self,
        messages: list[ConversationMessage],
        step: int,
    ) -> LLMResponse:
        """Call the LLM with tracing."""
        tool_defs = self.tools.definitions(allowed_only=True)
        self._transition(AgentState.THINKING, label="Calling LLM")
        self.trace.log(
            EventType.LLM_CALL,
            step=step,
            model=self.llm.model_name,
            message_count=len(messages),
            tool_count=len(tool_defs),
        )

        response = await self.llm.generate(
            messages=messages,
            tools=tool_defs if tool_defs else None,
            temperature=self.config.temperature,
            max_tokens=self.config.max_output_tokens or 4096,
        )

        self.trace.log(
            EventType.LLM_RESPONSE,
            step=step,
            has_tool_calls=response.has_tool_calls,
            finish_reason=response.finish_reason,
        )
        return response

    # ------------------------------------------------------------------
    # Observation building
    # ------------------------------------------------------------------

    def _build_messages(self) -> list[ConversationMessage]:
        """Build the full message list for the LLM: system + history."""
        messages: list[ConversationMessage] = [
            ConversationMessage(role=Role.SYSTEM, content=self.system_prompt)
        ]
        messages.extend(self.memory.get_messages())
        return messages

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    async def run(self, user_input: str, conversation_id: Optional[str] = None) -> AgentResult:
        """Execute the agent loop on a user input.

        Subclasses implement the actual loop logic (ReAct, plan-and-execute, etc.).
        """
        ...
