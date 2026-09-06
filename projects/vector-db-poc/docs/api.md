# API Guide — Usage and Contextual Meaning

This guide documents every API endpoint, what it does, and — just as
importantly — **what concept** it represents in the world of vector databases
and embeddings. For each endpoint you'll find:

- **Contextual meaning** — why the operation exists and where you encounter
  it in real vector search applications.
- **Key concepts demonstrated** — the underlying vector/ML principle.
- **Request/response examples** with real-world context.

---

All endpoints are under `/api/v1/`.

## API Lifecycle Overview

The API follows the **vector search lifecycle** — the sequence of steps that
any application using embeddings must perform:

```
┌──────────────────────────────────────────────────────────┐
│  1. Check service    →   GET  /api/v1/health              │
│  2. Generate vectors →   POST /api/v1/embed               │
│  3. Store vectors    →   POST /api/v1/documents/          │
│  4. Retrieve         →   POST /api/v1/search              │
│  5. List & inspect   →   GET  /api/v1/documents/          │
│  6. Clean up         →   DELETE /api/v1/documents/{id}   │
└──────────────────────────────────────────────────────────┘
```

Each endpoint maps to a **core concept in vector databases and embeddings**.
Below, every endpoint is documented with:

- **What it does** — the technical operation
- **Contextual meaning** — why the concept matters and where you encounter it
  in real applications
- **Key concepts demonstrated** — the vector/ML principles at play

---

## Health check

### Contextual meaning

A health endpoint verifies that the **service** and its **dependencies** are
ready to serve traffic. In a vector search system, this means confirming:

- The **embedding model** is loaded in memory (GPU/CPU tensors are initialized).
- The **vector database** (Qdrant) is reachable and responsive.
- The **collection** (Qdrant's equivalent of a table) exists or can be created on demand.

If any dependency is unavailable, the health endpoint reports a degraded state
so that callers (load balancers, Kubernetes probes, CI pipelines) can react
before serving failed requests.

### Key concepts demonstrated

- **Service readiness checks** in distributed systems
- **Dependency health** (database connectivity, model loading)
- **API versioning** (`/api/v1/`) for backward-compatible evolution

`GET /api/v1/health`

Returns the service status, Qdrant connectivity, the embedding model name,
and the embedding dimension.

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

### Contextual meaning

An **embedding** is a fixed-length vector of floating-point numbers that
represents the *semantic content* of a piece of text. The embed endpoint
transforms user text into this numerical representation so that it can be
compared with other embeddings using geometric distance — without ever
comparing the raw text itself.

Every modern vector search workflow follows the same pattern:

1. **Embed** the query the user typed.
2. **Embed** the documents you want to search over (done ahead of time).
3. **Compare** the query embedding against document embeddings using a
   similarity metric (cosine, dot product, Euclidean).

You rarely call `/embed` in production directly — the `/search` and
`/documents/` endpoints do it internally. However, calling `/embed`
explicitly is useful for:

- **Debugging** — inspecting the raw vector to understand what the model "sees".
- **Pre-computing** embeddings outside the API (e.g., in a batch job).
- **Experimenting** with different models and comparing their vector outputs.

### Key concepts demonstrated

- **Dense vector embeddings** — continuous real-valued vectors
- **Semantic representation** — meaning encoded in geometry
- **Model-specific dimensions** — `all-MiniLM-L6-v2` always produces 384-dim vectors
- **Stateless transformation** — the same input always yields the same output

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

### Contextual meaning

This endpoint implements the **ingestion** phase of a vector search system.
Ingestion is the process of:

1. Taking raw text (documents, articles, product descriptions, etc.).
2. Transforming it into embeddings using a model.
3. Storing the vector along with metadata in the vector database.

Once stored, the document can be **retrieved** later by semantic similarity —
a user can search for "fast web framework" and find a document that says
"FastAPI is a modern web framework" even though those exact words don't all
appear in the same query.

#### Chunk size and overlap

By default, each document is embedded as a **single vector**. For long
documents (e.g., a 10,000-character article), a single embedding loses
granularity — a search for a sentence buried in the middle of the document
may return a low similarity score because the embedding represents the
*entire* text, not the specific section.

Chunking splits the document into smaller, overlapping segments before
embedding. Each chunk becomes its own vector. This improves **retrieval
granularity** — a query about a specific section can match that chunk even if
other parts of the document are irrelevant.

### Key concepts demonstrated

- **Document ingestion** — the write path of a vector store
- **Metadata storage** — associating structured data (category, source, etc.)
  with each vector
- **Chunking** — splitting long text for more precise retrieval
- **Chunk overlap** — including context from neighboring chunks to reduce
  boundary-edge effects
- **Bulk vs. single** — the `/batch/` endpoint amortizes model loading and
  network round-trips

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

### Contextual meaning

Bulk ingestion optimises the ingestion pipeline for **throughput**. Instead of
making one HTTP round-trip per document, the client sends an array of
documents in a single request. The server:

1. Chunks each document (if `chunk_size` is provided).
2. Batches embeddings into a single call to the embedding model.
3. Writes all vectors to Qdrant in a single `upsert` operation.

This is how you would load a real document corpus: a background job reads
files from disk, calls `/batch/`, and the vectors are ready for search as soon
as the response returns.

### Key concepts demonstrated

- **Batch processing** — amortising model-loading and network overhead
- **Write efficiency** — single bulk write vs. many small writes
- **Per-document chunking parameters** — each document can specify its own
  `chunk_size` and `chunk_overlap`

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

### Contextual meaning

A document store needs discoverability — you need to know what is already
indexed before you can search or update it. This endpoint wraps Qdrant's
**scroll** API, which performs a forward scan through stored points.

In production, scroll-based listing is rarely the primary access pattern (you
usually search by content), but it is essential for:

- **Auditing** — verifying that documents were ingested correctly.
- **Pagination** — iterating over millions of vectors in batched pages.
- **Deletion targeting** — listing before deleting to confirm which
  documents will be affected.

### Key concepts demonstrated

- **Vector point iteration** — Qdrant's `scroll` API returns points in
  arbitrary order with a `next_page` cursor.
- **Pagination** — `limit` and `offset` prevent loading millions of vectors
  into memory at once.
- **Metadata inspection** — each result includes the document's metadata,
  making it possible to build admin UIs or debug indexing issues.

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

### Contextual meaning

Semantic search is the **retrieval** phase — the heart of any vector search
application. The workflow is:

1. The user submits a **query** (natural language text).
2. The query is embedded into the same vector space as the stored documents.
3. A **similarity metric** (cosine, Euclidean, dot product) compares the query
   vector against every stored vector.
4. The **top-K** most similar results are returned, ranked by similarity score.

This is fundamentally different from **keyword search** (e.g., Elasticsearch,
PostgreSQL `LIKE`), which matches literal tokens. Semantic search matches
*meaning* — a query for "feline pet" will find a document about "cats" because
their embeddings are geometrically close, even though no words overlap.

#### Score threshold

The `score_threshold` parameter lets you filter out low-confidence matches.
Similarity scores range from 0 to 1 (cosine); a threshold of `0.7` means "only
return results that are at least 70% similar to the query." This prevents
weak matches from cluttering the results — essential when building a
question-answering or recommendation system.

#### What happens without a collection?

If no documents have been ingested yet, the collection does not exist and the
endpoint returns `404`. This distinguishes "no documents have been added" from
"no results matched" — the former requires ingestion first, the latter is a
valid (empty) search result.

### Key concepts demonstrated

- **Embed-and-retrieve** pipeline — query embedding → similarity comparison
- **Cosine similarity** — the default metric for comparing embeddings
- **Top-K retrieval** — returning the K nearest neighbours
- **Score thresholding** — filtering by confidence
- **Metadata in results** — returning structured context alongside vectors

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

### Contextual meaning

Vector databases are **append-heavy** — writes (upserts) and reads (searches)
are optimised, but deletes require a **re-indexing** step that can be
expensive at scale. This endpoint uses Qdrant's **filter-based delete**, which
scans the payload for all points whose `doc_id` matches the given value and
removes them.

This is particularly important for **chunked documents**: when a document is
ingested with `chunk_size`, it is stored as multiple vectors (one per chunk).
A naive delete-by-ID would only remove one chunk, leaving **orphaned data**.
Filter-based delete ensures all chunks belonging to a document are removed in
a single operation.

### Key concepts demonstrated

- **Payload filtering** — deleting by metadata field value, not by point ID
- **Chunk cleanup** — ensuring all pieces of a chunked document are removed
- **Data lifecycle** — the "D" in "CRUD" for vector stores
- **Soft delete considerations** — in production you may mark documents as
  deleted rather than physically removing them (to avoid index rebuilds)

`DELETE /api/v1/documents/{doc_id}`

Deletes a document and all of its chunks.  Returns `204 No Content` on
success.

```bash
curl -X DELETE http://localhost:8000/api/v1/documents/doc-2
```

---

## Root endpoint

`GET /`

Returns basic service information. Useful for confirming the API gateway
is running and reachable before calling the versioned endpoints.

```bash
curl http://localhost:8000/
```

Response:

```json
{
  "message": "Vector DB POC",
  "docs": "/docs",
  "api": "/api/v1"
}
```
