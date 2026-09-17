"""
Calculator tool — evaluates mathematical expressions.

This tool demonstrates a **safe-ish** calculator: it uses Python's ``eval``
but with ``__builtins__`` stripped and only a restricted set of ``math``
functions exposed. This is a common pattern for agent calculator tools.

Security note: ``eval`` is inherently risky. For a learning POC this is
acceptable because:
1. The namespace is heavily restricted (no builtins, no imports).
2. The tool is only invoked when the LLM explicitly calls it.
3. Guardrails (allow-list, timeouts) limit exposure.

In production you would use ``numexpr``, ``asteval``, or a dedicated
expression parser. This is documented in `docs/agentic-ai/tools.md`.
"""

from __future__ import annotations

import math
from typing import Any

from app.tools.base import Tool, ToolResult

# A restricted namespace: only math functions, no builtins, no imports.
_SAFE_NAMES: dict[str, Any] = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "pow": pow,
    "sum": sum,
    # Common math functions
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "pi": math.pi,
    "e": math.e,
    "log": math.log,
    "log10": math.log10,
    "floor": math.floor,
    "ceil": math.ceil,
    "factorial": math.factorial,
}


class CalculatorTool(Tool):
    """A calculator that evaluates mathematical expressions."""

    name = "calculator"
    description = (
        "A calculator that evaluates mathematical expressions and returns the numeric result. "
        "Use this for any arithmetic, algebra, or numerical computation. "
        "The expression must use Python-compatible syntax."
    )
    category = "math"
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "The mathematical expression to evaluate, e.g. '2 + 2 * 10' or 'sqrt(144) + 5'.",
            }
        },
        "required": ["expression"],
    }

    async def execute(self, expression: str, **kwargs: Any) -> ToolResult:
        # Evaluate with a restricted namespace
        result = eval(expression, {"__builtins__": {}}, _SAFE_NAMES)
        # Convert to a clean string representation
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return ToolResult(self.name, str(result))

    def _validate_args(self, kwargs: dict[str, Any]) -> None:
        super()._validate_args(kwargs)
        if not kwargs.get("expression") or not kwargs["expression"].strip():
            raise ValueError("expression must not be empty")
