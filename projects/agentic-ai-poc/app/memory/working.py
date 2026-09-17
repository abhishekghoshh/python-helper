"""
Working memory — task-scoped scratchpad.

During a single agent run the agent may need to track:
- The current goal / plan
- Which sub-tasks are complete
- Intermediate results
- Notes for itself

This is a simple in-memory key/value store scoped to one agent run.
It is reset when a new task begins.
"""

from __future__ import annotations

from typing import Any

from app.memory.base import WorkingMemory


class InMemoryWorkingMemory(WorkingMemory):
    """A simple dict-backed working memory (task-scoped, not persisted)."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def has(self, key: str) -> bool:
        return key in self._data

    def unset(self, key: str) -> None:
        self._data.pop(key, None)

    def clear(self) -> None:
        self._data.clear()

    def all(self) -> dict[str, Any]:
        """Return a copy of all stored data."""
        return dict(self._data)
