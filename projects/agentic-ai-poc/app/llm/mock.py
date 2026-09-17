"""
Mock LLM service — a simulated LLM that demonstrates tool calling without
requiring an API key or network access.

The mock works in two phases:

1. **Decision phase** — when the conversation has no tool results yet, the
   mock inspects the latest user message and decides (via keyword heuristics)
   which tool(s) to call and with what arguments.
2. **Synthesis phase** — when the conversation *does* contain tool results,
   the mock reads the results and produces a final answer.

This is intentionally simple. It is **not** meant to replace a real LLM —
it exists so the agent loop, tool calling, memory, and observability can
be developed, tested, and understood **offline**. Swap in ``OpenAILLMService``
for real intelligence.

Each heuristic is a small method, making the decision logic transparent and
easy to extend for learning.
"""

from __future__ import annotations

import json
import logging
import re

from app.models.schemas import ConversationMessage, LLMResponse, Role, ToolCall, ToolCallFunction, ToolDefinition
from app.observability.trace import EventType

logger = logging.getLogger(__name__)


class MockLLMService:
    """Simulated LLM with keyword-based tool-calling decisions.

    Set ``force_tool`` to always call a specific tool (useful for testing).
    Set ``force_response`` to always return a specific text (useful for
    testing the synthesis path).
    """

    def __init__(
        self,
        force_tool: str | None = None,
        force_response: str | None = None,
    ) -> None:
        self._model_name = "mock-gpt-4o-mini"
        self._force_tool = force_tool
        self._force_response = force_response
        self._call_count = 0

    @property
    def model_name(self) -> str:
        return self._model_name

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _last_user_message(messages: list[ConversationMessage]) -> str:
        for msg in reversed(messages):
            if msg.role == Role.USER and msg.content:
                return msg.content
        return ""

    @staticmethod
    def _has_tool_results(messages: list[ConversationMessage]) -> bool:
        """True if the **last** message is an unprocessed tool result.

        We check only the last message because a real LLM sees the full
        conversation and produces a new decision for the latest user turn.
        Tool results from *previous* turns have already been addressed.
        """
        if not messages:
            return False
        last = messages[-1]
        return last.role == Role.TOOL and bool(last.content)

    @staticmethod
    def _extract_tool_results(messages: list[ConversationMessage]) -> list[tuple[str, str]]:
        """Return list of (tool_name, result_content) from the **current turn's** tool messages.

        Only tool messages that come after the last assistant message with
        a text response are included — these are the unprocessed results
        from the current decision.
        """
        results: list[tuple[str, str]] = []
        # Walk backwards to find the contiguous block of tool messages
        # at the end of the conversation (the current turn's results).
        for msg in reversed(messages):
            if msg.role == Role.TOOL:
                content = msg.content or ""
                if not content:
                    content = "[tool returned no output]"
                results.append((msg.tool_name or "unknown", content))
            else:
                break
        results.reverse()
        return results

    # ------------------------------------------------------------------
    # Phase 1: Decision — choose a tool based on the user's query
    # ------------------------------------------------------------------

    def _decide_tool_call(self, query: str, available_tools: list[ToolDefinition]) -> LLMResponse:
        """Heuristic tool selection based on keyword matching.

        Returns a response with ``tool_calls`` set (the LLM "wants to use a tool").

        Dispatch order:
        1. Math → calculator
        2. Recent/news → web_search
        3. Time/date → datetime_now
        4. File reading → file_reader
        5. Factual question → rag_query (if available), else web_search
        6. Fallback → direct answer
        """
        available_names = {
            tc.function.name for tc in [self._to_call(t) for t in available_tools]
        }

        # If a specific tool is forced, use it.
        if self._force_tool and self._force_tool in available_names:
            return self._make_tool_call(self._force_tool, self._guess_args(self._force_tool, query))

        query_lower = query.lower()

        # 1. Math / calculation
        if self._detect_math(query_lower):
            if "calculator" in available_names:
                expr = self._extract_math_expression(query)
                return self._make_tool_call("calculator", {"expression": expr or query})

        # 2. Recent / current events → web search
        if any(kw in query_lower for kw in ["latest", "recent", "news", "current", "weather", "stock", "price"]):
            if "web_search" in available_names:
                return self._make_tool_call("web_search", {"query": query})

        # 3. Date / time
        if any(kw in query_lower for kw in ["time", "date", "today", "now", "current", "day of"]):
            if "datetime_now" in available_names:
                args = {}
                if any(kw in query_lower for kw in ["new_york", "est", "eastern"]):
                    args["timezone"] = "America/New_York"
                return self._make_tool_call("datetime_now", args)

        # 4. File reading
        if any(kw in query_lower for kw in ["file", "read file", "open", "document", "load file", "file://"]):
            if "file_reader" in available_names:
                path = self._extract_path(query)
                return self._make_tool_call("file_reader", {"path": path or "README.md"})

        # 5. Factual question → try rag_query, then web_search
        is_factual = any(qw in query_lower for qw in [
            "what is", "who is", "where is", "when is", "capital of",
            "tell me about", "explain", "how does", "summarize", "what are",
        ])
        if is_factual:
            if "rag_query" in available_names:
                return self._make_tool_call("rag_query", {"question": query})
            if "web_search" in available_names:
                return self._make_tool_call("web_search", {"query": query})

        # 6. Fallback: answer directly
        return self._make_text_response(self._default_answer(query))

    # ------------------------------------------------------------------
    # Phase 2: Synthesis — produce a final answer from tool results
    # ------------------------------------------------------------------

    def _synthesize_answer(self, query: str, tool_results: list[tuple[str, str]]) -> LLMResponse:
        """Produce a final answer after seeing one or more tool results."""
        if self._force_response is not None:
            return self._make_text_response(self._force_response)

        # Combine tool results into a synthesis
        if not tool_results:
            return self._make_text_response(self._default_answer(query))

        # Synthesize: reference what the tools found
        parts: list[str] = []
        for tool_name, result in tool_results:
            parts.append(f"{tool_name}: {result}")

        combined = " | ".join(parts)
        answer = (
            f"Based on my analysis, here's what I found:\n\n{combined}\n\n"
            f"Is there anything else you'd like me to help with?"
        )

        return self._make_text_response(answer)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _to_call(tool: ToolDefinition) -> ToolCall:
        return ToolCall(
            id=f"call_mock_{id(tool)}",
            function=ToolCallFunction(name=tool.function.name, arguments="{}"),
        )

    @staticmethod
    def _make_tool_call(name: str, arguments: dict) -> LLMResponse:
        args_json = json.dumps(arguments)
        return LLMResponse(
            id=f"mock_resp_{id(args_json)}",
            model="mock-gpt-4o-mini",
            content=None,
            tool_calls=[
                ToolCall(
                    id="call_mock",
                    function=ToolCallFunction(name=name, arguments=args_json),
                )
            ],
            finish_reason="tool_calls",
        )

    @staticmethod
    def _make_text_response(content: str) -> LLMResponse:
        return LLMResponse(
            id="mock_resp_text",
            model="mock-gpt-4o-mini",
            content=content,
            tool_calls=None,
            finish_reason="stop",
        )

    @staticmethod
    def _detect_math(query: str) -> bool:
        """Detect if the query is asking for a calculation."""
        # Look for arithmetic operators with numbers
        if re.search(r"\d+\s*[\+\-\*/]\s*\d+", query):
            return True
        if re.search(r"\b(calculate|compute|solve|sum of|multiply|divide|add|subtract)\b", query):
            return True
        return False

    @staticmethod
    def _extract_math_expression(query: str) -> str | None:
        """Try to extract a math expression from the query.

        Starts matching at the first digit and greedily consumes digits,
        whitespace, and arithmetic operators/parentheses.
        """
        match = re.search(r"\d+[\d\s\+\-\*/\.\(\)]*", query)
        if match:
            return match.group(0).strip()
        # Fallback: look for "calculate <expr>" or "compute <expr>"
        match = re.search(r"(?:calculate|compute|solve)\s+(.+)", query, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    @staticmethod
    def _extract_path(query: str) -> str | None:
        """Extract a file path from the query."""
        # Look for path-like patterns
        match = re.search(r"[\w\-_./]+\.md|[\w\-_./]+\.txt|[\w\-_./]+\.py", query)
        if match:
            return match.group(0)
        match = re.search(r"file://(\S+)", query)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _guess_args(self_tool_name: str, query: str) -> dict:
        """Generate plausible arguments for a forced tool based on the query."""
        if self_tool_name == "calculator":
            expr = MockLLMService._extract_math_expression(query)
            return {"expression": expr or query}
        if self_tool_name == "datetime_now":
            return {}
        if self_tool_name == "web_search":
            return {"query": query}
        if self_tool_name == "rag_query":
            return {"question": query}
        if self_tool_name == "file_reader":
            path = MockLLMService._extract_path(query)
            return {"path": path or "README.md"}
        return {}

    @staticmethod
    def _default_answer(query: str) -> str:
        """A fallback response when no tools are called."""
        return (
            f"I'm a simulated LLM demo. I looked at your query: \"{query}\". "
            f"In a real deployment, I would use a real LLM API (e.g. OpenAI) "
            f"to generate a response. This mock demonstrates the agent loop "
            f"mechanics without requiring an API key."
        )

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def generate(
        self,
        messages: list[ConversationMessage],
        tools: list[ToolDefinition] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Simulate an LLM call.

        Decision logic:
        - If tool results exist in the conversation → synthesize a final answer.
        - Otherwise → use heuristics to decide which tool to call.
        """
        self._call_count += 1
        tools = tools or []

        query = self._last_user_message(messages)
        has_results = self._has_tool_results(messages)

        if has_results:
            tool_results = self._extract_tool_results(messages)
            return self._synthesize_answer(query, tool_results)

        if not tools:
            # No tools available — just answer
            return self._make_text_response(self._default_answer(query))

        return self._decide_tool_call(query, tools)

    async def generate_stream(
        self,
        messages: list[ConversationMessage],
        tools: list[ToolDefinition] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        """Simulate streaming by yielding the content token-by-token (character by character)."""
        response = await self.generate(messages, tools, temperature, max_tokens)
        if response.content:
            for char in response.content:
                yield char
        elif response.tool_calls:
            # For streaming, we yield a marker then the tool call info
            yield f"[Tool call: {response.tool_calls[0].function.name}]"


def get_mock_llm_service() -> MockLLMService:
    """Factory for the mock LLM service (module-level convenience)."""
    return MockLLMService()


# Module-level singleton
mock_llm_service = MockLLMService()
