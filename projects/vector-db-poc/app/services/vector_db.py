"""Qdrant vector database service."""

import logging
import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

logger = logging.getLogger(__name__)

_NAMESPACE = uuid.NAMESPACE_DNS

_DISTANCE_MAP = {
    "cosine": qmodels.Distance.COSINE,
    "euclidean": qmodels.Distance.EUCLID,
    "dot": qmodels.Distance.DOT,
}


def to_uuid(point_id: str) -> uuid.UUID:
    """Deterministically map an arbitrary string ID to a UUID5."""
    return uuid.uuid5(_NAMESPACE, point_id)


class VectorDBService:
    """Minimal Qdrant wrapper for storing and querying vectors."""

    def __init__(
        self,
        client: QdrantClient,
        collection_name: str,
        embedding_dim: int,
        distance: str = "cosine",
    ):
        self.client = client
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        self.distance = _DISTANCE_MAP.get(distance.lower(), qmodels.Distance.COSINE)
        logger.debug(
            "VectorDBService initialized: collection=%s, dim=%d, distance=%s",
            collection_name,
            embedding_dim,
            distance,
        )

    def create_collection(self) -> None:
        if not self.client.collection_exists(self.collection_name):
            logger.info(
                "Creating collection '%s' (dim=%d, distance=%s)",
                self.collection_name,
                self.embedding_dim,
                self.distance,
            )
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qmodels.VectorParams(
                    size=self.embedding_dim,
                    distance=self.distance,
                ),
            )

    def ensure_collection(self) -> None:
        """Create the collection if it does not already exist."""
        self.create_collection()

    def upsert(self, points: list[dict]) -> int:
        """points: list of dicts with id, vector, payload (id is a str)."""
        logger.debug("Upserting %d points into '%s'", len(points), self.collection_name)
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                qmodels.PointStruct(
                    id=str(to_uuid(p["id"])),
                    vector=p["vector"],
                    payload=p.get("payload", {}),
                )
                for p in points
            ],
        )
        return len(points)

    def search(
        self, vector: list[float], top_k: int = 5, score_threshold: float | None = None
    ) -> list[dict]:
        search_kwargs = dict(
            collection_name=self.collection_name,
            query_vector=vector,
            with_payload=True,
            with_vectors=False,
            limit=top_k,
        )
        if score_threshold is not None:
            search_kwargs["score_threshold"] = score_threshold
        logger.debug(
            "Searching '%s' top_k=%d score_threshold=%s",
            self.collection_name,
            top_k,
            score_threshold,
        )
        results = self.client.search(**search_kwargs)
        logger.debug("Search returned %d results", len(results))
        return [
            {
                "id": str(hit.id),
                "score": hit.score,
                "payload": hit.payload or {},
            }
            for hit in results
        ]

    def scroll(self, limit: int = 100, offset: str | None = None) -> tuple[list[dict], str | None]:
        # Qdrant's scroll API uses cursor-based pagination where ``offset`` is
        # a point ID, not a numeric offset.  Treat "0", "" and None as "start
        # from the beginning" (no offset).
        if not offset or offset == "0":
            offset = None
        logger.debug("Scrolling collection '%s' limit=%d offset=%s", self.collection_name, limit, offset)
        results, next_page = self.client.scroll(
            collection_name=self.collection_name,
            with_payload=True,
            with_vectors=False,
            limit=limit,
            offset=offset,
        )
        points = [
            {
                "id": str(r.id),
                "payload": r.payload or {},
            }
            for r in results
        ]
        logger.debug("Scrolled %d points, next_page=%s", len(points), next_page)
        return points, next_page

    def delete(self, ids: list[str]) -> int:
        logger.info("Deleting %d points by ID from '%s'", len(ids), self.collection_name)
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=qmodels.PointIdsList(points=[str(to_uuid(i)) for i in ids]),
        )
        return len(ids)

    def delete_by_doc_id(self, doc_id: str) -> None:
        """Delete all points (including chunks) whose payload doc_id matches."""
        logger.info("Deleting all chunks for doc_id='%s' from '%s'", doc_id, self.collection_name)
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="doc_id",
                        match=qmodels.MatchValue(value=doc_id),
                    )
                ]
            ),
        )
