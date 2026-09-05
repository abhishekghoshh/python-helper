# Metadata in Vector Databases

## What is metadata?

**Metadata** is structured data associated with a vector — information that describes the vector but is not part of the vector itself. In Qdrant, metadata is stored as **payload** alongside each vector point.

```
Point
├── id: "a1b2c3d4-..." (UUID5 of "doc-1")
├── vector: [0.012, -0.045, ...] (384 floats)
└── payload (metadata):
    ├── text: "Vector databases store embeddings..."
    ├── doc_id: "doc-1"
    └── category: "database"
```

## Why metadata is important

Without metadata, a vector database returns only vectors and similarity scores. You can't tell what the vectors represent — just how similar they are to your query. Metadata bridges the gap:

- **"What is this result?"** → `text` field in payload
- **"Where did it come from?"** → `source` or `doc_id` field
- **"What category does it belong to?"** → `category` field
- **"When was it created?"** → `created_at` field

## How metadata works in this project

### Storage

When a document is added via `POST /api/v1/documents/`, the payload is created in `app/api/routes.py:68`:

```python
payload = {"text": doc.text, "doc_id": doc.id, **(doc.metadata or {})}
```

This payload contains:
1. **`text`** — the original document text (so search results can return it without a separate lookup)
2. **`doc_id`** — the original string ID (because Qdrant uses UUIDs internally, this maps back)
3. **User-provided metadata** — any additional fields from the `DocumentCreate.metadata` dict

The payload is passed to Qdrant during upsert:

```python
# app/api/routes/vector_db.py:34-44
qmodels.PointStruct(
    id=str(to_uuid(p["id"])),
    vector=p["vector"],
    payload=p.get("payload", {}),
)
```

### Retrieval

During search, Qdrant returns the payload alongside each result:

```python
# app/services/vector_db.py:47-62
results = self.client.search(
    collection_name=self.collection_name,
    query_vector=vector,
    with_payload=True,   # ← include payload in results
    with_vectors=False,   # ← don't return the vector (saves bandwidth)
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

### Response formatting

The search endpoint maps payload fields back to the response schema:

```python
# app/api/routes.py:120-127
hits = [
    SearchHit(
        id=r["payload"].get("doc_id", r["id"]),
        text=r["payload"].get("text", ""),
        score=round(r["score"], 4),
        metadata={k: v for k, v in r["payload"].items() if k not in ("text", "doc_id")},
    )
    for r in results
]
```

This extracts:
- `id` from the `doc_id` payload field (maps UUID back to original ID)
- `text` from the `text` payload field
- `metadata` — all remaining payload fields (user metadata only)

## Metadata structure

### Current structure

In this project, each document's payload has this structure:

```json
{
  "text": "The original document text",
  "doc_id": "doc-1",
  "category": "database",
  "author": "John Doe"
}
```

| Field | Purpose | Origin |
|-------|---------|--------|
| `text` | Original document content for result display | Stored automatically |
| `doc_id` | Maps Qdrant UUID back to original string ID | Stored automatically |
| Other fields | User-defined metadata | From `DocumentCreate.metadata` |

### Metadata vs. payload

- **Metadata**: The user-provided data (e.g., `{"category": "database"}`)
- **Payload**: Everything stored in Qdrant, including `text` and `doc_id` + user metadata

The API separates these in responses: `text` and `doc_id` are top-level response fields, while user metadata is in the `metadata` field.

## Document IDs

### The UUID problem

Qdrant requires unique point IDs. While it accepts strings, UUIDs are preferred for:
- Uniqueness guarantees across distributed systems
- Predictable length (always 36 characters)
- Collision resistance

### UUID5 in this project

The project uses **UUID5** (SHA-1 based) to deterministically map string IDs to UUIDs:

```python
# app/services/vector_db.py:6-11
_NAMESPACE = uuid.NAMESPACE_DNS

def to_uuid(point_id: str) -> uuid.UUID:
    """Deterministically map an arbitrary string ID to a UUID5."""
    return uuid.uuid5(_NAMESPACE, point_id)
```

This means:
- `"doc-1"` → always the same UUID (e.g., `a1b2c3d4-...`)
- The same string ID will always overwrite/update the same point
- Delete operations work with the original string ID

### Alternatives

| ID strategy | Pros | Cons |
|-------------|------|------|
| **UUID5** (this project) | Deterministic, reversible, no mapping table | Verbose UUIDs in storage |
| UUID4 (random) | Guaranteed unique | Not deterministic — need a separate mapping |
| Sequential integers | Compact, indexable | Not distributed-friendly, predictable |
| User-provided strings | Human-readable | Potential collisions, length issues |

## Chunk IDs

If chunking is implemented in the future, each chunk of a document needs a unique ID that:
1. Is unique across all documents and chunks
2. Can be traced back to the original document
3. Preserves chunk ordering

A common approach: `UUID5(doc_id + "__" + str(chunk_index))`

This allows:
- Finding all chunks of a document via prefix matching
- Reassembling a document from its chunks
- Deleting all chunks of a document by computing chunk UUIDs

## Source information

For learning purposes, it would be useful to add a `source` field to metadata:

```python
# Enhanced payload
payload = {
    "text": doc.text,
    "doc_id": doc.id,
    "source": doc.source,  # e.g., "api", "pdf", "web"
    "chunk_index": i,      # for chunked documents
    **doc.metadata,
}
```

This enables questions like: "Which documents about 'database' came from API sources?"

## Filtering

Qdrant supports **payload filtering** — searching only within vectors that match certain metadata criteria. However, **this POC does not implement filtering** in its search endpoint.

To filter, the search method would need:

```python
# Hypothetical enhancement
results = self.client.search(
    collection_name=self.collection_name,
    query_vector=vector,
    with_payload=True,
    with_vectors=False,
    limit=top_k,
    # Add filter:
    filter=qmodels.Filter(
        must=[
            qmodels.FieldCondition(
                key="category",
                match=qmodels.MatchValue(value="database"),
            )
        ]
    ),
)
```

### Pre-filtering vs. Post-filtering

| Strategy | How it works | Performance | Trade-off |
|----------|-------------|-------------|-----------|
| **Pre-filtering** | Filter first, then search the filtered subset | Faster (fewer vectors to compare) | May miss relevant results removed by filter |
| **Post-filtering** | Search all, then filter results | Slower (compares all vectors) | May return fewer results than `top_k` |
| **Hybrid** | Combine both | Best of both | More complex to implement |

## Metadata indexing

In Qdrant, payload fields can be indexed for faster filtering. Indexed fields support:
- Fast equality lookups (`category = "database"`)
- Range queries (`date > "2024-01-01"`)
- Full-text search within payloads
- Geo-distance queries

Indexing is configured per-collection and adds storage overhead but speeds up filtered searches.

## Practical examples

### Store metadata

```bash
curl -X POST http://localhost:8000/api/v1/documents/ \
  -H "Content-Type: application/json" \
  -d '{
    "id": "doc-1",
    "text": "Vector databases store embeddings for fast similarity search.",
    "metadata": {"category": "database", "author": "Alice", "year": 2024}
  }'
```

### Retrieve with metadata

```bash
curl -X POST "http://localhost:8000/api/v1/search?query=similarity+search&top_k=3"
```

Response:
```json
{
  "query": "similarity search",
  "hits": [
    {
      "id": "doc-1",
      "text": "Vector databases store embeddings for fast similarity search.",
      "score": 0.82,
      "metadata": {"category": "database", "author": "Alice", "year": 2024}
    }
  ]
}
```

## Best practices

1. **Store the original text** in the payload so search results are self-contained
2. **Store the original document ID** to map back from internal UUIDs
3. **Use descriptive metadata keys** (e.g., `category` not `cat`)
4. **Index frequently-filtered fields** for better performance
5. **Avoid very large payloads** — they increase storage and slow down searches
6. **Consider structured vs. free-form** metadata — structured (key-value pairs) is easier to filter on