"""
ReAct Agent — the explicit agent loop.

This is the **core** of what makes a system "agentic". The loop is written
out explicitly as a ``while`` statement so learners can see every step.
No framework hides the loop.

### The ReAct Loop

```
Observe → Reason (LLM) → Act (Tool) → Observe → Reason → ... → Final Answer
```

At each iteration:
1. The conversation history (system prompt + all messages) is sent to the LLM.
2. The LLM decides: call a tool, or respond directly.
3. If tool calls → execute them, add results as observations, **loop back**.
4. If a text response → **stop**, return the answer.
5. If neither (edge case) → terminate with a diagnostic.

Termination conditions:
- LLM produces a text response (no tool calls)
- ``max_iterations`` reached
- An unrecoverable error occurs

Guardrails applied on every tool call:
- Allow-list check (only permitted tools)
- Human-in-the-loop approval (for risky tools)
- Timeout (no hanging tools)
- Error catching (failures become observations, not crashes)
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Optional

from app.agents.base import BaseAgent
from app.agents.types import AgentState
from app.core.config import settings
from app.llm.service import LLMInterface
from app.memory.short_term import ConversationBuffer
from app.models.schemas import (
    AgentConfig,
    AgentResult,
    ConversationMessage,
    Role,
    ToolCall,
    ToolExecutionResult,
)
from app.observability.trace import ExecutionTrace, EventType
from app.tools.base import ToolRegistry

logger = logging.getLogger(__name__)


class ReActAgent(BaseAgent):
    """A ReAct-style agent with an explicit observe→reason→act loop.

    The name **ReAct** comes from the paper "ReAct: Synergizing Reasoning
    and Acting in Language Models" (Yao et al., 2022). The core idea:
    interleave reasoning (chain-of-thought) with tool actions, using
    observations to guide the next reasoning step.
    """

    def __init__(
        self,
        llm: LLMInterface,
        tools: ToolRegistry,
        **kwargs,
    ) -> None:
        super().__init__(llm, tools, **kwargs)

    async def run(
        self,
        user_input: str,
        conversation_id: Optional[str] = None,
    ) -> AgentResult:
        """Execute the agent loop on a user input.

        Args:
            user_input: The user's message / task.
            conversation_id: Optional ID for tracking (memory, tracing).

        Returns:
            An ``AgentResult`` with the final answer, state, and trace.
        """
        self._transition(AgentState.RUNNING, label=f"Starting agent run")
        self.trace.log(
            EventType.AGENT_START,
            conversation_id=conversation_id or str(uuid.uuid4()),
            user_input=user_input[:200],
        )

        # Add the user message to short-term memory
        self.memory.add_user(user_input)
        self.working.set("task", user_input)

        iteration = 0
        tool_call_count = 0
        llm_call_count = 0
        final_answer: Optional[str] = None
        error_msg: Optional[str] = None

        max_iter = self.config.max_iterations

        while iteration < max_iter:
            iteration += 1
            self.trace.set_step(iteration)
            self.trace.log(
                EventType.OBSERVATION,
                step=iteration,
                message_count=len(self.memory.get_messages()),
            )

            # Optional delay between iterations (rate limiting)
            if self.config.iteration_delay > 0:
                await asyncio.sleep(self.config.iteration_delay)

            # --- Step 1: Call the LLM ---
            messages = self._build_messages()
            llm_response = await self._llm_call(messages, step=iteration)
            llm_call_count += 1

            # --- Step 2: Observe the response ---
            self._transition(AgentState.OBSERVING, label="Processing LLM response")

            has_tool_calls = llm_response.has_tool_calls

            # --- Step 3: If tool calls, execute them and loop back ---
            if has_tool_calls and llm_response.tool_calls:
                self._transition(AgentState.TOOL_CALLING, label=f"Executing {len(llm_response.tool_calls)} tool call(s)")

                # Add the assistant's tool-call message to memory first
                self.memory.add(ConversationMessage(
                    role=Role.ASSISTANT,
                    content=llm_response.content,
                    tool_calls=llm_response.tool_calls,
                ))

                # Execute all tool calls for this turn
                tool_results: list[ToolExecutionResult] = []
                for tool_call in self.tool_calls_to_execute(llm_response.tool_calls):
                    self.trace.log(
                        EventType.PLANNING,
                        step=iteration,
                        tool_name=tool_call.function.name,
                    )
                    result = await self._execute_tool(tool_call)
                    tool_results.append(result)
                    tool_call_count += 1

                # Add tool results as observations to memory
                for result in tool_results:
                    self.memory.add(result.to_message())

                self._transition(AgentState.OBSERVING, label="Tool results observed, continuing loop")
                continue  # back to the top of the loop

            # --- Step 4: If text response, we're done ---
            if llm_response.content:
                final_answer = llm_response.content
                # Record the final answer in memory so the next turn has full context
                self.memory.add(ConversationMessage(role=Role.ASSISTANT, content=final_answer))
                self._transition(AgentState.COMPLETED, label="Final answer produced")
                self.trace.log(
                    EventType.AGENT_END,
                    step=iteration,
                    success=True,
                    total_steps=iteration,
                    total_tool_calls=tool_call_count,
                )
                break

            # --- Step 5: Edge case — no content and no tool calls ---
            error_msg = (
                f"LLM produced no content and no tool calls on iteration {iteration}. "
                f"finish_reason={llm_response.finish_reason!r}"
            )
            logger.warning(error_msg)
            self.trace.log(EventType.WARNING, step=iteration, message=error_msg)

            # Ask the LLM to reconsider by adding a clarification prompt
            if iteration < max_iter:
                self.memory.add(ConversationMessage(
                    role=Role.USER,
                    content="Please provide a response. If you need to use a tool, do so. "
                            "Otherwise, answer the user's question directly.",
                ))
                continue
            else:
                error_msg = f"Agent could not produce a response within {max_iter} iterations."
                break

        else:
            # Loop exhausted without break — max iterations reached
            self._transition(AgentState.MAX_ITERATIONS, label="Max iterations reached")
            self.trace.log(
                EventType.AGENT_END,
                step=iteration,
                success=False,
                reason="max_iterations",
                total_steps=iteration,
                total_tool_calls=tool_call_count,
            )
            if final_answer is None:
                final_answer = (
                    "I've reached my maximum number of iterations without producing "
                    "a final answer. I may need more steps or a different approach."
                )

        if final_answer is None:
            final_answer = error_msg or "No response was generated."

        # Build the final result from the trace
        steps = self._build_step_history(iteration, tool_call_count, llm_call_count)

        return AgentResult(
            success=self._state == AgentState.COMPLETED,
            answer=final_answer,
            final_state=self._state,
            total_steps=iteration,
            total_tool_calls=tool_call_count,
            total_llm_calls=llm_call_count,
            trace=[],
            error=error_msg if self._state != AgentState.COMPLETED else None,
        )

    def tool_calls_to_execute(self, tool_calls: list[ToolCall]) -> list[ToolCall]:
        """Filter and order tool calls for execution.

        Currently returns all calls. In a more sophisticated agent this
        could:
        - Filter out blocked tools
        - Reorder dependent vs. independent calls
        - Deduplicate
        """
        # Apply guardrail: only allow-listed tools
        return [tc for tc in tool_calls if self.tools.is_allowed(tc.function.name)]

    def _build_step_history(self, iterations: int, tool_calls: int, llm_calls: int) -> list:
        """Build a summary list of steps from the trace."""
        # The detailed trace is in self.trace; this is a lightweight summary.
        return [
            {
                "iterations": iterations,
                "tool_calls": tool_calls,
                "llm_calls": llm_calls,
            }
        ]
