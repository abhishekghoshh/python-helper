from fastapi import APIRouter, Depends, HTTPException, status
from qdrant_client import QdrantClient

import logging

from app.config import settings
from app.models.schemas import (
    DocumentCreate,
    DocumentListItem,
    DocumentResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    HealthResponse,
    ListDocumentsResponse,
    SearchHit,
    SearchRequest,
    SearchResponse,
)
from app.services.chunking import chunk_text
from app.services.embedding import EmbeddingService
from app.services.vector_db import VectorDBService

logger = logging.getLogger(__name__)

router = APIRouter()

_embedding_service: EmbeddingService | None = None
_vdb_service: VectorDBService | None = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(settings.embedding_model)
    return _embedding_service


def get_vector_db_service() -> VectorDBService:
    global _vdb_service
    if _vdb_service is None:
        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        _vdb_service = VectorDBService(
            client, settings.collection_name, settings.embedding_dim,
            distance=settings.qdrant_distance,
        )
    return _vdb_service


@router.get("/health", response_model=HealthResponse)
def health(emb: EmbeddingService = Depends(get_embedding_service)):
    logger.info("Health check requested")
    try:
        dim = emb.dimension
    except Exception:
        dim = 0
    # Probe Qdrant to report actual connectivity status
    try:
        vdb = get_vector_db_service()
        vdb.client.get_collections()
        qdrant_status = "connected"
    except Exception as exc:
        logger.warning("Qdrant health check failed: %s", exc)
        qdrant_status = "disconnected"
    return HealthResponse(
        status="ok",
        qdrant=qdrant_status,
        embedding_model=settings.embedding_model,
        embedding_dim=dim,
    )


@router.post("/embed", response_model=EmbeddingResponse)
def embed(
    request: EmbeddingRequest,
    emb: EmbeddingService = Depends(get_embedding_service),
):
    logger.info("Embedding request: %d chars", len(request.text))
    vector = emb.embed(request.text)
    return EmbeddingResponse(vector=vector, dimension=len(vector))


@router.post("/documents/", status_code=status.HTTP_201_CREATED, response_model=DocumentResponse)
def add_document(
    doc: DocumentCreate,
    emb: EmbeddingService = Depends(get_embedding_service),
    vdb: VectorDBService = Depends(get_vector_db_service),
):
    logger.info("Adding document: id=%s", doc.id)
    vdb.create_collection()

    chunk_size = doc.chunk_size or len(doc.text)
    chunk_overlap = doc.chunk_overlap or 0

    chunks = chunk_text(
        doc.text,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    ) if chunk_size < len(doc.text) else [doc.text]

    vectors = emb.embed_batch(chunks) if len(chunks) > 1 else [emb.embed(chunks[0])]

    points = []
    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
        point_id = f"{doc.id}__{i}" if len(chunks) > 1 else doc.id
        payload = {
            "text": chunk,
            "doc_id": doc.id,
            "chunk_index": i,
            **(doc.metadata or {}),
        }
        points.append({
            "id": point_id,
            "vector": vector,
            "payload": payload,
        })

    count = vdb.upsert(points)
    logger.info("Stored document '%s': %d chunks", doc.id, count)

    return DocumentResponse(
        id=doc.id,
        text=doc.text,
        metadata=doc.metadata or {},
        inserted_chunks=count,
    )


@router.post("/documents/batch/", status_code=status.HTTP_201_CREATED)
def add_documents(
    docs: list[DocumentCreate],
    emb: EmbeddingService = Depends(get_embedding_service),
    vdb: VectorDBService = Depends(get_vector_db_service),
):
    vdb.create_collection()

    logger.info("Batch adding %d documents", len(docs))
    points = []
    for doc in docs:
        chunk_size = doc.chunk_size or len(doc.text)
        chunk_overlap = doc.chunk_overlap or 0

        chunks = chunk_text(
            doc.text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        ) if chunk_size < len(doc.text) else [doc.text]

        vectors = emb.embed_batch(chunks) if len(chunks) > 1 else [emb.embed(chunks[0])]

        for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
            point_id = f"{doc.id}__{i}" if len(chunks) > 1 else doc.id
            payload = {
                "text": chunk,
                "doc_id": doc.id,
                "chunk_index": i,
                **(doc.metadata or {}),
            }
            points.append({
                "id": point_id,
                "vector": vector,
                "payload": payload,
            })

    count = vdb.upsert(points)
    logger.info("Batch upserted %d points for %d documents", count, len(docs))
    return {"inserted": count, "ids": [d.id for d in docs]}


@router.get("/documents/", response_model=ListDocumentsResponse)
def list_documents(
    limit: int = 100,
    offset: str | None = None,
    vdb: VectorDBService = Depends(get_vector_db_service),
):
    logger.info("Listing documents: limit=%d, offset=%s", limit, offset)
    try:
        if not vdb.client.collection_exists(settings.collection_name):
            logger.info("Collection '%s' does not exist, returning empty list", settings.collection_name)
            return ListDocumentsResponse(count=0, documents=[], next_page=None)
    except Exception:
        logger.warning("Cannot reach Qdrant, returning empty list")
        return ListDocumentsResponse(count=0, documents=[], next_page=None)
    points, next_page = vdb.scroll(limit=limit, offset=offset)
    logger.info("Listed %d documents", len(points))
    documents = [
        DocumentListItem(
            id=p["payload"].get("doc_id", p["id"]),
            text=p["payload"].get("text", ""),
            metadata={k: v for k, v in p["payload"].items() if k not in ("text", "doc_id", "chunk_index")},
        )
        for p in points
    ]
    return ListDocumentsResponse(
        count=len(documents),
        documents=documents,
        next_page=next_page,
    )


@router.post("/search", response_model=SearchResponse)
def search(
    request: SearchRequest,
    emb: EmbeddingService = Depends(get_embedding_service),
    vdb: VectorDBService = Depends(get_vector_db_service),
):
    logger.info("Search query: '%s' top_k=%d score_threshold=%s", request.query, request.top_k, request.score_threshold)
    if not vdb.client.collection_exists(settings.collection_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{settings.collection_name}' does not exist. Add documents first.",
        )
    query_vector = emb.embed(request.query)
    results = vdb.search(
        query_vector,
        top_k=request.top_k,
        score_threshold=request.score_threshold,
    )
    logger.info("Search returned %d results", len(results))
    hits = [
        SearchHit(
            id=r["payload"].get("doc_id", r["id"]),
            text=r["payload"].get("text", ""),
            score=round(r["score"], 4),
            metadata={k: v for k, v in r["payload"].items() if k not in ("text", "doc_id", "chunk_index")},
        )
        for r in results
    ]
    return SearchResponse(query=request.query, hits=hits)


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    doc_id: str,
    vdb: VectorDBService = Depends(get_vector_db_service),
):
    logger.info("Deleting document: id=%s", doc_id)
    vdb.delete_by_doc_id(doc_id)
    return
