"""
Vector database service — manages vector storage and similarity search using Qdrant.

Adapted from the existing gen-ai-poc / vector-db-poc implementation.

Key concepts demonstrated:
- Collection creation with configurable distance metric
- Point (vector) insertion with metadata payloads
- Similarity search (nearest-neighbor lookup)
- Metadata filtering (hybrid search capability)

Heavy dependencies (qdrant-client) are imported lazily so the core
agent loop works without it.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from app.core.config import settings
from app.models.schemas import Chunk, SearchHit

logger = logging.getLogger(__name__)

_NAMESPACE = uuid.NAMESPACE_DNS


def to_uuid(point_id: str) -> uuid.UUID:
    """Deterministically map an arbitrary string ID to a UUID5."""
    return uuid.uuid5(_NAMESPACE, point_id)


class VectorDBService:
    """Service wrapping Qdrant for vector storage and retrieval.

    Uses lazy initialization of the Qdrant client. When Qdrant is not
    available, methods raise a clear error so the caller can handle it.
    """

    def __init__(self) -> None:
        self._client: Optional[Any] = None
        self._collection: str = settings.qdrant_collection

    @property
    def collection_name(self) -> str:
        return self._collection

    @property
    def client(self):
        """Lazily initialise the Qdrant client."""
        if self._client is None:
            from qdrant_client import QdrantClient

            host = settings.qdrant_host
            port = settings.qdrant_port
            # Handle both "host:port" URL and bare host
            if host.startswith("http"):
                self._client = QdrantClient(url=host)
            else:
                self._client = QdrantClient(host=host, port=port)
            logger.info("Connected to Qdrant at %s:%s", host, port)
        return self._client

    def _distance(self):
        from qdrant_client.http import models as rest
        return rest.Distance.COSINE

    async def create_collection(self) -> None:
        """Create the vector collection if it does not exist."""
        from qdrant_client.http import models as rest
        from qdrant_client.http.exceptions import UnexpectedResponse

        try:
            self.client.get_collection(self._collection)
            logger.info("Collection '%s' already exists", self._collection)
        except UnexpectedResponse:
            self.client.recreate_collection(
                collection_name=self._collection,
                vectors_config=rest.VectorParams(
                    size=settings.embedding_dimensions,
                    distance=self._distance(),
                ),
            )
            logger.info(
                "Created collection '%s' with %d-dim vectors",
                self._collection, settings.embedding_dimensions,
            )

    async def upsert_chunks(self, chunks: list[Chunk], embeddings: list[list[float]]) -> int:
        """Store document chunks and their embeddings in the vector DB."""
        from qdrant_client.http import models as rest

        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")

        points: list[rest.PointStruct] = []
        for chunk, vector in zip(chunks, embeddings):
            point_id = chunk.id or str(uuid.uuid4())
            # Qdrant only accepts integer or UUID point IDs — map arbitrary
            # string chunk IDs (e.g. "doc-1_chunk_0") to a deterministic UUID.
            payload: dict[str, Any] = {
                "text": chunk.text,
                "document_id": chunk.document_id,
                "chunk_index": chunk.chunk_index,
                **chunk.metadata,
            }
            points.append(rest.PointStruct(id=to_uuid(point_id), vector=vector, payload=payload))

        self.client.upsert(collection_name=self._collection, points=points)
        logger.info("Upserted %d points into '%s'", len(points), self._collection)
        return len(points)

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filter_condition: Optional[dict[str, Any]] = None,
    ) -> list[SearchHit]:
        """Perform a similarity search in the vector DB."""
        from qdrant_client.http import models as rest

        search_filter = None
        if filter_condition:
            search_filter = rest.Filter(
                must=[
                    rest.FieldCondition(
                        key=key,
                        match=rest.MatchValue(any=[val] if isinstance(val, list) else [val]),
                    )
                    for key, val in filter_condition.items()
                ]
            )

        results = self.client.query_points(
            collection_name=self._collection,
            query=query_vector,
            with_payload=True,
            with_vectors=False,
            limit=top_k,
            query_filter=search_filter,
        )

        hits: list[SearchHit] = []
        for r in results.points:
            payload = r.payload or {}
            hits.append(SearchHit(
                id=str(r.id),
                score=r.score,
                text=payload.get("text", ""),
                metadata={k: v for k, v in payload.items() if k != "text"},
            ))
        return hits

    async def delete(self, ids: list[str]) -> int:
        """Delete points by their original string IDs."""
        from qdrant_client.http import models as rest
        self.client.delete(
            collection_name=self._collection,
            points_selector=rest.PointIdsList(points=[str(to_uuid(i)) for i in ids]),
        )
        return len(ids)

    @property
    def available(self) -> bool:
        """Check if Qdrant is reachable."""
        try:
            _ = self.client
            return True
        except Exception:
            return False


# Module-level singleton
vector_db = VectorDBService()
