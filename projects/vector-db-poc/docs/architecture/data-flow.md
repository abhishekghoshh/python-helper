# Data Flow — End-to-End Traces

This document traces the complete execution path for every major feature, showing exactly what code runs and in what order.

---

## Feature 1: Health Check (`GET /api/v1/health`)

```
Client
  │
  │ GET /api/v1/health
  ▼
FastAPI (app/main.py:5-9)
  │ app = FastAPI(...)
  │ app.include_router(router, prefix="/api/v1")
  ▼
Router (app/api/routes.py:39)
  │ @router.get("/health")
  │ Depends(get_embedding_service)
  ▼
get_embedding_service() (routes.py:22-26)
  │ _embedding_service is None → EmbeddingService(settings.embedding_model)
  │ → EmbeddingService.__init__(model_name="sentence-transformers/all-MiniLM-L6-v2")
  ▼
health() (routes.py:40-48)
  │ emb.dimension
  │   → EmbeddingService.dimension (embedding.py:27-31)
  │   → self.load() → SentenceTransformer(self.model_name) [first call only]
  │   → self.model.get_sentence_embedding_dimension() → 384
  │ try/except catches model load failures
  ▼
HealthResponse(status="ok", embedding_model="sentence-transformers/all-MiniLM-L6-v2")
  │
  ▼
Client ← {"status": "ok", "embedding_model": "..."}
```

**External calls:**
- HuggingFace Hub — downloads `all-MiniLM-L6-v2` model (~90MB) on first access

---

## Feature 2: Generate Embeddings (`POST /api/v1/embed?text=hello`)

```
Client
  │
  │ POST /api/v1/embed?text=hello+world
  ▼
Router (app/api/routes.py:51-57)
  │ @router.post("/embed")
  │ text: str (from query parameter)
  │ Depends(get_embedding_service)
  ▼
get_embedding_service() (routes.py:22-26)
  │ Returns cached _embedding_service (or creates new)
  ▼
embed() (routes.py:52-57)
  │ emb.embed(text)
  │   → EmbeddingService.embed() (embedding.py:15-19)
  │   → self.load() [already loaded after first call]
  │   → self.model.encode("hello world", convert_to_numpy=True)
  │   → vector.tolist() → [0.012, -0.045, ...] (384 floats)
  ▼
EmbeddingResponse(vector=[...], dimension=384)
  │
  ▼
Client ← {"vector": [0.012, -0.045, ...], "dimension": 384}
```

**Key details:**
- `convert_to_numpy=True` — returns a NumPy array, not a PyTorch tensor
- `.tolist()` — converts to Python list for JSON serialization
- The model is loaded once (lazy) and reused for all subsequent requests

---

## Feature 3: Add a Document (`POST /api/v1/documents/`)

```
Client
  │
  │ POST /api/v1/documents/
  │ Body: {"id": "doc-1", "text": "...", "metadata": {"category": "db"}}
  ▼
Router (app/api/routes.py:60-82)
  │ @router.post("/documents/", status_code=201)
  │ doc: DocumentCreate (Pydantic-validated)
  │ Depends(get_embedding_service) → emb
  │ Depends(get_vector_db_service) → vdb
  ▼
add_document() (routes.py:61-82)
  │
  ├─ vdb.create_collection()
  │   → VectorDBService.create_collection() (vector_db.py:22-30)
  │   → self.client.collection_exists("demo")
  │   → if not exists:
  │       self.client.recreate_collection(
  │           collection_name="demo",
  │           vectors_config=VectorParams(size=384, distance=Distance.COSINE)
  │       )
  │
  ├─ vector = emb.embed(doc.text)
  │   → EmbeddingService.embed() (embedding.py:15-19)
  │   → model.encode(text, convert_to_numpy=True).tolist()
  │   → [0.012, -0.045, ...] (384 floats)
  │
  ├─ payload = {"text": doc.text, "doc_id": doc.id, "category": "db"}
  │
  ├─ vdb.upsert([{id: "doc-1", vector: [...], payload: {...}}])
  │   → VectorDBService.upsert() (vector_db.py:32-45)
  │   → to_uuid("doc-1") → uuid.uuid5(NAMESPACE_DNS, "doc-1")
  │   → PointStruct(id=<uuid>, vector=[...], payload={...})
  │   → self.client.upsert(collection_name="demo", points=[PointStruct])
  │   → Qdrant stores the point
  │
  └─ return DocumentResponse(id="doc-1", text="...", metadata={"category": "db"})
  │   (metadata filters out "text" and "doc_id" keys)
  ▼
Client ← 201 Created
         {"id": "doc-1", "text": "...", "metadata": {"category": "db"}}
```

**External calls:**
- Qdrant REST/gRPC API — create collection, upsert point

**Data flow through Qdrant:**
```
Document (text) → Embedding (vector) → Payload (metadata) → Qdrant PointStruct
                 ↑                      ↑
            384 floats           {"text", "doc_id", "category"}
```

---

## Feature 4: Batch Add Documents (`POST /api/v1/documents/batch/`)

```
Client
  │
  │ POST /api/v1/documents/batch/
  │ Body: [{"id": "doc-2", "text": "...", ...}, {"id": "doc-3", ...}]
  ▼
Router (app/api/routes.py:85-103)
  │ docs: list[DocumentCreate]
  ▼
add_documents() (routes.py:86-103)
  │
  ├─ vdb.create_collection() [same as single add]
  │
  ├─ texts = [d.text for d in docs] → ["...", "..."]
  │
  ├─ vectors = emb.embed_batch(texts)
  │   → EmbeddingService.embed_batch() (embedding.py:21-25)
  │   → model.encode(["...", "..."], convert_to_numpy=True, show_progress_bar=False)
  │   → vectors.tolist() → [[...], [...]] (2 vectors, each 384 floats)
  │
  ├─ points = [{id, vector, payload}, ...]
  │   (one PointStruct per document)
  │
  ├─ count = vdb.upsert(points) → 2
  │   → QdrantClient.upsert() — single batch call for all points
  │
  └─ return {"inserted": 2, "ids": ["doc-2", "doc-3"]}
  ▼
Client ← 201 Created
         {"inserted": 2, "ids": ["doc-2", "doc-3"]}
```

**Key advantage of batch processing:**
- `embed_batch` uses a single `model.encode()` call for all texts (more efficient than calling `embed` multiple times)
- `vdb.upsert` sends all points in a single Qdrant API call

---

## Feature 5: Semantic Search (`POST /api/v1/search`)

```
Client
  │
  │ POST /api/v1/search?query=How+do+similarity+search+engines+work&top_k=3
  ▼
Router (app/api/routes.py:106-129)
  │ @router.post("/search")
  │ query: str, top_k: int = 5
  │ Depends(get_embedding_service) → emb
  │ Depends(get_vector_db_service) → vdb
  ▼
search() (routes.py:107-129)
  │
  ├─ if not vdb.client.collection_exists("demo"): raise 404
  │   → Checks if the collection exists before searching
  │
  ├─ query_vector = emb.embed(query)
  │   → EmbeddingService.embed("How do similarity search engines work")
  │   → [0.023, -0.012, ...] (384 floats)
  │
  ├─ results = vdb.search(query_vector, top_k=3)
  │   → VectorDBService.search() (vector_db.py:47-62)
  │   → self.client.search(
  │       collection_name="demo",
  │       query_vector=[0.023, ...],
  │       with_payload=True,
  │       with_vectors=False,
  │       limit=3
  │   )
  │   → Qdrant returns top-3 similar points:
  │       [{id: UUID, score: 0.82, payload: {"text": "...", "doc_id": "doc-1", ...}}, ...]
  │   → Simplified to [{id: str, score: float, payload: dict}, ...]
  │
  ├─ hits = [SearchHit(
  │     id=r["payload"]["doc_id"]  ← maps UUID back to original string ID
  │     text=r["payload"]["text"]
  │     score=round(r["score"], 4)
  │     metadata={k: v for k, v in payload if k not in ("text", "doc_id")}
  │   ) for r in results]
  │
  └─ return SearchResponse(query=query, hits=hits)
  ▼
Client ← 200 OK
         {"query": "...", "hits": [
           {"id": "doc-1", "text": "...", "score": 0.82, "metadata": {...}},
           ...
         ]}
```

**Key concepts in the search flow:**

1. **UUID → string ID mapping**: Qdrant stores points with UUID5 IDs, but the API returns the original string ID from the `doc_id` field in the payload.

2. **Score interpretation**: Scores are cosine similarity values in range [0, 1]. A score of 0.82 means the vectors point in similar directions (high semantic similarity).

3. **Payload reconstruction**: The document text and metadata are stored in the payload and returned with each search result — no separate document lookup is needed.

---

## Feature 6: Delete Document (`DELETE /api/v1/documents/{doc_id}`)

```
Client
  │
  │ DELETE /api/v1/documents/doc-2
  ▼
Router (app/api/routes.py:132-138)
  │ @router.delete("/documents/{doc_id}")
  │ doc_id: str = "doc-2"
  │ Depends(get_vector_db_service) → vdb
  ▼
delete_document() (routes.py:133-138)
  │
  ├─ vdb.delete(ids=["doc-2"])
  │   → VectorDBService.delete() (vector_db.py:64-69)
  │   → to_uuid("doc-2") → uuid.uuid5(NAMESPACE_DNS, "doc-2")
  │   → same UUID as when "doc-2" was upserted
  │   → PointIdsList(points=[str(uuid)])
  │   → QdrantClient.delete(collection_name="demo", points_selector=PointIdsList)
  │   → Qdrant removes the point
  │
  └─ return (204 No Content, empty body)
  ▼
Client ← 204 No Content
```

---

## Data stored in Qdrant

For each document added, Qdrant stores a **point** with this structure:

```
PointStruct
├── id: UUID5(NAMESPACE_DNS, "doc-1")  e.g., "a1b2c3d4-..."
├── vector: [0.012, -0.045, ..., 0.033]  (384 floats, COSINE distance)
└── payload:
    ├── text: "Vector databases store embeddings..."  (original document text)
    ├── doc_id: "doc-1"  (original string ID for mapping back)
    └── category: "database"  (user-provided metadata)
```

### Why store both `text` and `doc_id` in the payload?

- **`text`**: Stored so search results can return the original document content without a separate database lookup
- **`doc_id`**: Stored because Qdrant uses UUIDs internally; the original string ID is needed to map search results back to the user's identifiers, and to enable delete operations

### Collection configuration

The Qdrant collection is created with:

```python
qmodels.VectorParams(
    size=384,           # embedding_dim from settings
    distance=qmodels.Distance.COSINE,  # cosine similarity
)
```

- `size=384` must match the embedding model's output dimension
- `distance=COSINE` determines how similarity is computed during search