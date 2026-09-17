"""
Embedding service — converts text into dense vectors and computes
semantic similarity.

Supports two backends (switchable via settings):

1. **sentence-transformers** (local):
   Runs an on-device transformer model — no API calls or costs.
   The default `all-MiniLM-L6-v2` produces 384-dimensional vectors.

2. **OpenAI embeddings** (cloud):
   Calls OpenAI's embedding endpoint for higher-dimensional vectors
   (e.g. 1536-d for text-embedding-3-small).

The service also demonstrates **cosine similarity**, **Euclidean distance**,
and **dot product** — the three core distance metrics used by vector
databases.
"""

from __future__ import annotations

import logging

import numpy as np
from openai import AsyncOpenAI

from app.core.config import settings
from app.models.schemas import EmbeddingResponse, SimilarityResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Distance / similarity metrics
# ---------------------------------------------------------------------------


def _to_numpy(vec: list[float]) -> np.ndarray:
    return np.array(vec, dtype=np.float64)


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Cosine similarity — angle between two vectors (ignoring magnitude)."""
    a, b = _to_numpy(vec_a), _to_numpy(vec_b)
    dot = float(np.dot(a, b))
    norm = float(np.linalg.norm(a) * np.linalg.norm(b))
    if norm == 0:
        return 0.0
    return dot / norm


def euclidean_distance(vec_a: list[float], vec_b: list[float]) -> float:
    """Euclidean (L2) distance — straight-line distance in space."""
    a, b = _to_numpy(vec_a), _to_numpy(vec_b)
    return float(np.linalg.norm(a - b))


def dot_product(vec_a: list[float], vec_b: list[float]) -> float:
    """Dot product — raw inner product; sensitive to both direction and magnitude."""
    return float(np.dot(_to_numpy(vec_a), _to_numpy(vec_b)))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> SimilarityResponse:
    """Compute all three similarity metrics between two vectors."""
    return SimilarityResponse(
        cosine=cosine_similarity(vec_a, vec_b),
        euclidean=euclidean_distance(vec_a, vec_b),
        dot_product=dot_product(vec_a, vec_b),
    )


# ---------------------------------------------------------------------------
# Embedding backends
# ---------------------------------------------------------------------------


class _SentenceTransformersBackend:
    """Local embedding backend using the sentence-transformers library."""

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(settings.embedding_model)
        self._dimensions = settings.embedding_dimensions

    async def embed(self, text: str) -> list[float]:
        # sentence-transformers encode is synchronous but fast for single texts
        vectors = await _run_in_thread(self._model.encode, [text])
        return vectors[0].tolist()

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_name(self) -> str:
        return settings.embedding_model


class _OpenAIEmbeddingBackend:
    """Cloud embedding backend using OpenAI's API."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.llm_api_key or "dummy-key",
            base_url=settings.llm_base_url,
        )
        self._model_name = settings.openai_embedding_model
        self._dimensions = 1536  # text-embedding-3-small default

    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(
            model=self._model_name,
            input=text,
        )
        return response.data[0].embedding

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_name(self) -> str:
        return self._model_name


async def _run_in_thread(func, *args, **kwargs):
    """Run a synchronous function in a thread to avoid blocking the event loop."""
    import asyncio

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


# ---------------------------------------------------------------------------
# Public embedding service
# ---------------------------------------------------------------------------


class EmbeddingService:
    """Service for text-to-vector conversion and similarity computation."""

    def __init__(self) -> None:
        self._backend: _SentenceTransformersBackend | _OpenAIEmbeddingBackend | None = None

    @property
    def backend(self):
        """Lazily initialise the embedding backend based on configuration."""
        if self._backend is None:
            if settings.embedding_provider == "openai":
                self._backend = _OpenAIEmbeddingBackend()
                logger.info("Using OpenAI embedding backend: %s", self._backend.model_name)
            else:
                self._backend = _SentenceTransformersBackend()
                logger.info("Using sentence-transformers backend: %s", self._backend.model_name)
        return self._backend

    @property
    def dimensions(self) -> int:
        return self.backend.dimensions

    @property
    def model_name(self) -> str:
        return self.backend.model_name

    async def embed(self, text: str) -> list[float]:
        """Convert a single text string into an embedding vector."""
        logger.debug("Embedding text (%d chars) via %s", len(text), self.model_name)
        vec = await self.backend.embed(text)
        logger.debug("Embedding complete — %d dimensions", len(vec))
        return vec

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts at once (batch)."""
        backend = self.backend
        logger.info("Batch embedding %d texts via %s", len(texts), self.model_name)
        if isinstance(backend, _SentenceTransformersBackend):
            vectors = await _run_in_thread(backend._model.encode, texts)
            result = [v.tolist() for v in vectors]
        else:
            # OpenAI batch
            response = await backend._client.embeddings.create(
                model=backend._model_name,
                input=texts,
            )
            # OpenAI may reorder; sort by index to preserve order
            data = sorted(response.data, key=lambda d: d.index)
            result = [d.embedding for d in data]
        logger.debug("Batch embedding complete — %d vectors", len(result))
        return result

    async def embed_query(self, text: str) -> EmbeddingResponse:
        """Generate an embedding and return it in API-ready form."""
        vec = await self.embed(text)
        return EmbeddingResponse(
            embedding=vec,
            model=self.model_name,
            dimensions=self.dimensions,
        )

    async def similarity(self, text_a: str, text_b: str) -> SimilarityResponse:
        """Compute similarity between two texts by embedding them first."""
        logger.info(
            "Computing similarity between two texts (%d, %d chars)",
            len(text_a),
            len(text_b),
        )
        vec_a = await self.embed(text_a)
        vec_b = await self.embed(text_b)
        return compute_similarity(vec_a, vec_b)


# Module-level singleton
embedding_service = EmbeddingService()
