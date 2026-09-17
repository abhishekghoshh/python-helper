"""
Observability — execution tracing for the agent.

Every important event in an agent run (LLM calls, tool calls, state
transitions, errors) is recorded as a **TraceEvent**. Together these
form an **ExecutionTrace** that answers the question:

  "What happened, in what order, and why?"

This is essential for debugging agents (wrong tool selection, infinite
loops, slow calls) and for the learning objective — every decision is
visible and inspectable.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class EventType(str, Enum):
    """Categories of traceable events."""

    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    STATE_CHANGE = "state_change"
    LLM_CALL = "llm_call"
    LLM_RESPONSE = "llm_response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    TOOL_ERROR = "tool_error"
    OBSERVATION = "observation"
    PLANNING = "planning"
    REFLECTION = "reflection"
    HITL_APPROVAL = "hitl_approval"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class TraceEvent:
    """A single event in the agent execution trace."""

    event_type: EventType
    timestamp: float = field(default_factory=time.time)
    # Wall-clock elapsed since the trace started (seconds).
    elapsed: float = 0.0
    # The iteration / step number this event belongs to.
    step: int = 0
    # Free-form event data (e.g. tool name, llm model, error message).
    data: dict[str, Any] = field(default_factory=dict)
    # Human-readable label for the event.
    label: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "elapsed": round(self.elapsed, 4),
            "step": self.step,
            "label": self.label,
            "data": self.data,
        }


class ExecutionTrace:
    """Collects and serializes trace events for an agent run.

    Usage::

        trace = ExecutionTrace()
        trace.log(EventType.LLM_CALL, model="gpt-4o-mini", tokens=123)
        trace.log(EventType.TOOL_CALL, tool_name="calculator", args={"expression": "1+1"})
        # ...
        print(trace.to_dict())
    """

    def __init__(self) -> None:
        self._events: list[TraceEvent] = []
        self._start: float = time.time()
        self._step: int = 0

    @property
    def events(self) -> list[TraceEvent]:
        return list(self._events)

    def set_step(self, step: int) -> None:
        """Set the current step counter for subsequent events."""
        self._step = step

    def log(
        self,
        event_type: EventType,
        label: Optional[str] = None,
        step: Optional[int] = None,
        **data: Any,
    ) -> TraceEvent:
        """Record a trace event."""
        event = TraceEvent(
            event_type=event_type,
            timestamp=time.time(),
            elapsed=time.time() - self._start,
            step=step if step is not None else self._step,
            data=data,
            label=label,
        )
        self._events.append(event)
        return event

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full trace as a dictionary."""
        return {
            "start_time": self._start,
            "duration_seconds": round(time.time() - self._start, 4),
            "event_count": len(self._events),
            "events": [e.to_dict() for e in self._events],
        }

    def to_log_lines(self) -> list[str]:
        """Render the trace as human-readable log lines (for CLI / learning display)."""
        lines: list[str] = []
        for e in self._events:
            ts = f"[{e.elapsed:7.3f}s]"
            tag = f"{e.event_type.value:>14}"
            step_str = f"step={e.step}" if e.step else ""
            label_str = f"{e.label}" if e.label else ""
            parts = [ts, tag, step_str, label_str]
            parts = [p for p in parts if p]
            line = " ".join(parts)
            if e.data:
                data_str = ", ".join(f"{k}={v}" for k, v in e.data.items())
                line += f" | {data_str}"
            lines.append(line)
        return lines

    def summary(self) -> str:
        """A one-line summary of the trace."""
        counts: dict[str, int] = {}
        for e in self._events:
            counts[e.event_type.value] = counts.get(e.event_type.value, 0) + 1
        return f"Trace: {len(self._events)} events — {counts}"
