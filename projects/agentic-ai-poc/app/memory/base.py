"""
Memory base classes.

Defines the abstract interfaces for the three kinds of memory an agent
needs:

- **Short-term** (``ShortTermMemory``): conversation history for the current
  session — kept in RAM, trimmed to fit the context window.
- **Working** (``WorkingMemory``): a scratchpad for intermediate task state
  — arbitrary key/value data scoped to the current task.
- **Long-term** (``LongTermMemory``): persistent facts and preferences stored
  across sessions — backed by a file on disk.

Each subclass implements a minimal, explicit interface so the agent loop
can use them without knowing the storage details.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from app.models.schemas import ConversationMessage, Role


class ShortTermMemory(ABC):
    """Conversation history for the current session."""

    @abstractmethod
    def add(self, message: ConversationMessage) -> None:
        """Append a message to the conversation history."""
        ...

    @abstractmethod
    def get_messages(self) -> list[ConversationMessage]:
        """Return all messages (possibly trimmed)."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear the conversation history."""
        ...


class WorkingMemory(ABC):
    """Task-scoped scratchpad for intermediate state."""

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Store a key/value pair."""
        ...

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value by key."""
        ...

    @abstractmethod
    def has(self, key: str) -> bool:
        """Check if a key exists."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all working memory."""
        ...


class LongTermMemory(ABC):
    """Persistent memory across sessions."""

    @abstractmethod
    async def store(self, key: str, value: str, namespace: str = "default") -> None:
        """Store a fact in persistent memory."""
        ...

    @abstractmethod
    async def retrieve(self, key: str, namespace: str = "default") -> Optional[str]:
        """Retrieve a fact by key."""
        ...

    @abstractmethod
    async def search(self, query: str, namespace: str = "default") -> list[dict[str, Any]]:
        """Search for facts matching a query."""
        ...

    @abstractmethod
    async def save(self) -> None:
        """Persist memory to disk."""
        ...
