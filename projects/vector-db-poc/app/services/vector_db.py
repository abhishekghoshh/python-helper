import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

_NAMESPACE = uuid.NAMESPACE_DNS


def to_uuid(point_id: str) -> uuid.UUID:
    """Deterministically map an arbitrary string ID to a UUID5."""
    return uuid.uuid5(_NAMESPACE, point_id)


class VectorDBService:
    """Minimal Qdrant wrapper for storing and querying vectors."""

    def __init__(self, client: QdrantClient, collection_name: str, embedding_dim: int):
        self.client = client
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim

    def create_collection(self) -> None:
        if not self.client.collection_exists(self.collection_name):
            self.client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=qmodels.VectorParams(
                    size=self.embedding_dim,
                    distance=qmodels.Distance.COSINE,
                ),
            )

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

    def search(self, vector: list[float], top_k: int = 5) -> list[dict]:
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            with_payload=True,
            with_vectors=False,
            limit=top_k,
        )
        return [
            {
                "id": str(hit.id),
                "score": hit.score,
                "payload": hit.payload or {},
            }
            for hit in results
        ]

    def delete(self, ids: list[str]) -> int:
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=qmodels.PointIdsList(points=[str(to_uuid(i)) for i in ids]),
        )
        return len(ids)
