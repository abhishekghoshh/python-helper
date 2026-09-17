"""
Pydantic data models (DTOs) for the API and internal services.

These schemas define every request/response shape and the internal
message objects that flow through the GenAI pipeline.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Chat message types
# ---------------------------------------------------------------------------


class MessageRole(str, Enum):
    """Roles in a chat conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    """A single message in a chat conversation."""

    role: MessageRole
    content: str

    model_config = {"use_enum_values": False}


# ---------------------------------------------------------------------------
# LLM API schemas
# ---------------------------------------------------------------------------


class LLMRequest(BaseModel):
    """Request body for chat completion generation."""

    messages: list[ChatMessage] = Field(..., min_length=1, description="Conversation messages")
    model: str | None = Field(None, description="Model identifier (uses default if omitted)")
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    top_p: float | None = Field(None, ge=0.0, le=1.0)
    max_tokens: int | None = Field(None, ge=1, le=16384)
    stream: bool = Field(False, description="Stream token-by-token")

    model_config = {"use_enum_values": False}


class LLMResponse(BaseModel):
    """Response from the LLM."""

    id: str
    model: str
    content: str
    usage: dict[str, int] | None = None
    finish_reason: str | None = None


class LLMStreamChunk(BaseModel):
    """A single chunk in a streaming response."""

    content: str
    finish_reason: str | None = None


# ---------------------------------------------------------------------------
# Embedding API schemas
# ---------------------------------------------------------------------------


class EmbeddingRequest(BaseModel):
    """Request to generate embeddings for a piece of text."""

    text: str = Field(..., min_length=1)
    model: str | None = Field(None, description="Embedding model override")


class EmbeddingResponse(BaseModel):
    """Response containing an embedding vector."""

    embedding: list[float]
    model: str
    dimensions: int


class SimilarityRequest(BaseModel):
    """Request to compute similarity between two texts."""

    text_a: str
    text_b: str
    metric: str = Field("cosine", description="cosine | euclid | dot")


class SimilarityResponse(BaseModel):
    """Response containing similarity scores."""

    cosine: float
    euclidean: float
    dot_product: float


# ---------------------------------------------------------------------------
# Document / RAG schemas
# ---------------------------------------------------------------------------


class Document(BaseModel):
    """A document to be indexed."""

    id: str | None = None
    content: str = Field(..., min_length=1, description="Full text content")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata")


class Chunk(BaseModel):
    """A piece of a document after chunking."""

    id: str
    text: str
    document_id: str
    chunk_index: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    """Result of ingesting documents."""

    documents_processed: int
    chunks_created: int
    collection: str


class SearchHit(BaseModel):
    """A single search result."""

    id: str
    score: float
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Response for document search."""

    query: str
    hits: list[SearchHit]
    collection: str


class RAGRequest(BaseModel):
    """Request body for a RAG question-answer."""

    question: str = Field(..., min_length=1)
    top_k: int | None = Field(None, ge=1, le=50, description="Override default top-k")
    model: str | None = Field(None, description="Override LLM model")
    temperature: float | None = Field(None, ge=0.0, le=2.0)


class RAGResponse(BaseModel):
    """Response containing the generated RAG answer."""

    answer: str
    sources: list[SearchHit] = Field(default_factory=list)
    context: str = ""
