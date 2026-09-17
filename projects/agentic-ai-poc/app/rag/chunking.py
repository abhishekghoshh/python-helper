"""
RAG chunking utilities — split documents into overlapping chunks.

Adapted from the existing gen-ai-poc ingestion module.
A simple character-based splitter is used for learning clarity.
"""

from __future__ import annotations

import uuid

from app.core.config import settings
from app.models.schemas import Chunk, Document


def chunk_text(
    text: str,
    chunk_size: int = settings.rag_chunk_size,
    chunk_overlap: int = settings.rag_chunk_overlap,
) -> list[str]:
    """Split text into overlapping chunks using a character-based strategy.

    A simple character-based splitter is used for learning clarity.
    In production you might use token-based splitting or
    sentence-aware splitters (e.g. from langchain or llama-index).
    """
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - chunk_overlap
        if start <= 0:
            break
    return chunks


def chunk_document(document: Document) -> list[Chunk]:
    """Convert a Document into a list of Chunk objects with metadata."""
    texts = chunk_text(
        document.content,
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
    )
    doc_id = document.id or str(uuid.uuid4())
    chunks: list[Chunk] = []
    for i, text in enumerate(texts):
        chunks.append(Chunk(
            id=f"{doc_id}_chunk_{i}",
            text=text,
            document_id=doc_id,
            chunk_index=i,
            metadata=document.metadata,
        ))
    return chunks
