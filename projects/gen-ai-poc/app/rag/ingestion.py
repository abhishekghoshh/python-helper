"""
RAG step 1 — Document ingestion: parsing and chunking.

The flow:
    Documents → Chunking → Embeddings → Vector DB

This module handles the **Document → Chunking** step. It:
- Accepts raw text documents
- Splits them into overlapping chunks of configurable size
- Preserves metadata and document provenance

Chunking is critical because:
- LLM context windows are finite; we cannot pass entire documents
- Embedding models have token limits per input
- Smaller, focused chunks improve retrieval precision
"""

from __future__ import annotations

import logging
import uuid

from app.core.config import settings
from app.models.schemas import Chunk, Document

logger = logging.getLogger(__name__)


def chunk_text(
    text: str,
    chunk_size: int = settings.rag_chunk_size,
    chunk_overlap: int = settings.rag_chunk_overlap,
) -> list[str]:
    """Split text into overlapping chunks using a character-based strategy.

    A simple character-based splitter is used for learning clarity.
    In production you might use token-based splitting or
    sentence-aware splitters (e.g. from langchain or llama-index).

    Args:
        text: The full text to split.
        chunk_size: Maximum number of characters per chunk.
        chunk_overlap: Number of overlapping characters between adjacent chunks.

    Returns:
        List of text chunks.
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
        # Move forward, subtracting overlap to carry context into the next chunk
        start = end - chunk_overlap
        # If the step is non-positive, prevent an infinite loop
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

    chunks: list[Chunk] = []
    for i, text in enumerate(texts):
        chunks.append(
            Chunk(
                id=f"{document.id or str(uuid.uuid4())}_chunk_{i}",
                text=text,
                document_id=document.id or str(uuid.uuid4()),
                chunk_index=i,
                metadata=document.metadata,
            )
        )

    logger.info(
        "Chunked document '%s' into %d chunks (size=%d, overlap=%d)",
        document.id,
        len(chunks),
        settings.rag_chunk_size,
        settings.rag_chunk_overlap,
    )
    return chunks


async def ingest_documents(
    documents: list[Document],
    vector_db_service,
    embedding_service,
) -> tuple[int, int]:
    """Full ingestion pipeline: chunk → embed → store.

    Args:
        documents: Raw documents to ingest.
        vector_db_service: VectorDBService instance.
        embedding_service: EmbeddingService instance.

    Returns:
        Tuple of (documents_processed, chunks_created).
    """
    logger.info("Starting ingestion pipeline — %d documents", len(documents))

    await vector_db_service.create_collection()

    all_chunks: list[Chunk] = []
    for doc in documents:
        all_chunks.extend(chunk_document(doc))

    logger.info("Chunking complete — %d chunks created", len(all_chunks))

    # Embed all chunks in a single batch
    texts = [c.text for c in all_chunks]
    logger.info("Generating embeddings for %d chunks", len(texts))
    embeddings = await embedding_service.embed_many(texts)

    await vector_db_service.upsert_chunks(all_chunks, embeddings)

    logger.info(
        "Ingestion pipeline complete — %d docs, %d chunks, %d embeddings stored",
        len(documents),
        len(all_chunks),
        len(embeddings),
    )
    return len(documents), len(all_chunks)
