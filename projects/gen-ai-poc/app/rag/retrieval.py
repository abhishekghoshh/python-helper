"""
RAG step 2 — Retrieval: similarity search and context construction.

The flow:
    Query → Query Embedding → Vector Search → Retrieved Context

This module:
- Embeds a user's question using the same embedding model used at ingest time
- Performs a similarity search in the vector DB (approximate nearest-neighbor)
- Retrieves the top-K most relevant chunks
- Constructs a context string to feed into the LLM prompt

Key concepts demonstrated:
- Query embedding must use the **same** model/dimensions as document embeddings
- **top-k** controls how many chunks are retrieved
- Distance/similarity scores rank results
- Retrieved context is injected into the prompt (the "augmentation" in RAG)
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.models.schemas import SearchHit

logger = logging.getLogger(__name__)


async def retrieve_context(
    question: str,
    vector_db_service,
    embedding_service,
    top_k: int | None = None,
    filter_condition: dict | None = None,
) -> list[SearchHit]:
    """Embed a query and retrieve the most similar document chunks.

    Args:
        question: The user's question/query.
        vector_db_service: VectorDBService instance.
        embedding_service: EmbeddingService instance.
        top_k: Override for number of results (defaults to settings.rag_top_k).
        filter_condition: Optional metadata filter for hybrid search.

    Returns:
        List of SearchHit objects, ranked by similarity score.
    """
    k = top_k or settings.rag_top_k

    logger.info("Retrieving context — question=%s, top_k=%d", question[:60], k)

    # Embed the query using the same model as the documents
    query_embedding = await embedding_service.embed(question)

    # Search the vector DB for similar vectors
    hits = await vector_db_service.search(
        query_vector=query_embedding,
        top_k=k,
        filter_condition=filter_condition,
    )

    logger.info("Retrieved %d hits for query (k=%d)", len(hits), k)
    return hits


def build_context(hits: list[SearchHit], max_chars: int = 3000) -> str:
    """Construct a context string from retrieved search hits.

    Truncates to max_chars to stay within LLM context limits.

    Args:
        hits: Retrieved search hits.
        max_chars: Maximum total characters for the context block.

    Returns:
        A formatted context string.
    """
    if not hits:
        return ""

    separator = "\n---\n"
    context_parts: list[str] = []
    total = 0

    for i, hit in enumerate(hits):
        snippet = f"[Source {i + 1}] (score: {hit.score:.4f})\n{hit.text}"
        if total + len(snippet) > max_chars:
            remaining = max_chars - total
            if remaining > 100:  # only add if enough room
                snippet = snippet[:remaining]
            else:
                break
        context_parts.append(snippet)
        total += len(snippet)

    return separator.join(context_parts)


def build_rag_prompt(question: str, context: str) -> str:
    """Build the final prompt that combines context and the user's question.

    The prompt structure demonstrates the RAG pattern:
    1. System message — defines the assistant's role and instructions
    2. Retrieved context — the knowledge from the vector DB
    3. User question — the actual query

    This is a plain string for transparency. In the API layer this becomes
    a ChatMessage with appropriate roles.
    """
    system_prompt = (
        "You are a helpful assistant that answers questions based on "
        "the provided context.\n"
        "If you cannot answer the question from the context, say so honestly.\n"
        "Do not make up facts that are not supported by the context.\n"
        "Cite the source numbers from the context when you use them."
    )

    if context:
        user_prompt = f"""Context:
{context}

Question: {question}

Answer:"""
    else:
        system_prompt = (
            "You are a helpful assistant. Answer the question " "to the best of your ability."
        )
        user_prompt = f"Question: {question}\n\nAnswer:"

    return f"{system_prompt}\n\n{user_prompt}"
