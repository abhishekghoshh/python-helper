# API Guide

All endpoints are under `/api/v1/`.

## Health check

`GET /api/v1/health`

Returns the service status and the name of the embedding model.

```bash
curl http://localhost:8000/api/v1/health
```

Response:

```json
{
  "status": "ok",
  "qdrant": "connected",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
}
```

## Generate embeddings

`POST /api/v1/embed`

Accepts form-urlencoded or query parameter `text`. Returns the dense vector.

```bash
curl -X POST "http://localhost:8000/api/v1/embed?text=What is a vector database"
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

Stores a document (its text embedding + metadata) in Qdrant.

```bash
curl -X POST http://localhost:8000/api/v1/documents/ \
  -H "Content-Type: application/json" \
  -d '{"id": "doc-1", "text": "Vector databases store embeddings for fast similarity search.", "metadata": {"category": "database"}}'
```

## Add documents in bulk

`POST /api/v1/documents/batch/`

Accepts a JSON array of documents and ingests them in a single upsert.

```bash
curl -X POST http://localhost:8000/api/v1/documents/batch/ \
  -H "Content-Type: application/json" \
  -d '[
    {"id": "doc-2", "text": "FastAPI is a modern web framework for Python.", "metadata": {"category": "framework"}},
    {"id": "doc-3", "text": "Semantic search finds results based on meaning rather than keywords.", "metadata": {"category": "search"}}
  ]'
```

Response:

```json
{
  "inserted": 2,
  "ids": ["doc-2", "doc-3"]
}
```

## Semantic search

`POST /api/v1/search`

Embeds the query and returns the most similar documents by cosine similarity.

```bash
curl -X POST "http://localhost:8000/api/v1/search?query=How do similarity search engines work&top_k=3"
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

## Delete a document

`DELETE /api/v1/documents/{doc_id}`

```bash
curl -X DELETE http://localhost:8000/api/v1/documents/doc-2
```
