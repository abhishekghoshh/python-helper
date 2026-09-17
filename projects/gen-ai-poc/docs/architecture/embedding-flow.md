# Embedding Flow

This page details how text is converted into vectors and stored in the
vector database.

## The Embedding Flow

```mermaid
flowchart TD
    subgraph "Ingestion Phase"
        DOC1[Document] --> CHUNK1[Chunking]
        CHUNK1 --> TEXTS[List of text chunks]
        TEXTS --> BATCH[Batch Embedding]
        BATCH --> VECTORS[List of vector embeddings]
        VECTORS --> UPSERT[Upsert to Vector DB]
        UPSERT --> POINTS[(Stored Points)]
    end

    subgraph "Query Phase"
        Q[Question] --> EMBED[Single Embedding]
        EMBED --> QVEC[Query Vector]
        QVEC --> SEARCH[Vector Search]
        POINTS --> SEARCH
        SEARCH --> RESULTS[Ranked Results]
    end

    subgraph "External"
        MODEL[Embedding Model<br/>sentence-transformers]
        QDB[Qdrant Vector DB]
    end

    BATCH --> MODEL
    EMBED --> MODEL
    UPSERT --> QDB
    SEARCH --> QDB

    style DOCUMENTS fill=#3498db,color=#fff
    style Q fill=#3498db,color=#fff
    style VECTORS fill=#e74c3c,color=#fff
    style RESULTS fill=#27ae60,color=#fff
    style MODEL fill=#9b59b6,color=#fff
    style QDB fill=#f39c12,color=#fff
```

## Code Walkthrough

### Document to Chunks

```python
# app/rag/ingestion.py
def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - chunk_overlap
    return chunks

def chunk_document(document: Document) -> list[Chunk]:
    texts = chunk_text(document.content, ...)
    chunks = []
    for i, text in enumerate(texts):
        chunks.append(Chunk(
            id=f"{document.id}_chunk_{i}",
            text=text,
            document_id=document.id,
            chunk_index=i,
            metadata=document.metadata,
        ))
    return chunks
```

### Chunks to Vectors

```python
# app/embeddings/service.py
async def embed_many(self, texts: list[str]) -> list[list[float]]:
    """Batch embed multiple texts."""
    if isinstance(self.backend, _SentenceTransformersBackend):
        # Local model — batch encode
        vectors = await _run_in_thread(self.backend._model.encode, texts)
        return [v.tolist() for v in vectors]
    else:
        # OpenAI API — batch call
        response = await self.backend._client.embeddings.create(
            model=self.backend._model_name,
            input=texts,
        )
        data = sorted(response.data, key=lambda d: d.index)
        return [d.embedding for d in data]
```

### Vectors to Vector DB

```python
# app/services/vectordb.py
async def upsert_chunks(self, chunks: list[Chunk], embeddings: list[list[float]]) -> int:
    points = []
    for chunk, vector in zip(chunks, embeddings):
        payload = {
            "text": chunk.text,
            "document_id": chunk.document_id,
            "chunk_index": chunk.chunk_index,
            **chunk.metadata,
        }
        points.append(rest.PointStruct(
            id=chunk.id,
            vector=vector,
            payload=payload,
        ))

    self.client.upsert(
        collection_name=self._collection,
        points=points,
    )
```

### Query Vector Generation

```python
# app/rag/retrieval.py
async def retrieve_context(question: str, ...):
    query_embedding = await embedding_service.embed(question)
    hits = await vector_db.search(query_vector=query_embedding, top_k=5)
    return hits
```

## Batch vs. Single Embedding

### Ingestion (Batch)

```python
# Batch for efficiency
texts = [c.text for c in all_chunks]
embeddings = await embedding_service.embed_many(texts)
```

**Benefits**:
- Single call vs. N calls
- Better rate limit utilization
- Lower per-chunk cost (API)

### Query (Single)

```python
# Single for low latency
query_embedding = await embedding_service.embed(question)
```

**Benefits**:
- Faster response (no batching delay)
- Only one embedding needed

## Embedding Backend Architecture

```mermaid
graph TD
    ES[EmbeddingService] --> ST[sentence-transformers]
    ES --> OAI[OpenAI API]

    ST --> MODEL[all-MiniLM-L6-v2<br/>384 dimensions<br/>Local inference]
    OAI --> MODEL2[text-embedding-3-small<br/>1536 dimensions<br/>Cloud inference]

    style ES fill=#3498db,color=#fff
    style ST fill=#e74c3c,color=#fff
    style OAI fill=#f39c12,color=#fff
    style MODEL fill=#27ae60,color=#fff
    style MODEL2 fill=#27ae60,color=#fff
```

### Switching Backends

```python
# app/embeddings/service.py
class EmbeddingService:
    @property
    def backend(self):
        if self._backend is None:
            if settings.embedding_provider == "openai":
                self._backend = _OpenAIEmbeddingBackend()
            else:
                self._backend = _SentenceTransformersBackend()
        return self._backend
```

```bash
# .env
EMBEDDING_PROVIDER=sentence-transformers  # Local (default)
# or
EMBEDDING_PROVIDER=openai                  # Cloud
```

## Vector Storage Details

### Qdrant Point Structure

Each stored point in Qdrant contains:

```json
{
  "id": "doc_001_chunk_0",
  "vector": [0.23, -0.87, 0.45, ...],  // 384 floats
  "payload": {
    "text": "Machine learning is a subset of AI...",
    "document_id": "doc_001",
    "chunk_index": 0,
    "category": "AI",
    "source": "lecture_notes"
  }
}
```

### What Gets Stored

| Field | Source | Purpose |
|-------|--------|---------|
| `vector` | Embedding model | Similarity search |
| `text` | Chunk text | Return to user |
| `document_id` | Document ID | Provenance |
| `chunk_index` | Chunking step | Ordering |
| Metadata | User-provided | Filtering |

## Distance Metric Impact

The collection's distance metric affects how similarity is computed:

| Metric | Stored As | Search Behavior |
|--------|-----------|----------------|
| Cosine | Cosine similarity | Direction-based (ignores magnitude) |
| Euclidean | L2 distance | Geometric distance |
| Dot product | Inner product | Magnitude + direction |

```python
# app/services/vectordb.py
vectors_config=rest.VectorParams(
    size=settings.embedding_dimensions,
    distance=self._distance(),  # Cosine in POC
)
```

## Next Steps

- [Vector DB Interaction](vector-db-interaction.md)
- [RAG Flow](rag-flow.md)
- [Data Flow](data-flow.md)
