# API Guide

All endpoints are under `/api/v1/`.

## Health check

`GET /api/v1/health`

Returns the service status, Qdrant connectivity, the embedding model name,
and the embedding dimension.

```bash
curl http://localhost:8000/api/v1/health
```

Response:

```json
{
  "status": "ok",
  "qdrant": "connected",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "embedding_dim": 384
}
```

## Generate embeddings

`POST /api/v1/embed`

Accepts a JSON request body with a `text` field. Returns the dense embedding
vector.

```bash
curl -X POST http://localhost:8000/api/v1/embed \
  -H "Content-Type: application/json" \
  -d '{"text": "What is a vector database"}'
```

Response:

```json
{
  "vector": [0.012, -0.045, ...],
  "dimension": 384
}
```

## Add a document

`POST /api/v1/documents/`

Stores a document's text embedding and metadata in Qdrant.

By default each document is embedded as a single vector.  For long documents,
provide `chunk_size` (and optionally `chunk_overlap`) to split the text into
overlapping chunks before embedding — improving retrieval granularity.

```bash
# Single vector (no chunking)
curl -X POST http://localhost:8000/api/v1/documents/ \
  -H "Content-Type: application/json" \
  -d '{"id": "doc-1", "text": "Vector databases store embeddings for fast similarity search.", "metadata": {"category": "database"}}'

# With chunking (long document split into 500-char chunks, 50-char overlap)
curl -X POST http://localhost:8000/api/v1/documents/ \
  -H "Content-Type: application/json" \
  -d '{"id": "doc-2", "text": "...very long text...", "metadata": {"source": "manual"}, "chunk_size": 500, "chunk_overlap": 50}'
```

Response:

```json
{
  "id": "doc-1",
  "text": "...",
  "metadata": {"category": "database"},
  "inserted_chunks": 1
}
```

For chunked documents, `inserted_chunks` shows how many vectors were created.
Each chunk is stored as a separate point; all chunks of the same document
share the same `doc_id` in the payload so they can be deleted together.

## Add documents in bulk

`POST /api/v1/documents/batch/`

Accepts a JSON array of documents.  Chunking parameters can be specified
per-document.

```bash
curl -X POST http://localhost:8000/api/v1/documents/batch/ \
  -H "Content-Type: application/json" \
  -d '[
    {"id": "doc-2", "text": "FastAPI is a modern web framework.", "metadata": {"category": "framework"}},
    {"id": "doc-3", "text":"Semantic search finds results by meaning.", "metadata": {"category": "search"}, "chunk_size": 100, "chunk_overlap": 20}
  ]'
```

Response:

```json
{
  "inserted": 3,
  "ids": ["doc-2", "doc-3"]
}
```

`inserted` is the total number of vector points written (chunks included).

## List documents

`GET /api/v1/documents/`

Returns all stored document chunks with their metadata.  Supports `limit` and
`offset` for pagination.

```bash
curl "http://localhost:8000/api/v1/documents/?limit=100"
```

Response:

```json
{
  "count": 2,
  "documents": [
    {"id": "doc-1", "text": "...", "metadata": {"category": "database"}},
    {"id": "doc-3", "text": "...", "metadata": {"category": "search"}}
  ],
  "next_page": null
}
```

## Semantic search

`POST /api/v1/search`

Embeds the query text and returns the most similar document chunks by
cosine similarity.

Optional parameters:

- `top_k` — maximum number of results (default 5)
- `score_threshold` — minimum similarity score; results below this are
  filtered out (default: no filtering)

```bash
# Basic search
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "How do similarity search engines work", "top_k": 3}'

# With score threshold
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "vector database", "top_k": 5, "score_threshold": 0.3}'
```

Response:

```json
{
  "query": "How do similarity search engines work",
  "hits": [
    {
      "id": "doc-1",
      "text": "Vector databases store embeddings for fast similarity search.",
      "score": 0.82,
      "metadata": {"category": "database"}
    }
  ]
}
```

If the Qdrant collection does not exist, the endpoint returns `404`.

## Delete a document

`DELETE /api/v1/documents/{doc_id}`

Deletes a document and all of its chunks.  Returns `204 No Content` on
success.

```bash
curl -X DELETE http://localhost:8000/api/v1/documents/doc-2
```
