"""Text chunking utilities for document ingestion.

Chunking splits long documents into smaller pieces so that:
1. Each chunk fits within an embedding model's context window (e.g., 256 tokens)
2. Search results are more precise (returning relevant passages, not entire documents)
3. More vectors are stored, improving retrieval granularity
"""

import logging
import re

logger = logging.getLogger(__name__)


class ChunkSizeError(ValueError):
    """Raised when chunk_size or chunk_overlap have invalid values."""


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[str]:
    """Split text into overlapping chunks.

    Uses a recursive splitting strategy:
    1. Split by paragraphs (double newlines)
    2. For paragraphs exceeding chunk_size, split by sentences
    3. Greedily accumulate paragraphs/sentences into chunks
    4. Apply character-based overlap between consecutive chunks

    Args:
        text: The input text to chunk.
        chunk_size: Maximum number of characters per chunk.
        chunk_overlap: Number of overlapping characters between consecutive chunks.

    Returns:
        A list of text chunks (strings), each up to chunk_size characters.
    """
    if not text.strip():
        logger.debug("chunk_text received empty text; returning []")
        return []

    if chunk_size <= 0:
        raise ChunkSizeError("chunk_size must be greater than 0")

    if chunk_overlap >= chunk_size:
        raise ChunkSizeError("chunk_overlap must be less than chunk_size")

    logger.debug("Chunking text (%d chars) with chunk_size=%d, overlap=%d", len(text), chunk_size, chunk_overlap)

    # Step 1: Split into paragraphs
    paragraphs = re.split(r"\n\s*\n", text.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        return []

    # Step 2: Split large paragraphs by sentences, then accumulate
    segments: list[str] = []
    for para in paragraphs:
        if len(para) <= chunk_size:
            segments.append(para)
        else:
            # Split by sentence boundaries
            sentences = re.split(r"(?<=[.!?])\s+", para)
            sentences = [s.strip() for s in sentences if s.strip()]
            segments.extend(sentences)

    # Step 3: Greedily accumulate segments into chunks
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length = 0

    for segment in segments:
        if not segment:
            continue

        if current_length + len(segment) + 1 > chunk_size and current_chunk:
            # Flush current chunk
            chunk_text_str = " ".join(current_chunk)
            chunks.append(chunk_text_str)

            # Apply overlap: carry over the last part of the previous chunk
            if chunk_overlap > 0:
                overlap_text = chunk_text_str[-chunk_overlap:]
                current_chunk = [overlap_text]
                current_length = len(overlap_text)
            else:
                current_chunk = []
                current_length = 0

        current_chunk.append(segment)
        current_length += len(segment) + 1

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks
