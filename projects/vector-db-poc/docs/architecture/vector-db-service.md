# Vector Database Service — Learning Guide

## 1. What problem does it solve?

To store, index, and search **high-dimensional vectors** efficiently. A regular database can store vectors as arrays, but it cannot perform k-NN (k-nearest neighbors) search quickly — a linear scan of every vector would be prohibitively slow for large datasets. The vector database service provides optimized storage and search over vectors with associated metadata.

## 2. Why is it required?

Semantic search requires finding vectors that are **similar** to a query vector. With thousands or millions of vectors, brute-force comparison is O(n) per query. A vector database like Qdrant uses **approximate nearest neighbor (ANN)** indexing (HNSW graphs) to find similar vectors in sub-linear time, making semantic search practical at scale.

## 3. What concept does it demonstrate?

- **Vector collections** — logical groupings of vectors with a shared schema (dimension, distance metric)
- **Point storage** — vectors stored with unique IDs and metadata (payload)
- **Deterministic ID mapping** — converting human-readable IDs to database IDs consistently
- **k-NN search** — finding the K most similar vectors to a query
- **Payload filtering** — metadata associated with vectors
- **Collection management** — creating and checking collection existence

## 4. How does it work internally?

### Theory

Qdrant stores each vector as a **PointStruct** with three components:

1. **ID** — A unique identifier (UUID in this project)
2. **Vector** — The dense embedding (e.g., 384 floats)
3. **Payload** — Arbitrary JSON metadata (e.g., `{"text": "...", "category": "docs"}`)

When searching, Qdrant:
1. Receives a query vector
2. Traverses its HNSW graph to find approximate nearest neighbors
3. Computes exact similarity (cosine) for candidates in the graph neighborhood
4. Returns the top-K matches with their scores and payloads

### Implementation in this project

The `VectorDBService` class (`app/services/vector_db.py`) wraps `qdrant_client.QdrantClient`:

```python
class VectorDBService:
    def __init__(self, client: QdrantClient, collection_name: str, embedding_dim: int):
        self.client = client
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
```

#### Deterministic UUID mapping

A key design decision: document IDs in the API are human-readable strings (e.g., `"doc-1"`), but Qdrant requires unique point IDs. Instead of sequential or random UUIDs, the project uses **UUID5**:

```python
_NAMESPACE = uuid.NAMESPACE_DNS

def to_uuid(point_id: str) -> uuid.UUID:
    """Deterministically map an arbitrary string ID to a UUID5."""
    return uuid.uuid5(_NAMESPACE, point_id)
```

**UUID5** generates a UUID from a SHA-1 hash of a namespace + name. This means:
- The same string ID always produces the same UUID
- Upserting a document with `"doc-1"` and later deleting `"doc-1"` will target the correct point
- No need to track a separate ID mapping table

This is important because it allows the **same string ID** to be used for both insert and delete operations.

#### Collection creation

```python
def create_collection(self) -> None:
    if not self.client.collection_exists(self.collection_name):
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=qmodels.VectorParams(
                size=self.embedding_dim,
                distance=qmodels.Distance.COSINE,
            ),
        )
```

- Creates a collection with **384 dimensions** and **cosine distance**
- `recreate_collection` handles both creation and recreation
- Checked with `collection_exists` to avoid errors on re-creation

#### Upsert (insert/update)

```python
def upsert(self, points: list[dict]) -> int:
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
```

- Each point is converted to a `PointStruct` with UUID-mapped ID
- Vectors and payload (metadata) are stored together
- The `upsert` operation inserts new points or updates existing ones with the same ID

#### Search

```python
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
```

- `query_vector` — the embedding of the search query
- `with_payload=True` — includes metadata in results
- `with_vectors=False` — doesn't include the stored vectors (saves bandwidth)
- `limit=top_k` — number of results to return
- Returns a simplified dict format with `id`, `score`, and `payload`

#### Delete

```python
def delete(self, ids: list[str]) -> int:
    self.client.delete(
        collection_name=self.collection_name,
        points_selector=qmodels.PointIdsList(points=[str(to_uuid(i)) for i in ids]),
    )
    return len(ids)
```

- Uses the same UUID5 mapping to find points by their original string ID
- `PointIdsList` tells Qdrant which specific points to delete

## 5. Important classes and methods

### `to_uuid(point_id)`

| Aspect | Detail |
|--------|--------|
| **Location** | `app/services/vector_db.py:10` |
| **Purpose** | Deterministically map string IDs to UUIDs |
| **Namespace** | `uuid.NAMESPACE_DNS` |
| **Algorithm** | SHA-1 based UUID5 |
| **Why** | Same string → same UUID, enabling consistent upsert/delete |

### `VectorDBService`

| Method | Purpose | Code reference |
|--------|---------|----------------|
| `__init__(client, collection_name, embedding_dim)` | Store config | `vector_db.py:17-20` |
| `create_collection()` | Create Qdrant collection with COSINE distance | `vector_db.py:22-30` |
| `upsert(points)` | Insert/update points with UUID-mapped IDs | `vector_db.py:32-45` |
| `search(vector, top_k)` | k-NN search returning id/score/payload | `vector_db.py:47-62` |
| `delete(ids)` | Delete points by original string IDs | `vector_db.py:64-69` |

### How it's wired in the API

In `app/api/routes.py`, the `VectorDBService` is lazily instantiated:

```python
_vdb_service: VectorDBService | None = None

def get_vector_db_service() -> VectorDBService:
    global _vdb_service
    if _vdb_service is None:
        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        _vdb_service = VectorDBService(
            client, settings.collection_name, settings.embedding_dim
        )
    return _vdb_service
```

## 6. Alternatives

| Database | Why choose it | Trade-offs |
|----------|--------------|------------|
| **Qdrant (this project)** | Easy self-hosting, HNSW indexing, payload filtering, good Python client | Single-node by default, smaller ecosystem than Milvus |
| **Pinecone** | Fully managed, serverless, multi-region | Vendor lock-in, cost at scale |
| **Milvus** | Distributed, massive scale, multiple index types | Complex deployment, heavy resource usage |
| **Weaviate** | GraphQL API, built-in ML modules, hybrid search | More complex setup than Qdrant |
| **Chroma** | Designed for LLM apps, simple API | Less mature, focused on embeddings |
| **pgvector** | Runs in PostgreSQL, SQL queries, ACID | Slower than dedicated vector DBs |

## 7. Trade-offs

- **HNSW indexing** (Qdrant's default) trades a small amount of recall for significant speed gains. For most applications, recall is 95%+ at 10–50x faster search.
- **UUID5 vs. UUID4**: UUID5 is deterministic (same input → same UUID), which is essential for upsert/delete by original ID. UUID4 would be random and require tracking an ID mapping.
- **COSINE distance** works well for text embeddings because it measures direction (semantic meaning) independent of magnitude. For some use cases, L2 (Euclidean) or DOT (dot product) may be more appropriate.
- **Payload storage**: Storing metadata (payload) alongside vectors enables filtering and result reconstruction, but increases storage and can slow down searches if payloads are large.