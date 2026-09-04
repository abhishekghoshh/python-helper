from fastapi import APIRouter, Depends, HTTPException, status
from qdrant_client import QdrantClient

from app.config import settings
from app.models.schemas import (
    DocumentCreate,
    DocumentResponse,
    EmbeddingResponse,
    HealthResponse,
    SearchHit,
    SearchResponse,
)
from app.services.embedding import EmbeddingService
from app.services.vector_db import VectorDBService

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
            client, settings.collection_name, settings.embedding_dim
        )
    return _vdb_service


@router.get("/health", response_model=HealthResponse)
def health(emb: EmbeddingService = Depends(get_embedding_service)):
    try:
        dim = emb.dimension
    except Exception:
        dim = 0
    return HealthResponse(
        status="ok",
        embedding_model=settings.embedding_model,
    )


@router.post("/embed", response_model=EmbeddingResponse)
def embed(
    text: str,
    emb: EmbeddingService = Depends(get_embedding_service),
):
    vector = emb.embed(text)
    return EmbeddingResponse(vector=vector, dimension=len(vector))


@router.post("/documents/", status_code=status.HTTP_201_CREATED, response_model=DocumentResponse)
def add_document(
    doc: DocumentCreate,
    emb: EmbeddingService = Depends(get_embedding_service),
    vdb: VectorDBService = Depends(get_vector_db_service),
):
    vdb.create_collection()
    vector = emb.embed(doc.text)
    payload = {"text": doc.text, "doc_id": doc.id, **(doc.metadata or {})}
    vdb.upsert(
        [
            {
                "id": doc.id,
                "vector": vector,
                "payload": payload,
            }
        ]
    )
    return DocumentResponse(
        id=doc.id,
        text=doc.text,
        metadata={k: v for k, v in payload.items() if k not in ("text", "doc_id")},
    )


@router.post("/documents/batch/", status_code=status.HTTP_201_CREATED)
def add_documents(
    docs: list[DocumentCreate],
    emb: EmbeddingService = Depends(get_embedding_service),
    vdb: VectorDBService = Depends(get_vector_db_service),
):
    vdb.create_collection()
    texts = [d.text for d in docs]
    vectors = emb.embed_batch(texts)
    points = [
        {
            "id": d.id,
            "vector": vectors[i],
            "payload": {"text": d.text, "doc_id": d.id, **(d.metadata or {})},
        }
        for i, d in enumerate(docs)
    ]
    count = vdb.upsert(points)
    return {"inserted": count, "ids": [d.id for d in docs]}


@router.post("/search", response_model=SearchResponse)
def search(
    query: str,
    top_k: int = 5,
    emb: EmbeddingService = Depends(get_embedding_service),
    vdb: VectorDBService = Depends(get_vector_db_service),
):
    if not vdb.client.collection_exists(settings.collection_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{settings.collection_name}' does not exist. Add documents first.",
        )
    query_vector = emb.embed(query)
    results = vdb.search(query_vector, top_k=top_k)
    hits = [
        SearchHit(
            id=r["payload"].get("doc_id", r["id"]),
            text=r["payload"].get("text", ""),
            score=round(r["score"], 4),
            metadata={k: v for k, v in r["payload"].items() if k not in ("text", "doc_id")},
        )
        for r in results
    ]
    return SearchResponse(query=query, hits=hits)


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    doc_id: str,
    vdb: VectorDBService = Depends(get_vector_db_service),
):
    vdb.delete(ids=[doc_id])
    return
