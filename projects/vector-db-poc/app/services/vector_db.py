import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

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

    def create_collection(self) -> None:
        if not self.client.collection_exists(self.collection_name):
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
        results = self.client.search(**search_kwargs)
        return [
            {
                "id": str(hit.id),
                "score": hit.score,
                "payload": hit.payload or {},
            }
            for hit in results
        ]

    def scroll(self, limit: int = 100, offset: str | None = None) -> tuple[list[dict], str | None]:
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
        return points, next_page

    def delete(self, ids: list[str]) -> int:
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=qmodels.PointIdsList(points=[str(to_uuid(i)) for i in ids]),
        )
        return len(ids)

    def delete_by_doc_id(self, doc_id: str) -> None:
        """Delete all points (including chunks) whose payload doc_id matches."""
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
