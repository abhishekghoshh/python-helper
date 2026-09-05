from typing import Any, Optional

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None


class DocumentResponse(BaseModel):
    id: str
    text: str
    score: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    vector: Optional[list[float]] = None
    inserted_chunks: Optional[int] = None


class DocumentListItem(BaseModel):
    id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ListDocumentsResponse(BaseModel):
    count: int
    documents: list[DocumentListItem]
    next_page: Optional[str] = None


class EmbeddingRequest(BaseModel):
    text: str


class EmbeddingResponse(BaseModel):
    vector: list[float]
    dimension: int


class SearchHit(BaseModel):
    id: str
    text: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    score_threshold: Optional[float] = None


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit]


class HealthResponse(BaseModel):
    status: str = "ok"
    qdrant: str = "connected"
    embedding_model: str
    embedding_dim: int = 0
