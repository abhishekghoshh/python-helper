# Using Qdrant

Qdrant is the vector database used in this POC. This page walks through
how to use it in practice.

## Installation

### Via Docker (Recommended)

```bash
docker run -p 6333:6333 -p 6334:6334 \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant
```

### Via Docker Compose

```yaml
# docker-compose.yml
services:
  qdrant:
    image: qdrant/qdrant:v1.11
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_storage:/qdrant/storage
```

Then start:
```bash
docker compose up qdrant
```

### Python SDK

```bash
poetry add qdrant-client
```

## Basic Operations

### 1. Connect

```python
from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")
```

### 2. Create a Collection

A **collection** is like a table — it holds vectors of the same dimensions
and distance metric.

```python
from qdrant_client.http import models

client.recreate_collection(
    collection_name="my-documents",
    vectors_config=models.VectorParams(
        size=384,                    # Embedding dimensions
        distance=models.Distance.COSINE,  # Similarity metric
    ),
)
```

### 3. Add Vectors (Upsert)

```python
from qdrant_client.http import models

client.upsert(
    collection_name="my-documents",
    points=[
        models.PointStruct(
            id="doc-001",
            vector=[0.1, 0.2, ...],  # 384-dim embedding
            payload={
                "text": "The capital of France is Paris.",
                "category": "geography",
                "language": "en",
            },
        ),
    ],
)
```

### 4. Search

```python
results = client.search(
    collection_name="my-documents",
    query_vector=[0.1, 0.2, ...],  # Query embedding
    with_payload=True,   # Include metadata
    with_vectors=False,  # Don't include raw vectors
    limit=5,             # Top-5 results
)

for hit in results:
    print(f"Score: {hit.score:.4f}")
    print(f"Text: {hit.payload['text']}")
    print(f"Category: {hit.payload['category']}")
```

## Distance Metrics

Qdrant supports three distance modes (set at collection creation):

| Metric | Use Case | When to use |
|--------|----------|-------------|
| `COSINE` | Semantic similarity | Most search applications |
| `EUCLID` | Geometric distance | Clustering, visualization |
| `DOT` | Raw inner product | When vector magnitude matters |

```python
# Cosine (default in our POC)
distance=models.Distance.COSINE

# Euclidean
distance=models.Distance.EUCLID

# Dot product
distance=models.Distance.DOT
```

## Search with Filters

Combine vector search with metadata filtering:

```python
results = client.search(
    collection_name="my-documents",
    query_vector=[0.1, 0.2, ...],
    with_payload=True,
    limit=5,
    query_filter=models.Filter(
        must=[
            models.FieldCondition(
                key="category",
                match=models.MatchValue(value="geography"),
            ),
            models.FieldCondition(
                key="language",
                match=models.MatchValue(value="en"),
            ),
        ],
    ),
)
```

## In Our POC

The vector service wraps Qdrant's API:

```python
# app/services/vectordb.py
class VectorDBService:
    def __init__(self):
        self._collection = settings.qdrant_collection

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(url=settings.qdrant_host)
        return self._client

    async def create_collection(self):
        """Create collection with config from settings."""
        ...

    async def upsert_chunks(self, chunks, embeddings):
        """Store document chunks with embeddings."""
        ...

    async def search(self, query_vector, top_k=5, filter_condition=None):
        """Similarity search with optional metadata filter."""
        ...
```

### Configuration

```bash
# .env
QDRANT_HOST=http://localhost:6333
QDRANT_COLLECTION=genai-documents
QDRANT_DISTANCE=cosine
```

### API Endpoints Using Qdrant

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/rag/ingest` | Add documents to Qdrant |
| `POST /api/v1/rag/search` | Search Qdrant |
| `POST /api/v1/rag/query` | Full RAG (search + generate) |

## Qdrant Web UI

Qdrant includes a built-in web UI at `http://localhost:6333`:

```bash
# After starting Qdrant, open in browser
open http://localhost:6333
```

The UI lets you:
- Browse collections
- View points and vectors
- Run search queries interactively
- Inspect payloads and scores

## Performance Tuning

### HNSW Parameters

```python
from qdrant_client.http.models import HnswConfig

client.recreate_collection(
    collection_name="my-docs",
    vectors_config=models.VectorParams(
        size=384,
        distance=models.Distance.COSINE,
        hnsw_config=HnswConfig(
            m=32,              # Connections per node (default: 16)
            ef_construct=200,  # Build quality (default: 100)
        ),
    ),
)

# Search with ef (higher = more accurate, slower)
client.search(
    collection_name="my-docs",
    query_vector=[...],
    limit=5,
    search_params=models.SearchParams(hnsw_ef=200),
)
```

### Memory Optimization

- **Vectors**: Stored in memory by default (use `on_disk_payload=true` to reduce memory)
- **Payload**: Stored on disk by default
- **Index**: HNSW graph is in memory

## Common Commands

### List Collections

```python
print(client.get_collections())
```

### Delete a Collection

```python
client.delete_collection("my-documents")
```

### Delete Points by Filter

```python
client.delete(
    collection_name="my-documents",
    points_selector=models.FilterSelector(
        filter=models.Filter(
            must=[models.FieldCondition(key="category", match={"value": "temp"})]
        )
    ),
)
```

### Count Points

```python
count = client.scroll(
    collection_name="my-documents",
    limit=1,
    with_vectors=False,
    with_payload=False,
)
print(f"Total points: {count[1]}")
```

## Next Steps

- Review the [Vector Database Interaction](../architecture/vector-db-interaction.md) architecture doc for the full
  implementation
- Try the API endpoints to see Qdrant in action
