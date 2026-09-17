"""
RAG Retriever tool — Retrieval-Augmented Generation as a tool.

This bridges the existing vector DB / embedding system with the agent's
tool-calling flow. Instead of a fixed RAG pipeline (retrieve → generate),
the **agent decides** when to retrieve and generates the answer via its
own LLM call.

### Flow

When the agent calls ``rag_query``:

    Agent → LLM decides to call rag_query tool
    rag_query → embeds question → searches vector DB → builds context
    → calls LLM with (system prompt + context + question)
    → returns grounded answer + source references

This is **RAG-as-a-tool** — the LLM controls *whether* and *when* to retrieve,
which is the key difference from a fixed RAG pipeline.

**Dependency note:** Qdrant and sentence-transformers are lazy-loaded.
If they are not installed, the tool returns a clear error so the agent
can fall back to web_search or a direct answer.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.core.config import settings
from app.llm.service import LLMInterface
from app.models.schemas import ConversationMessage, Role
from app.services.embedding import EmbeddingService
from app.services.vector_db import VectorDBService
from app.tools.base import Tool, ToolResult
from app.rag.chunking import chunk_document

logger = logging.getLogger(__name__)


class RAGRetrieverTool(Tool):
    """A tool that queries a vector database and generates a grounded answer.

    Depends on:
    - An ``LLMInterface`` instance (for answer generation)
    - An ``EmbeddingService`` instance (for query encoding)
    - A ``VectorDBService`` instance (for similarity search)
    """

    name = "rag_query"
    description = (
        "Retrieves relevant documents from a vector database and generates "
        "a grounded answer. Use this when the user asks about information "
        "that might be in the knowledge base or any ingested documents."
    )
    category = "rag"
    parameters = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question or query to search the knowledge base with.",
            }
        },
        "required": ["question"],
    }

    def __init__(
        self,
        llm_service: LLMInterface,
        embedding_service: Optional[EmbeddingService] = None,
        vector_db_service: Optional[VectorDBService] = None,
    ) -> None:
        self._llm_service = llm_service
        self._embedding_service = embedding_service or EmbeddingService()
        self._vector_db = vector_db_service or VectorDBService()

    async def execute(self, question: str, top_k: Optional[int] = None, **kwargs: Any) -> ToolResult:
        # 1. Check if vector DB is available
        if not self._vector_db.available:
            return ToolResult(
                self.name, "",
                success=False,
                error="Vector database is not available. Ingest documents first "
                      "and ensure Qdrant is running.",
            )
        if not self._embedding_service.available:
            return ToolResult(
                self.name, "",
                success=False,
                error="Embedding service is not available. Install sentence-transformers.",
            )

        k = top_k or settings.rag_top_k

        # 2. Embed the question
        query_embedding = await self._embedding_service.embed(question)

        # 3. Search the vector DB
        # Ensure the collection exists so querying before any ingestion degrades
        # gracefully to "no results" instead of raising a collection-not-found error.
        await self._vector_db.create_collection()
        hits = await self._vector_db.search(query_vector=query_embedding, top_k=k)

        if not hits:
            return ToolResult(
                self.name,
                "No relevant documents found in the knowledge base for this question.",
            )

        # 4. Build context from retrieved hits
        context_parts = []
        for i, hit in enumerate(hits, 1):
            context_parts.append(f"[Source {i}] {hit.text}")
        context = "\n\n".join(context_parts)

        # 5. Generate answer using the LLM
        system_prompt = (
            "You are a helpful assistant that answers questions based on the "
            "provided context. If you cannot answer from the context, say so "
            "honestly. Do not make up facts. Cite the source numbers."
        )
        messages = [
            ConversationMessage(role=Role.SYSTEM, content=system_prompt),
            ConversationMessage(
                role=Role.USER,
                content=f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:",
            ),
        ]

        response = await self._llm_service.generate(messages)
        answer = response.content or "I could not generate an answer from the retrieved context."

        # 6. Format result with sources
        sources_str = "\n".join(
            f"  [{i}] (score: {hit.score:.4f}) {hit.text[:200]}"
            for i, hit in enumerate(hits, 1)
        )
        result_text = f"{answer}\n\nSources:\n{sources_str}"

        return ToolResult(self.name, result_text)

    async def ingest(self, documents: list[str], ids: Optional[list[str]] = None) -> str:
        """Ingest raw text documents into the vector database.

        This is a setup method, not typically called by the agent at runtime.
        Returns a summary string.
        """
        from app.models.schemas import Document as DocumentSchema

        if not self._embedding_service.available:
            return "Embedding service not available."

        await self._vector_db.create_collection()

        doc_objs = []
        for i, text in enumerate(documents):
            doc_id = ids[i] if ids and i < len(ids) else f"doc-{i}"
            doc_objs.append(DocumentSchema(id=doc_id, content=text))

        all_chunks = []
        for doc in doc_objs:
            all_chunks.extend(chunk_document(doc))

        texts = [c.text for c in all_chunks]
        embeddings = await self._embedding_service.embed_many(texts)
        await self._vector_db.upsert_chunks(all_chunks, embeddings)

        return f"Ingested {len(documents)} documents → {len(all_chunks)} chunks stored."
