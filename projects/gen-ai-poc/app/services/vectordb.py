"""
Vector database service — manages document storage and similarity search
using Qdrant.

Qdrant is used as the primary vector database for this POC. It is lightweight,
runs easily in Docker, supports multiple distance metrics, and provides
metadata filtering — all essential for demonstrating RAG.

This service demonstrates:
- Collection creation with configurable distance metric
- Point (vector) insertion with metadata payloads
- Similarity search (nearest-neighbor lookup)
- Metadata filtering (hybrid search capability)
- The relationship between vectors and documents
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

from app.core.config import settings
from app.models.schemas import Chunk, SearchHit

logger = logging.getLogger(__name__)


class VectorDBService:
    """Service wrapping Qdrant for vector storage and retrieval."""

    def __init__(self) -> None:
        self._client: QdrantClient | None = None
        self._collection: str = settings.qdrant_collection

    @property
    def collection(self) -> str:
        """Return the collection name."""
        return self._collection

    @property
    def client(self) -> QdrantClient:
        """Lazily initialise the Qdrant client."""
        if self._client is None:
            self._client = QdrantClient(
                url=settings.qdrant_host,
                # Skip compatibility check so it works with any server version
                check_compatibility=False,
            )
            logger.info("Connected to Qdrant at %s", settings.qdrant_host)
        return self._client

    def _distance(self) -> rest.Distance:
        """Map config distance to Qdrant Distance enum."""
        mode = settings.qdrant_distance_mode
        mapping = {
            "Cosine": rest.Distance.COSINE,
            "Euclid": rest.Distance.EUCLID,
            "Dot": rest.Distance.DOT,
        }
        return mapping[mode]

    async def create_collection(self) -> None:
        """Create the vector collection if it does not exist."""
        if self.client.collection_exists(self._collection):
            logger.info("Collection '%s' already exists", self._collection)
            return

        self.client.recreate_collection(
            collection_name=self._collection,
            vectors_config=rest.VectorParams(
                size=settings.embedding_dimensions,
                distance=self._distance(),
            ),
        )
        logger.info(
            "Created collection '%s' with %d-dim vectors and %s distance",
            self._collection,
            settings.embedding_dimensions,
            settings.qdrant_distance,
        )

    async def upsert_chunks(self, chunks: list[Chunk], embeddings: list[list[float]]) -> int:
        """Store document chunks and their embeddings in the vector DB.

        Args:
            chunks: The text chunks to store.
            embeddings: Corresponding embedding vectors (same length as chunks).

        Returns:
            Number of points written (0 = failed).
        """
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")

        points: list[rest.PointStruct] = []
        for chunk, vector in zip(chunks, embeddings, strict=True):
            point_id = chunk.id if chunk.id else str(uuid.uuid4())
            payload: dict[str, Any] = {
                "text": chunk.text,
                "document_id": chunk.document_id,
                "chunk_index": chunk.chunk_index,
                **chunk.metadata,
            }
            points.append(
                rest.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            )

        result = self.client.upsert(
            collection_name=self._collection,
            points=points,
            wait=True,
        )
        logger.info("Upserted %d points into '%s'", len(points), self._collection)
        return 1 if result else 0

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filter_condition: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        """Perform a similarity search in the vector DB.

        Args:
            query_vector: The embedding to search for.
            top_k: Number of nearest neighbors to return.
            filter_condition: Optional metadata filter (e.g. {"category": "tech"}).

        Returns:
            List of SearchHit objects ranked by similarity.
        """
        search_filter = None
        if filter_condition:
            must_conditions = []
            for key, val in filter_condition.items():
                if isinstance(val, list):
                    must_conditions.append(
                        rest.FieldCondition(
                            key=key,
                            match=rest.MatchAny(any=val),
                        )
                    )
                else:
                    must_conditions.append(
                        rest.FieldCondition(
                            key=key,
                            match=rest.MatchValue(value=val),
                        )
                    )
            search_filter = rest.Filter(must=must_conditions)

        logger.info(
            "Vector search — collection='%s', top_k=%d, dimensions=%d, filter=%s",
            self._collection,
            top_k,
            len(query_vector),
            filter_condition,
        )
        results = self.client.query_points(
            collection_name=self._collection,
            query=query_vector,
            with_payload=True,
            with_vectors=False,
            limit=top_k,
            query_filter=search_filter,
        )
        logger.info("Vector search returned %d results", len(results.points))

        hits: list[SearchHit] = []
        for r in results.points:
            payload = r.payload or {}
            hits.append(
                SearchHit(
                    id=r.id,
                    score=r.score,
                    text=payload.get("text", ""),
                    metadata={k: v for k, v in payload.items() if k != "text"},
                )
            )
        return hits


# Module-level singleton
vector_db = VectorDBService()
