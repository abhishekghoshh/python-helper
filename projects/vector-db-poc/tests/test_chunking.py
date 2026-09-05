"""Unit tests for the document chunking utility.

These tests run without any external services (no Qdrant, no model loading).
"""

import pytest

from app.services.chunking import chunk_text, ChunkSizeError


def test_single_paragraph_small_text():
    """Text shorter than chunk_size returns a single chunk."""
    text = "This is a short sentence."
    chunks = chunk_text(text, chunk_size=500, chunk_overlap=0)
    assert chunks == [text]


def test_single_paragraph_large_text():
    """Text longer than chunk_size is split."""
    text = "This is a long paragraph. " * 20
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=0)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 100


def test_chunk_overlap():
    """Overlapping chunks share text at the boundary."""
    text = "The quick brown fox jumps over the lazy dog. " * 10
    chunks = chunk_text(text, chunk_size=50, chunk_overlap=10)
    assert len(chunks) > 1
    # The overlap text should appear at the end of one chunk and the start
    # of the next.
    for i in range(len(chunks) - 1):
        assert chunks[i + 1].startswith(chunks[i][-10:])


def test_multiple_paragraphs_preserved():
    """Paragraph boundaries are respected."""
    text = "First paragraph. " + "x" * 200 + "\n\n" + "Second paragraph. " + "y" * 200
    chunks = chunk_text(text, chunk_size=50, chunk_overlap=5)
    # Should find chunks referencing both paragraphs
    assert any("First paragraph" in c for c in chunks)
    assert any("Second paragraph" in c for c in chunks)


def test_chunk_size_zero():
    """A chunk_size of zero raises ChunkSizeError."""
    with pytest.raises(ChunkSizeError):
        chunk_text("hello", chunk_size=0)


def test_chunk_overlap_too_large():
    """An overlap >= chunk_size raises ChunkSizeError."""
    with pytest.raises(ChunkSizeError):
        chunk_text("hello world", chunk_size=10, chunk_overlap=10)


def test_empty_text():
    """Empty text returns an empty list."""
    assert chunk_text("", chunk_size=100) == []


def test_exact_fit():
    """Text that exactly fits in one chunk returns a single chunk."""
    text = "a" * 100
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=10)
    assert chunks == [text]


def test_sentence_boundary_not_broken():
    """Chunks break at sentence boundaries, not mid-sentence (when possible)."""
    text = "First sentence. Second sentence. Third sentence."
    chunks = chunk_text(text, chunk_size=15, chunk_overlap=0)
    # Each chunk should start at a sentence boundary (not mid-sentence)
    for chunk in chunks:
        assert chunk.endswith(".") or chunk == text
