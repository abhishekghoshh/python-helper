"""Tests for the chunking module."""

import pytest

from app.models.schemas import Document
from app.rag.ingestion import chunk_document, chunk_text


class TestChunkText:
    def test_short_text_returns_single_chunk(self):
        text = "This is a short text."
        chunks = chunk_text(text, chunk_size=500, chunk_overlap=100)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_is_split(self):
        text = "A" * 1000
        chunks = chunk_text(text, chunk_size=500, chunk_overlap=100)
        assert len(chunks) > 1
        # Each chunk (except possibly the last) should be chunk_size long
        for chunk in chunks[:-1]:
            assert len(chunk) == 500

    def test_overlap_is_applied(self):
        text = "A" * 1000
        chunks = chunk_text(text, chunk_size=500, chunk_overlap=100)
        # Second chunk should overlap with first by 100 chars
        assert chunks[1].startswith("A" * 100)

    def test_overlap_must_be_smaller_than_chunk_size(self):
        text = "A" * 1000
        with pytest.raises(ValueError, match="chunk_overlap must be smaller"):
            chunk_text(text, chunk_size=100, chunk_overlap=100)

    def test_empty_text(self):
        chunks = chunk_text("", chunk_size=500, chunk_overlap=100)
        assert len(chunks) == 1
        assert chunks[0] == ""


class TestChunkDocument:
    def test_chunk_document_returns_chunks(self):
        doc = Document(
            id="doc_001",
            content="This is a short document about AI and machine learning concepts." * 20,
            metadata={"category": "education"},
        )
        chunks = chunk_document(doc)
        assert len(chunks) > 0
        assert all(c.document_id == "doc_001" for c in chunks)
        assert all(c.chunk_index >= 0 for c in chunks)
        assert all(c.metadata == {"category": "education"} for c in chunks)

    def test_chunk_ids_are_unique(self):
        doc = Document(content="A" * 2000, metadata={})
        chunks = chunk_document(doc)
        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_chunk_indices_are_sequential(self):
        doc = Document(content="A" * 2000, metadata={})
        chunks = chunk_document(doc)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))
