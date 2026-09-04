from typing import Any, Optional

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentResponse(BaseModel):
    id: str
    text: str
    score: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    vector: Optional[list[float]] = None


class EmbeddingResponse(BaseModel):
    vector: list[float]
    dimension: int


class SearchHit(BaseModel):
    id: str
    text: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit]


class HealthResponse(BaseModel):
    status: str = "ok"
    qdrant: str = "connected"
    embedding_model: str
