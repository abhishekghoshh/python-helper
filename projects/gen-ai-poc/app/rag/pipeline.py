"""
RAG Pipeline — orchestrates the complete Retrieval-Augmented Generation flow.

This module ties together ingestion, retrieval, and generation into a single
cohesive pipeline. It is the "glue" that learners can read to understand how
all the GenAI components connect:

    Documents
        ↓  (ingestion: chunking)
    Chunks
        ↓  (embeddings: text → vectors)
    Embeddings
        ↓  (vector DB: storage + indexing)
    Vector DB
        ↓  (retrieval: similarity search)
    Retrieved Context
        ↓  (generation: prompt + LLM)
    Generated Response
"""

from __future__ import annotations

import logging

from app.embeddings.service import EmbeddingService, embedding_service
from app.llm.service import LLMService, llm_service
from app.models.schemas import Document, RAGRequest, RAGResponse, SearchHit
from app.rag.generation import generate_answer
from app.rag.ingestion import ingest_documents
from app.rag.retrieval import retrieve_context
from app.services.vectordb import VectorDBService, vector_db

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Complete RAG pipeline: ingest → retrieve → generate."""

    def __init__(
        self,
        llm_service: LLMService,
        embedding_service: EmbeddingService,
        vector_db_service: VectorDBService,
    ) -> None:
        self.llm = llm_service
        self.embedding_service = embedding_service
        self.vector_db = vector_db_service

    async def ingest(self, documents: list[Document]) -> tuple[int, int]:
        """Ingest documents into the vector database.

        Returns:
            (documents_processed, chunks_created)
        """
        logger.info("Ingesting %d documents", len(documents))
        result = await ingest_documents(documents, self.vector_db, self.embedding_service)
        docs_processed, chunks_created = result
        logger.info(
            "Ingestion complete — %d docs, %d chunks",
            docs_processed,
            chunks_created,
        )
        return result

    async def retrieve(
        self,
        question: str,
        top_k: int | None = None,
        filter_condition: dict | None = None,
    ) -> list[SearchHit]:
        """Retrieve relevant context for a question."""
        if top_k:
            logger.info(
                "Retrieving context — question=%s, top_k=%d",
                question[:60],
                top_k,
            )
        return await retrieve_context(
            question,
            self.vector_db,
            self.embedding_service,
            top_k=top_k,
            filter_condition=filter_condition,
        )

    async def query(self, request: RAGRequest) -> RAGResponse:
        """Full RAG query: retrieve → generate.

        Args:
            request: RAGRequest containing the question and optional params.

        Returns:
            RAGResponse with the generated answer and source chunks.
        """
        logger.info("RAG query received — question=%s", request.question[:80])

        # Step 1: Retrieve relevant context from the vector DB
        hits = await self.retrieve(
            question=request.question,
            top_k=request.top_k,
        )

        # Step 2: Generate an answer using the LLM with retrieved context
        response = await generate_answer(
            question=request.question,
            hits=hits,
            llm_service=self.llm,
            model=request.model,
            temperature=request.temperature,
        )

        logger.info(
            "RAG query complete — sources=%d, answer_length=%d",
            len(response.sources),
            len(response.answer),
        )
        return response


# Module-level singleton using the shared service instances
rag_pipeline = RAGPipeline(
    llm_service=llm_service,
    embedding_service=embedding_service,
    vector_db_service=vector_db,
)
