# API Routes — Learning Guide

## 1. What problem does it solve?

To expose the embedding and vector search capabilities as a **web API** that clients can interact with over HTTP. Without an API layer, the embedding and vector DB services are just Python modules — they need an HTTP interface to be usable by applications, web frontends, or automated systems.

## 2. Why is it required?

The API layer is the **interface** between the outside world and the internal services. It handles:

- **Request routing** — mapping URLs to handler functions
- **Request validation** — ensuring input data conforms to expected schemas
- **Response serialization** — converting Python objects to JSON
- **Dependency injection** — providing service instances to handlers
- **Error handling** — returning appropriate HTTP status codes

## 3. What concept does it demonstrate?

- **RESTful API design** — using HTTP methods (GET, POST, DELETE) and status codes
- **Pydantic request/response models** — automatic validation and serialization
- **FastAPI dependency injection** — `Depends()` for service lifecycle management
- **Singleton pattern** — reusing expensive service instances across requests
- **API schema design** — designing clean, consistent request/response shapes

## 4. How does it work internally?

### FastAPI routing

FastAPI uses a decorator-based routing system. Each endpoint is a function decorated with `@router.get()`, `@router.post()`, or `@router.delete()`:

```python
router = APIRouter()

@router.get("/health")
def health(...):
    return HealthResponse(...)
```

The `APIRouter` is registered in `app/main.py`:

```python
app.include_router(router, prefix="/api/v1")
```

This means all routes under the router are prefixed with `/api/v1`.

### Dependency injection

FastAPI's `Depends()` system allows declaring what dependencies a handler needs:

```python
def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(settings.embedding_model)
    return _embedding_service

@router.post("/embed")
def embed(
    text: str,
    emb: EmbeddingService = Depends(get_embedding_service),
):
    vector = emb.embed(text)
    return EmbeddingResponse(vector=vector, dimension=len(vector))
```

When a request comes in:
1. FastAPI sees `emb: EmbeddingService = Depends(get_embedding_service)`
2. It calls `get_embedding_service()` to get the instance
3. Injects the result into the `emb` parameter
4. The handler can use `emb` directly

The **singleton pattern** here means:
- The `SentenceTransformer` model is loaded only once (first request)
- The `QdrantClient` connection is reused across requests
- Subsequent requests reuse the already-initialized instances

### Request and response models

Every endpoint uses a **Pydantic model** as its `response_model`:

```python
@router.post("/embed", response_model=EmbeddingResponse)
def embed(text: str, emb: EmbeddingService = Depends(get_embedding_service)):
    ...
```

The `EmbeddingResponse` model:

```python
class EmbeddingResponse(BaseModel):
    vector: list[float]
    dimension: int
```

Pydantic automatically:
- **Validates** the input `text` parameter
- **Serializes** the returned `EmbeddingResponse` to JSON
- **Generates OpenAPI docs** (Swagger UI at `/docs`, ReDoc at `/redoc`)

### The six endpoints

#### `GET /api/v1/health`

Checks that the service is running and the embedding model can be loaded.

```python
@router.get("/health", response_model=HealthResponse)
def health(emb: EmbeddingService = Depends(get_embedding_service)):
    try:
        dim = emb.dimension
    except Exception:
        dim = 0
    return HealthResponse(
        status="ok",
        embedding_model=settings.embedding_model,
    )
```

**Design note:** The `try/except` catches errors from loading the model (e.g., model download failure). If the model fails to load, `dim` is set to 0 but the endpoint still returns `status="ok"`. This is a simplified health check — a production version would return a degraded status.

#### `POST /api/v1/embed`

Accepts a `text` query parameter and returns the embedding vector.

```python
@router.post("/embed", response_model=EmbeddingResponse)
def embed(
    text: str,
    emb: EmbeddingService = Depends(get_embedding_service),
):
    vector = emb.embed(text)
    return EmbeddingResponse(vector=vector, dimension=len(vector))
```

**Design note:** Using a query parameter (`?text=...`) rather than a request body is simple for testing with curl, but a request body would be more RESTful for a production API.

#### `POST /api/v1/documents/`

Creates the collection (if needed), generates an embedding, and stores the document.

```python
@router.post("/documents/", status_code=201, response_model=DocumentResponse)
def add_document(
    doc: DocumentCreate,
    emb: EmbeddingService = Depends(get_embedding_service),
    vdb: VectorDBService = Depends(get_vector_db_service),
):
    vdb.create_collection()
    vector = emb.embed(doc.text)
    payload = {"text": doc.text, "doc_id": doc.id, **(doc.metadata or {})}
    vdb.upsert([{"id": doc.id, "vector": vector, "payload": payload}])
    return DocumentResponse(
        id=doc.id,
        text=doc.text,
        metadata={k: v for k, v in payload.items() if k not in ("text", "doc_id")},
    )
```

**Key concepts:**
- `vdb.create_collection()` is called on every add — it's idempotent (checks if collection exists)
- The payload includes the document text (for retrieval during search) and the original ID (for mapping search results back to user IDs)
- The response metadata filters out `text` and `doc_id` since these are handled as separate fields

#### `POST /api/v1/documents/batch/`

Same as above but accepts a list of documents. Uses `embed_batch()` for efficient batch embedding.

#### `POST /api/v1/search`

Checks collection existence, embeds the query, searches, and returns formatted results.

```python
@router.post("/search", response_model=SearchResponse)
def search(
    query: str,
    top_k: int = 5,
    emb: EmbeddingService = Depends(get_embedding_service),
    vdb: VectorDBService = Depends(get_vector_db_service),
):
    if not vdb.client.collection_exists(settings.collection_name):
        raise HTTPException(404, "Collection does not exist. Add documents first.")
    query_vector = emb.embed(query)
    results = vdb.search(query_vector, top_k=top_k)
    hits = [SearchHit(
        id=r["payload"].get("doc_id", r["id"]),
        text=r["payload"].get("text", ""),
        score=round(r["score"], 4),
        metadata={k: v for k, v in r["payload"].items() if k not in ("text", "doc_id")},
    ) for r in results]
    return SearchResponse(query=query, hits=hits)
```

**Key concepts:**
- `collection_exists` check prevents errors when searching an empty database
- Search results map Qdrant UUIDs back to original document IDs via the `doc_id` payload field
- The `score` is rounded to 4 decimal places for cleaner output

#### `DELETE /api/v1/documents/{doc_id}`

Deletes a document by its original string ID.

```python
@router.delete("/documents/{doc_id}", status_code=204)
def delete_document(
    doc_id: str,
    vdb: VectorDBService = Depends(get_vector_db_service),
):
    vdb.delete(ids=[doc_id])
    return
```

**Design note:** Returns 204 (No Content) with an empty body, which is the standard for successful deletes.

## 5. Important schemas

### Request schemas

| Schema | Fields | Used by |
|--------|--------|---------|
| `DocumentCreate` | `id: str`, `text: str`, `metadata: dict` | POST /documents/, POST /documents/batch/ |

### Response schemas

| Schema | Fields | Used by |
|--------|--------|---------|
| `HealthResponse` | `status: str`, `qdrant: str`, `embedding_model: str` | GET /health |
| `EmbeddingResponse` | `vector: list[float]`, `dimension: int` | POST /embed |
| `DocumentResponse` | `id: str`, `text: str`, `score: float \| None`, `metadata: dict`, `vector: list[float] \| None` | POST /documents/ |
| `SearchHit` | `id: str`, `text: str`, `score: float`, `metadata: dict` | POST /search (in response) |
| `SearchResponse` | `query: str`, `hits: list[SearchHit]` | POST /search |

## 6. Alternatives

| Approach | Pros | Cons |
|----------|------|------|
| **FastAPI (this project)** | Auto-generated docs, async support, dependency injection, Pydantic validation | Learning curve for advanced features |
| **Flask/FastAPI** | Lightweight, minimal | Less built-in features |
| **Django REST Framework** | Batteries-included, admin panel | Heavier, less async-native |
| **Manual HTTP handling (http.server)** | No dependencies | Too low-level, reinventing wheels |

## 7. Trade-offs

- **Singleton services**: Reusing service instances saves memory and avoids re-downloading models, but means state persists across requests. For a stateless API, this is acceptable; for mutable global state, it can cause issues in concurrent scenarios.
- **Query parameters vs. request body**: Using `?text=...` for `/embed` is simple for testing but less RESTful. A POST with JSON body would be more consistent for a production API.
- **Error handling**: The current implementation lets most exceptions propagate as 500 errors. A production version would catch specific exceptions and return user-friendly error messages.
- **No authentication**: The POC has no auth. Production APIs should have API keys, OAuth, or session-based auth.