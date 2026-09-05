# Project Review

A comprehensive summary of the Vector DB POC — its architecture, the improvements
made, and a structured checklist of learning outcomes.

---

## 1. Existing Project Understanding

### What the project originally did

The Vector DB POC is a minimal FastAPI service that demonstrates the core
building blocks of a vector search system:

1. **Embedding generation** — Uses `sentence-transformers/all-MiniLM-L6-v2`
   to convert text into 384-dimensional dense vectors.
2. **Vector storage** — Stores vectors (with metadata) in Qdrant, a
   purpose-built vector database.
3. **Semantic search** — Embeds a user query and retrieves the most
   similar stored vectors by cosine similarity.

The original project had three API endpoints (`/health`, `/embed`, `/` root)
plus document ingestion (`/documents/`, `/documents/batch/`), search
(`/search`), and deletion (`DELETE /documents/{id}`).

### How the architecture works

```text
┌──────────────┐     ┌──────────┐     ┌──────────────────┐     ┌────────┐
│  HTTP Client  │ ──► │  FastAPI  │ ──► │  API Router      │ ──► │  App   │
└──────────────┘     └──────────┘     └──────────────────┘     └────────┘
                                                       │
                            ┌──────────────────────────┼──────────────────────────┐
                            │                          │                          │
                            ▼                          ▼                          ▼
                    ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
                    │  Embedding   │          │ Vector DB    │          │ Config       │
                    │  Service     │          │ Service       │          │ (Settings)   │
                    └──────────────┘          └──────────────┘          └──────────────┘
                            │                          │
                            ▼                          ▼
                    ┌──────────────┐          ┌──────────────┐
                    │  Sentence-   │          │   Qdrant      │
                    │  Transformers│          │   Container   │
                    └──────────────┘          └──────────────┘
```

- **Client** sends HTTP requests (REST API or web UI).
- **FastAPI** routes requests to the appropriate endpoint.
- **Embedding Service** loads a `SentenceTransformer` model and encodes text
  into vectors.
- **Vector DB Service** wraps the Qdrant client, managing collections, point
  storage, similarity search, and metadata filtering.
- **Qdrant** runs as a Docker container, persisting vectors to disk.

### How embeddings are generated

1. The `EmbeddingService` lazily loads a `SentenceTransformer` model on first
   use.
2. `model.encode(text)` converts text to a NumPy array.
3. The array is converted to a Python list of floats (the embedding vector).
4. The default model (`all-MiniLM-L6-v2`) produces 384-dimensional vectors.

### How vectors are stored

1. Documents are converted to `PointStruct` objects with a UUID5 ID
   (deterministic hash of the string ID).
2. Each point carries the embedding vector and a payload dict containing the
   original text, `doc_id`, `chunk_index`, and user-supplied metadata.
3. Points are upserted into a Qdrant collection configured with the
   `COSINE` distance metric.

### How vector search works

1. The query string is embedded using the same `SentenceTransformer` model.
2. Qdrant performs an approximate nearest-neighbor (HNSW) search against the
   collection, ranking points by cosine similarity.
3. Results are sorted by relevance score and returned as a list of hits with
   text, score, and metadata.

---

## 2. Improvements Made

### Changes overview

| Change | Reason | Files Changed | Impact |
|--------|--------|---------------|--------|
| Poetry migration | Replace fragile pip requirements files with a modern lock-file-based dependency manager | `pyproject.toml`, `poetry.lock` (new); `requirements*.txt` (deleted) | Reproducible dependencies; dev/docs groups; PEP 621 standard |
| Dockerfile.docs + docker-compose docs service | Serve MkDocs documentation in a container for consistency | `Dockerfile.docs` (new); `docker-compose.yml` (modified) | Documentation is Dockerized, runs on port 8001 |
| Document chunking | Long documents need to be split into manageable pieces for better retrieval precision | `app/services/chunking.py` (new); `app/api/routes.py` (modified); `app/models/schemas.py` (modified) | Documents can be chunked with configurable `chunk_size` and `chunk_overlap` |
| Configurable similarity metric | Allow choosing between cosine, euclidean, and dot-product distance | `app/config.py` (modified); `app/services/vector_db.py` (modified) | `QDRANT_DISTANCE` env var controls the collection's distance metric |
| Score threshold in search | Filter out low-quality matches | `app/api/routes.py` (modified); `app/services/vector_db.py` (modified); `app/models/schemas.py` (modified) | Search results can be filtered by minimum similarity score |
| List documents endpoint | Inspect stored documents and their metadata | `app/api/routes.py` (modified); `app/models/schemas.py` (modified) | `GET /documents/` with pagination via `limit`/`offset` |
| Filter-based document deletion | Chunked documents have multiple point IDs; need payload filter to delete all chunks | `app/services/vector_db.py` (modified); `app/api/routes.py` (modified) | `DELETE /documents/{id}` removes all chunks of a document |
| Health endpoint enhancement | Report embedding dimension and Qdrant status | `app/api/routes.py` (modified); `app/models/schemas.py` (modified) | `/health` returns `embedding_dim` and `qdrant` status |
| SearchRequest / EmbeddingRequest models | Proper POST body parsing (fixes 422 errors) | `app/models/schemas.py` (modified); `app/api/routes.py` (modified) | Endpoints accept JSON bodies correctly |
| `ensure_collection` method | Idempotent collection creation for tests and initialization | `app/services/vector_db.py` (modified) | Safe to call before upsert/search |
| Comprehensive documentation | 30+ doc files covering theory, architecture, interviews | `docs/concepts/*.md`, `docs/vector-databases/*.md`, `docs/interview/*.md`, `docs/architecture/*.md` (new) | Self-learning resource for vector embeddings and vector databases |
| Test suite expansion | Cover new features and edge cases | `tests/conftest.py`, `tests/test_chunking.py`, `tests/test_routes.py` (modified) | 20 tests: 9 unit (chunking) + 11 integration (API) |

---

## 3. Remaining Improvements

### Must have (P0)

| Improvement | Why | Complexity |
|-------------|-----|------------|
| Async embedding model loading | The `EmbeddingService` loads the model synchronously on first request, blocking subsequent requests. Making it async (or pre-loading at startup) would eliminate the first-request cold start. | Medium |

### Should have (P1)

| Improvement | Why | Complexity |
|-------------|-----|------------|
| Model caching / singleton verification | Confirm the `EmbeddingService` singleton is truly shared across requests (it is, but a test for concurrency would help). | Low |
| Pagination tests for list_documents | The `offset` parameter isn't tested. | Low |
| Distance metric integration test | Verify that euclidean and dot-product distances produce different results. | Low |

### Nice to have (P2–P3)

| Improvement | Why | Complexity |
|-------------|-----|------------|
| Multiple embedding models | Allow switching between models (e.g., MiniLM vs. all-mpnet-base-v2) to compare dimensions and search quality. | Medium |
| Document deletion by filter | Delete documents by metadata (e.g., `WHERE category = 'database'`). | Low |
| Re-embedding on model change | If the embedding model is swapped, existing vectors become incompatible. A migration script would re-embed all documents. | High |

---

## 4. Learning Outcomes

By completing this project, you should now understand:

### Vectors and Embeddings

- [x] What vectors are — ordered arrays of numbers representing direction and magnitude
- [x] What embeddings are — dense vector representations of data (text, images) that capture semantic meaning
- [x] How embedding models work — tokenization → transformer → pooling → fixed-size vector
- [x] Embedding dimensions — `all-MiniLM-L6-v2` produces 384-dim vectors
- [x] Dense vs sparse vectors — dense has many non-zero values; sparse has mostly zeros
- [x] Semantic similarity vs keyword similarity — embeddings capture meaning, not just exact word matches

### Similarity and Distance Metrics

- [x] Cosine similarity — measures angle between vectors, independent of magnitude
- [x] Euclidean distance — measures straight-line distance in vector space
- [x] Manhattan distance — sum of absolute differences (L1 norm)
- [x] Dot product — sum of element-wise products; equivalent to cosine for normalized vectors
- [x] Why cosine is popular for embeddings — magnitude-invariant, ideal for normalized vectors
- [x] Vector normalization — scaling vectors to unit length

### Vector Databases

- [x] What a vector database is — stores and queries vector embeddings with similarity search
- [x] Why use a vector database — efficient ANN search, metadata filtering, persistence
- [x] Vector indexing — HNSW, IVF, Product Quantization
- [x] ANN (Approximate Nearest Neighbor) — trades accuracy for speed
- [x] HNSW — graph-based ANN algorithm
- [x] IVF — clustering-based ANN algorithm
- [x] Product Quantization — compresses vectors to reduce memory

### Search and Retrieval

- [x] Nearest-neighbor search — finding the k most similar vectors
- [x] Top-K search — returning the k best matches
- [x] Score thresholds — filtering results by minimum similarity
- [x] Metadata filtering — pre-filtering, post-filtering, hybrid search
- [x] Reciprocal Rank Fusion — combining keyword and vector scores

### Architecture and Design

- [x] Document chunking — splitting long documents for better retrieval
- [x] Chunk overlap — sharing text between consecutive chunks
- [x] RAG (Retrieval-Augmented Generation) architecture
- [x] Embedding model selection criteria
- [x] Scaling strategies for vector search

### Production and Operations

- [x] Configuration via environment variables (.env)
- [x] Docker-based deployment
- [x] Health check endpoints
- [x] Testing strategies for vector search systems

### Interview Preparation

- [x] Vectors and embeddings fundamentals
- [x] Similarity search concepts
- [x] Vector database internals
- [x] System design for semantic search at scale
- [x] Embedding model migration strategies
