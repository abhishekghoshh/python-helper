"""
Interactive CLI demo for the Agentic AI POC.

Run with:  python -m app.cli

Demonstrates the agent loop end-to-end using the mock LLM (no API key needed).
Type a question, and watch the agent observe → reason → act → observe loop.
"""

from __future__ import annotations

import asyncio
import sys

from app.agents.react_agent import ReActAgent
from app.agents.types import AgentState
from app.core.config import settings
from app.llm.mock import MockLLMService
from app.memory.short_term import ConversationBuffer
from app.memory.working import InMemoryWorkingMemory
from app.models.schemas import AgentConfig
from app.observability.trace import ExecutionTrace
from app.tools.calculator import CalculatorTool
from app.tools.datetime_tool import DateTimeTool
from app.tools.file_reader import FileReaderTool
from app.tools.web_search import WebSearchTool
from app.tools.base import ToolRegistry


def build_demo_agent() -> ReActAgent:
    """Build a demo agent with the mock LLM and all non-RAG tools."""
    tools = ToolRegistry()
    tools.register(CalculatorTool())
    tools.register(DateTimeTool())
    tools.register(FileReaderTool())
    tools.register(WebSearchTool())

    config = AgentConfig(
        max_iterations=settings.agent_max_iterations,
        trace_enabled=True,
        temperature=settings.llm_temperature,
    )
    memory = ConversationBuffer(max_chars=settings.memory_max_history_chars)
    working = InMemoryWorkingMemory()
    trace = ExecutionTrace()

    return ReActAgent(
        llm=MockLLMService(),
        tools=tools,
        config=config,
        memory=memory,
        working_memory=working,
        trace=trace,
    )


def print_trace_summary(trace: ExecutionTrace) -> None:
    """Print a human-readable trace of the agent's execution."""
    print("\n" + "=" * 60)
    print("  EXECUTION TRACE")
    print("=" * 60)
    for line in trace.to_log_lines():
        print(f"  {line}")
    print("=" * 60 + "\n")


async def main() -> None:
    print("""
============================================================
  Agentic AI POC — ReAct Agent Demo
  (Using Mock LLM — no API key required)
============================================================
Type your question and press Enter.
Examples:
  - What is 23 * 47 + 15?
  - What time is it now?
  - What is the capital of France?
  - Read file sample.txt
Type 'quit' or 'exit' to end.
============================================================
""")

    agent = build_demo_agent()

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if user_input.lower() in ("quit", "exit"):
            print("Goodbye!")
            break

        if not user_input:
            continue

        # Run the agent
        result = await agent.run(user_input)

        print(f"\n[State: {result.final_state.value}]")
        print(f"[Steps: {result.total_steps} | Tool calls: {result.total_tool_calls} | LLM calls: {result.total_llm_calls}]")
        print(f"\nAnswer:\n{result.answer}\n")

        print_trace_summary(agent.trace)

        if result.error:
            print(f"[Error: {result.error}]")


if __name__ == "__main__":
    asyncio.run(main())
