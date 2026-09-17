"""
Tool base classes and result types.

A **tool** is a function the agent can invoke. The defining characteristic
of an agentic system (vs. a fixed LLM workflow) is that the **LLM chooses**
which tool to call and with what arguments — the application code just
provides the mechanism.

### Design

``Tool`` is an abstract base. Each concrete tool (Calculator, DateTime, etc.)
implements ``execute``; the base class handles:

- Converting the tool into an OpenAI-format ``ToolDefinition``
- Parsing and validating keyword arguments from the LLM's JSON string
- Wrapping the result in a structured ``ToolResult``
- Timing and error handling

``ToolRegistry`` collects all available tools, enforces the allow-list
guardrail, and provides lookup by name.
"""

from __future__ import annotations

import asyncio
import json
import time
from abc import ABC, abstractmethod
from typing import Any, Optional

from app.models.schemas import ToolDefinition, FunctionDef


class ToolResult:
    """Structured result of a tool execution.

    The agent converts this back into an LLM-readable string for the
    next turn in the agent loop.
    """

    def __init__(
        self,
        tool_name: str,
        content: str,
        success: bool = True,
        error: Optional[str] = None,
        execution_time: float = 0.0,
    ) -> None:
        self.tool_name = tool_name
        self.content = content
        self.success = success
        self.error = error
        self.execution_time = execution_time

    def to_observation(self) -> str:
        """Format the result as an observation string for the LLM."""
        if self.success:
            return f"[{self.tool_name}] Success. Result: {self.content}"
        return f"[{self.tool_name}] Error: {self.error}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "content": self.content,
            "error": self.error,
            "execution_time": round(self.execution_time, 4),
        }


class Tool(ABC):
    """Abstract base class for all tools.

    Subclasses must define:
    - ``name``: the identifier the LLM uses to call this tool
    - ``description``: a clear, LLM-friendly description
    - ``parameters``: a JSON Schema dict for the tool's arguments
    - ``execute``: the actual logic (async for consistency)

    The base class provides ``to_definition`` (OpenAI format) and
    ``call`` (parse args → execute → wrap result).
    """

    name: str
    description: str
    parameters: dict[str, Any] = {}
    category: str = "general"

    def to_definition(self) -> ToolDefinition:
        """Return the OpenAI-format tool definition."""
        return ToolDefinition(
            type="function",
            function=FunctionDef(
                name=self.name,
                description=self.description,
                parameters=self.parameters,
            ),
        )

    def to_info(self) -> dict[str, Any]:
        """Return a summary dict for listing tools via the API."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "category": self.category,
        }

    def _parse_arguments(self, arguments: str) -> dict[str, Any]:
        """Parse the LLM's JSON argument string, with fallback handling."""
        if not arguments or arguments.strip() == "":
            return {}
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError:
            # The LLM sometimes emits partial or trailing JSON.
            # Try adding a closing brace.
            try:
                parsed = json.loads(arguments + "}")
            except json.JSONDecodeError:
                raise ValueError(f"Could not parse tool arguments as JSON: {arguments!r}")
        return parsed

    async def call(self, arguments: str) -> ToolResult:
        """Parse arguments, execute the tool, and return a structured result.

        This is the entry point used by the agent loop. It handles:
        - JSON argument parsing
        - Parameter validation (via ``_validate_args``)
        - Timing
        - Error catching (never lets exceptions escape)
        """
        start = time.time()
        try:
            kwargs = self._parse_arguments(arguments)
            self._validate_args(kwargs)
            result = await self.execute(**kwargs)
            if not isinstance(result, ToolResult):
                result = ToolResult(self.name, str(result))
            result.execution_time = time.time() - start
            return result
        except asyncio.TimeoutError:
            return ToolResult(
                self.name, "",
                success=False,
                error=f"Tool '{self.name}' timed out after {self._timeout_seconds()}s",
                execution_time=time.time() - start,
            )
        except Exception as e:
            return ToolResult(
                self.name, "",
                success=False,
                error=f"{type(e).__name__}: {e}",
                execution_time=time.time() - start,
            )

    def _timeout_seconds(self) -> float:
        """Override in subclasses to set a per-tool timeout."""
        from app.core.config import settings
        return settings.tool_timeout_seconds

    def _validate_args(self, kwargs: dict[str, Any]) -> None:
        """Validate required arguments. Override if custom validation is needed."""
        required = self.parameters.get("required", [])
        for req in required:
            if req not in kwargs:
                raise ValueError(f"Missing required argument: {req}")

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """Execute the tool. Return a string or ToolResult."""
        ...


class ToolRegistry:
    """Central registry of available tools.

    Responsibilities:
    - Register tools by name
    - Look up tools by name
    - Enforce the allow-list guardrail
    - Provide OpenAI-format tool definitions for the LLM
    """

    def __init__(self, allow_list: Optional[set[str]] = None) -> None:
        self._tools: dict[str, Tool] = {}
        self._allow_list: Optional[set[str]] = allow_list

    def register(self, tool: Tool) -> None:
        """Add a tool to the registry."""
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """Remove a tool from the registry."""
        self._tools.pop(name, None)

    def get(self, name: str) -> Optional[Tool]:
        """Look up a tool by name. Returns None if not found."""
        return self._tools.get(name)

    def list(self) -> list[Tool]:
        """Return all registered tools."""
        return list(self._tools.values())

    def names(self) -> list[str]:
        """Return sorted list of registered tool names."""
        return sorted(self._tools.keys())

    def definitions(self, allowed_only: bool = True) -> list[ToolDefinition]:
        """Return OpenAI-format definitions for the tools.

        If ``allowed_only`` is True and an allow-list is configured, only
        tools in the allow-list are returned.
        """
        tools = self._tools.values()
        if allowed_only and self._allow_list is not None:
            tools = [t for t in tools if t.name in self._allow_list or not self._allow_list]
        return [t.to_definition() for t in tools]

    def is_allowed(self, tool_name: str) -> bool:
        """Check if a tool is permitted by the allow-list."""
        if self._allow_list is None or not self._allow_list:
            return True  # no restriction
        return tool_name in self._allow_list

    def infos(self) -> list[dict[str, Any]]:
        """Return summary info for all registered tools."""
        return [t.to_info() for t in self._tools.values()]
