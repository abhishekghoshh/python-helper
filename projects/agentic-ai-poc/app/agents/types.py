"""
Shared types for the agent system.

This module contains:
- ``AgentState`` — re-exported from schemas for convenience
- ``HitlApprover`` — protocol for human-in-the-loop approval
- ``AgentError`` — exception type for agent errors
"""

from __future__ import annotations

from enum import Enum
from typing import Protocol


class AgentState(str, Enum):
    """Lifecycle states of an agent run.

    Models the agent as an explicit state machine. Each transition
    is observable and traceable for debugging and learning.
    """

    IDLE = "IDLE"
    RUNNING = "RUNNING"
    THINKING = "THINKING"
    TOOL_CALLING = "TOOL_CALLING"
    OBSERVING = "OBSERVING"
    PLANNING = "PLANNING"
    REFLECTING = "REFLECTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    MAX_ITERATIONS = "MAX_ITERATIONS"
    STOPPED = "STOPPED"


class AgentError(Exception):
    """Raised when the agent encounters an unrecoverable error."""


class HitlApprover(Protocol):
    """Protocol for human-in-the-loop approval.

    Implementations decide whether a given tool call is allowed to proceed.
    In a real system this might be a web UI dialog, an email notification,
    or an API call to a human operator.
    """

    async def approve(self, tool_name: str, arguments: dict) -> bool:
        """Return True if the tool call is approved, False otherwise."""
        ...


class AlwaysApprove:
    """Default approver that approves everything (HITL disabled)."""

    async def approve(self, tool_name: str, arguments: dict) -> bool:
        return True


class AlwaysDeny:
    """Approver that denies everything (useful for testing guardrails)."""

    async def approve(self, tool_name: str, arguments: dict) -> bool:
        return False
