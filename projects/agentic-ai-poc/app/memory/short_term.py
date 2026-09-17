"""
Short-term memory — conversation buffer.

Stores the conversation history for the current session in RAM. Truncates
from the oldest end when the total character count exceeds the configured
limit, keeping the most recent messages (which are usually the most relevant).

This maps to what LLM application developers call the "context window" or
"message history" — everything the LLM can see in the current conversation.
"""

from __future__ import annotations

import logging
from collections import deque

from app.core.config import settings
from app.models.schemas import ConversationMessage, Role
from app.memory.base import ShortTermMemory

logger = logging.getLogger(__name__)


class ConversationBuffer(ShortTermMemory):
    """A rolling conversation buffer with token-aware truncation.

    The buffer keeps messages as a deque. When the total character count
    exceeds ``max_chars`` (from settings), the oldest messages are removed
    from the front — preserving recent context while staying within
    the model's context window.
    """

    def __init__(self, max_chars: int | None = None) -> None:
        self._max_chars = max_chars or settings.memory_max_history_chars
        self._messages: deque[ConversationMessage] = deque()

    def add(self, message: ConversationMessage) -> None:
        self._messages.append(message)
        self._trim()

    def add_many(self, messages: list[ConversationMessage]) -> None:
        for msg in messages:
            self._messages.append(msg)
        self._trim()

    def get_messages(self) -> list[ConversationMessage]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()

    @property
    def max_chars(self) -> int:
        return self._max_chars

    def _char_count(self) -> int:
        return sum(len(msg.content or "") for msg in self._messages)

    def _trim(self) -> None:
        """Remove oldest messages until under the char limit."""
        while self._messages and self._char_count() > self._max_chars:
            removed = self._messages.popleft()
            logger.debug("Trimmed message from history (role=%s)", removed.role.value)

    def add_user(self, content: str) -> None:
        """Convenience: add a user message."""
        self.add(ConversationMessage(role=Role.USER, content=content))

    def add_assistant(self, content: str | None = None) -> None:
        """Convenience: add an assistant message."""
        self.add(ConversationMessage(role=Role.ASSISTANT, content=content))
