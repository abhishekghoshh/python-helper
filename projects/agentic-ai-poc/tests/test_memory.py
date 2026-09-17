"""Tests for memory modules."""

import pytest
import tempfile
import os

from app.memory.short_term import ConversationBuffer
from app.memory.working import InMemoryWorkingMemory
from app.memory.long_term import PersistentMemory
from app.models.schemas import ConversationMessage, Role


class TestConversationBuffer:
    def test_add_and_retrieve(self):
        buf = ConversationBuffer(max_chars=10000)
        buf.add_user("Hello")
        buf.add_assistant("Hi there!")
        msgs = buf.get_messages()
        assert len(msgs) == 2
        assert msgs[0].role == Role.USER
        assert msgs[1].role == Role.ASSISTANT

    def test_truncation(self):
        buf = ConversationBuffer(max_chars=50)
        # Add many messages — old ones should be trimmed
        for i in range(20):
            buf.add(ConversationMessage(role=Role.USER, content=f"Message number {i} " * 3))
        msgs = buf.get_messages()
        total_chars = sum(len(m.content or "") for m in msgs)
        assert total_chars <= 50 + 100  # small margin for the last message

    def test_clear(self):
        buf = ConversationBuffer()
        buf.add_user("test")
        assert len(buf.get_messages()) == 1
        buf.clear()
        assert len(buf.get_messages()) == 0

    def test_add_many(self):
        buf = ConversationBuffer(max_chars=10000)
        buf.add_many([
            ConversationMessage(role=Role.SYSTEM, content="You are helpful"),
            ConversationMessage(role=Role.USER, content="Hi"),
        ])
        assert len(buf.get_messages()) == 2


class TestWorkingMemory:
    def test_set_get(self):
        wm = InMemoryWorkingMemory()
        wm.set("goal", "calculate sum")
        assert wm.get("goal") == "calculate sum"
        assert wm.has("goal")

    def test_default(self):
        wm = InMemoryWorkingMemory()
        assert wm.get("missing", "default") == "default"

    def test_unset(self):
        wm = InMemoryWorkingMemory()
        wm.set("key", "value")
        wm.unset("key")
        assert not wm.has("key")

    def test_clear(self):
        wm = InMemoryWorkingMemory()
        wm.set("a", 1)
        wm.set("b", 2)
        wm.clear()
        assert not wm.has("a")
        assert not wm.has("b")


class TestPersistentMemory:
    @pytest.fixture
    def mem(self, tmp_path):
        db_path = str(tmp_path / "test_memory.db")
        return PersistentMemory(db_path=db_path)

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, mem):
        await mem.store("user_pref", "dark_mode", namespace="preferences")
        result = await mem.retrieve("user_pref", namespace="preferences")
        assert result == "dark_mode"

    @pytest.mark.asyncio
    async def test_retrieve_missing(self, mem):
        result = await mem.retrieve("nonexistent", namespace="preferences")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_overwrites(self, mem):
        await mem.store("key", "value1", namespace="test")
        await mem.store("key", "value2", namespace="test")
        result = await mem.retrieve("key", namespace="test")
        assert result == "value2"

    @pytest.mark.asyncio
    async def test_search(self, mem):
        await mem.store("capital", "Paris is the capital of France", namespace="facts")
        await mem.store("currency", "Euro is the currency", namespace="facts")
        results = await mem.search("capital", namespace="facts")
        assert len(results) >= 1
        assert any("Paris" in r["value"] for r in results)

    @pytest.mark.asyncio
    async def test_namespace_isolation(self, mem):
        await mem.store("key", "value_a", namespace="ns1")
        await mem.store("key", "value_b", namespace="ns2")
        assert await mem.retrieve("key", namespace="ns1") == "value_a"
        assert await mem.retrieve("key", namespace="ns2") == "value_b"

    @pytest.mark.asyncio
    async def test_forget(self, mem):
        await mem.store("temp", "value", namespace="test")
        await mem.forget("temp", namespace="test")
        assert await mem.retrieve("temp", namespace="test") is None
