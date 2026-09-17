"""
Long-term memory — persistent facts and preferences across sessions.

Backed by SQLite (stdlib ``sqlite3``, no extra dependencies). Stores
key/value facts in namespaces so different kinds of memory (user
preferences, learned facts, session summaries) are isolated.

### Why SQLite?

- No external server required (file-based).
- Supports indexing and full-text-like search via SQL LIKE.
- ACID guarantees for concurrent access.
- Ships with Python — zero additional dependencies.

### Privacy note

Long-term memory may contain sensitive user data. In a production system
this store would need encryption at rest, access controls, and a retention
policy. These concerns are documented but not implemented here.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from typing import Any, Optional

from app.core.config import settings
from app.memory.base import LongTermMemory

logger = logging.getLogger(__name__)


class PersistentMemory(LongTermMemory):
    """SQLite-backed persistent memory store.

    Usage::

        mem = PersistentMemory()
        await mem.store("user_name", "Alice", namespace="preferences")
        name = await mem.retrieve("user_name", namespace="preferences")
        # → "Alice"
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or settings.memory_lt_db_path
        os.makedirs(os.path.dirname(os.path.abspath(self._db_path)) or ".", exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        """Create the facts table if it does not exist."""
        conn = self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_facts (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    namespace   TEXT NOT NULL,
                    key         TEXT NOT NULL,
                    value       TEXT NOT NULL,
                    created_at  TEXT DEFAULT (datetime('now')),
                    updated_at  TEXT DEFAULT (datetime('now')),
                    UNIQUE(namespace, key)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mem_value ON memory_facts(value)"
            )
            conn.commit()
        finally:
            conn.close()

    async def store(self, key: str, value: str, namespace: str = "default") -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO memory_facts (namespace, key, value)
                VALUES (?, ?, ?)
                ON CONFLICT(namespace, key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = datetime('now')
                """,
                (namespace, key, value),
            )
            conn.commit()
        finally:
            conn.close()
        logger.debug("Stored memory: ns=%s key=%s", namespace, key)

    async def retrieve(self, key: str, namespace: str = "default") -> Optional[str]:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT value FROM memory_facts WHERE namespace = ? AND key = ? "
                "ORDER BY updated_at DESC LIMIT 1",
                (namespace, key),
            ).fetchone()
            return row["value"] if row else None
        finally:
            conn.close()

    async def search(self, query: str, namespace: str = "default") -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            like_pattern = f"%{query}%"
            rows = conn.execute(
                "SELECT key, value, created_at FROM memory_facts "
                "WHERE namespace = ? AND (key LIKE ? OR value LIKE ?) "
                "ORDER BY created_at DESC LIMIT 20",
                (namespace, like_pattern, like_pattern),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    async def forget(self, key: str, namespace: str = "default") -> int:
        """Delete a memory by key. Returns number of rows deleted."""
        conn = self._connect()
        try:
            cursor = conn.execute(
                "DELETE FROM memory_facts WHERE namespace = ? AND key = ?",
                (namespace, key),
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    async def save(self) -> None:
        """No-op for SQLite — writes are auto-committed per-store."""
        pass
