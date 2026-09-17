"""
RAG API endpoints — demonstrate the complete Retrieval-Augmented Generation flow.

Endpoints:
- POST /rag/ingest     — Ingest documents into the vector database
- POST /rag/search     — Search documents (similarity search)
- POST /rag/query      — Full RAG: retrieve context + generate answer
- GET  /rag/demo       — Demonstration without LLM calls (for learning)

The RAG flow:
    Documents → Chunking → Embeddings → Vector DB → Similarity Search
        → Retrieved Context → Prompt + Context → LLM → Answer
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    Document,
    IngestResponse,
    RAGRequest,
    RAGResponse,
    SearchResponse,
)
from app.rag.pipeline import rag_pipeline
from app.services.vectordb import vector_db

router = APIRouter(prefix="/rag", tags=["RAG"])
logger = logging.getLogger(__name__)


@router.post("/ingest", response_model=IngestResponse)
async def ingest_documents_api(
    documents: list[Document],
) -> IngestResponse:
    """Ingest documents into the vector database.

    Each document is:
    1. **Chunked** into overlapping pieces
    2. **Embedded** into dense vectors
    3. **Stored** in the vector database with metadata

    This enables semantic search — finding documents by meaning, not keywords.
    """
    if not documents:
        raise HTTPException(status_code=400, detail="No documents provided")

    logger.info("Ingestion request — %d documents", len(documents))
    docs_processed, chunks_created = await rag_pipeline.ingest(documents)
    logger.info(
        "Ingestion complete — %d docs processed, %d chunks created",
        docs_processed,
        chunks_created,
    )

    return IngestResponse(
        documents_processed=docs_processed,
        chunks_created=chunks_created,
        collection=vector_db.collection,
    )


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: RAGRequest,
    top_k: int = Query(default=None, ge=1, le=50),
) -> SearchResponse:
    """Perform a similarity search over ingested documents.

    The query is embedded and matched against stored embeddings
    using approximate nearest-neighbor search. Returns ranked results
    with similarity scores.
    """
    k = top_k or request.top_k
    logger.info("Search request — question=%s, top_k=%d", request.question[:60], k)
    try:
        hits = await rag_pipeline.retrieve(
            question=request.question,
            top_k=k,
        )
        logger.info("Search returned %d results", len(hits))
    except Exception as e:
        logger.error("Search failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e)) from e

    return SearchResponse(
        query=request.question,
        hits=hits,
        collection=vector_db.collection,
    )


@router.post("/query", response_model=RAGResponse)
async def rag_query(request: RAGRequest) -> RAGResponse:
    """Full RAG pipeline: retrieve context and generate an answer.

    This endpoint demonstrates the complete flow:
    1. Embed the user's question
    2. Search the vector DB for similar documents (top-k retrieval)
    3. Construct a prompt with retrieved context
    4. Call the LLM to generate a grounded response
    """
    logger.info("RAG query request — question=%s", request.question[:60])
    try:
        response = await rag_pipeline.query(request)
        logger.info(
            "RAG query success — answer_length=%d, sources=%d",
            len(response.answer),
            len(response.sources),
        )
        return response
    except Exception as e:
        logger.error("RAG query failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/demo")
async def rag_demo(
    question: str = Query(..., description="Question to demonstrate RAG with"),
    top_k: int = Query(default=5, ge=1, le=20),
) -> dict:
    """Demonstrate the RAG flow without calling an LLM.

    This endpoint shows:
    - The prompt that would be sent to the LLM
    - The retrieved context chunks
    - Similarity scores

    Useful for learning how RAG works without requiring an API key.
    """
    from app.rag.retrieval import build_context, build_rag_prompt

    logger.info("RAG demo — question=%s, top_k=%d", question[:60], top_k)
    try:
        hits = await rag_pipeline.retrieve(question=question, top_k=top_k)
    except Exception as e:
        logger.warning("RAG demo — vector DB unavailable: %s", e)
        # Vector DB may not be available — return info anyway
        hits = []
    context = build_context(hits)
    prompt = build_rag_prompt(question, context)

    return {
        "question": question,
        "retrieved_chunks": [
            {
                "text": h.text[:200] + "..." if len(h.text) > 200 else h.text,
                "score": round(float(h.score), 6),
                "metadata": h.metadata,
            }
            for h in hits
        ],
        "context": context[:500] + "..." if len(context) > 500 else context,
        "prompt": prompt,
        "note": "The prompt above is what would be sent to the LLM. The LLM service "
        "is not called here so no API key is needed.",
    }
