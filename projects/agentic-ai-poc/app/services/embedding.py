"""
Embedding service — converts text into dense vectors.

Adapted from the existing gen-ai-poc / vector-db-poc embedding service.

Supports two backends (switchable via settings):

1. **sentence-transformers** (local) — runs an on-device transformer model.
2. **OpenAI embeddings** (cloud) — calls OpenAI's embedding endpoint.

The service also exposes the three core distance/similarity metrics
(cosine, Euclidean, dot product) used by vector databases.

**Lazy loading:** heavy dependencies are imported only when first needed,
so the core agent loop works without sentence-transformers or torch.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _to_numpy(vec: list[float]):
    """Convert a list to a numpy array (numpy is a core dependency)."""
    import numpy as np
    return np.array(vec, dtype=np.float64)


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Cosine similarity — angle between two vectors (ignoring magnitude)."""
    a, b = _to_numpy(vec_a), _to_numpy(vec_b)
    dot = float(a @ b)
    norm = float((a @ a) ** 0.5 * (b @ b) ** 0.5)
    if norm == 0:
        return 0.0
    return dot / norm


def euclidean_distance(vec_a: list[float], vec_b: list[float]) -> float:
    """Euclidean (L2) distance — straight-line distance in space."""
    a, b = _to_numpy(vec_a), _to_numpy(vec_b)
    import numpy as np
    return float(np.sqrt(((a - b) ** 2).sum()))


def dot_product(vec_a: list[float], vec_b: list[float]) -> float:
    """Dot product — raw inner product; sensitive to magnitude and direction."""
    a, b = _to_numpy(vec_a), _to_numpy(vec_b)
    return float(a @ b)


class _SentenceTransformersBackend:
    """Local embedding backend using the sentence-transformers library."""

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(settings.embedding_model)
        self._dimensions = settings.embedding_dimensions

    async def embed(self, text: str) -> list[float]:
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: self._model.encode(text, convert_to_numpy=True)
        )
        return result.tolist()

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        )
        return [v.tolist() for v in result]

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_name(self) -> str:
        return settings.embedding_model


class _OpenAIEmbeddingBackend:
    """Cloud embedding backend using OpenAI's API."""

    def __init__(self) -> None:
        from openai import AsyncOpenAI
        from app.llm.service import OpenAILLMService

        self._client = AsyncOpenAI(
            api_key=settings.llm_api_key or "dummy-key",
            base_url=settings.llm_base_url,
        )
        self._dimensions = settings.embedding_dimensions
        self._model_name = settings.openai_embedding_model if hasattr(settings, 'openai_embedding_model') else "text-embedding-3-small"

    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(
            model=self._model_name,
            input=text,
        )
        return response.data[0].embedding

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(
            model=self._model_name,
            input=texts,
        )
        data = sorted(response.data, key=lambda d: d.index)
        return [d.embedding for d in data]

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_name(self) -> str:
        return self._model_name


class EmbeddingService:
    """Service for text-to-vector conversion and similarity computation.

    The backend is selected via ``settings.embedding_provider``:
    - ``"sentence-transformers"`` (default) → local model
    - ``"openai"`` → cloud API

    Heavy dependencies (sentence-transformers, openai) are imported lazily
    so importing this module doesn't require them.
    """

    def __init__(self) -> None:
        self._backend: Optional[object] = None

    @property
    def backend(self):
        if self._backend is None:
            if settings.embedding_provider == "openai":
                self._backend = _OpenAIEmbeddingBackend()
                logger.info("Using OpenAI embedding backend")
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
        return await self.backend.embed(text)

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        return await self.backend.embed_many(texts)

    async def similarity(self, text_a: str, text_b: str) -> dict:
        """Compute similarity between two texts by embedding them first."""
        vec_a = await self.embed(text_a)
        vec_b = await self.embed(text_b)
        return {
            "cosine": cosine_similarity(vec_a, vec_b),
            "euclidean": euclidean_distance(vec_a, vec_b),
            "dot_product": dot_product(vec_a, vec_b),
        }

    @property
    def available(self) -> bool:
        """Check if the embedding backend can be loaded."""
        try:
            _ = self.backend  # triggers lazy load
            return True
        except Exception:
            return False


# Module-level singleton
embedding_service = EmbeddingService()
