# Document Chunking

## Why chunking matters

When working with documents that are longer than an embedding model's maximum context length (or when you want to retrieve specific sections rather than entire documents), you need to **chunk** the text — split it into smaller pieces, each of which is independently embedded.

### The problem without chunking

In the **current implementation**, each document is embedded as a single unit:

```python
# app/api/routes.py:60-82
@router.post("/documents/")
def add_document(doc: DocumentCreate, ...):
    vector = emb.embed(doc.text)  # entire text as one vector
    payload = {"text": doc.text, "doc_id": doc.id, **(doc.metadata or {})}
    vdb.upsert([{"id": doc.id, "vector": vector, "payload": payload}])
```

This has several limitations:

1. **Context length limits**: `all-MiniLM-L6-v2` has a max sequence length of 256 tokens. Documents longer than this are **truncated** by the model, losing information.
2. **Coarse retrieval**: Searching returns entire documents, not relevant passages. A 10-page document that mentions the query topic once will be returned as a match, even if only a small section is relevant.
3. **No partial matching**: You can't retrieve a specific section of a long document.

### Why chunking is critical for RAG

In **Retrieval-Augmented Generation (RAG)**, the retrieved documents are passed as context to an LLM. The LLM has a limited context window. Chunked documents allow:

- Retrieving only the most relevant passages (not entire documents)
- Fitting more retrieved content into the LLM's context window
- Providing more precise context to the LLM
- Reducing LLM hallucination by grounding in specific text

### The embedding model context limit

The `all-MiniLM-L6-v2` model used in this project processes up to 256 tokens. The `encode()` method handles truncation automatically:

```python
# app/services/embedding.py:18
vector = self.model.encode(text, convert_to_numpy=True)
```

If `text` exceeds 256 tokens, only the first 256 tokens are encoded — the rest is silently ignored. This means:
- A 500-word document is effectively embedded using only the first ~150 words
- Critical information at the end of the document is lost
- Search results may miss relevant documents

Chunking solves this by splitting long documents into chunks that fit within the context limit.

## Chunking strategies

### 1. Fixed-size chunking

Split text into chunks of exactly N characters or tokens, regardless of content.

```
Text: "The cat sat on the mat. The dog ran in the park. Birds flew overhead."
Chunk size: 30 characters

Chunk 1: "The cat sat on the mat. "
Chunk 2: "The dog ran in the park. "
Chunk 3: "Birds flew overhead."
```

**Pros:** Simple, predictable, fast.
**Cons:** Can cut words/sentences in half, no respect for document structure.

### 2. Recursive (hierarchical) chunking

Split by larger units first (paragraphs), then sentences, then words, falling back to smaller units as needed.

```
Text: "Para 1. Para 2."

Split by paragraph → ["Para 1.", "Para 2."]
If chunk still > max_size, split by sentence → ["Sent 1.", "Sent 2."]
If still > max_size, split by word
```

**Pros:** Respects document structure, more natural chunks.
**Cons:** More complex, varies chunk sizes.

### 3. Semantic chunking

Use a model to identify natural boundaries (topic changes, sentence boundaries) and split at semantically coherent points.

```
Text: "Topic A discussion. Topic A more. Topic B discussion."

Semantic chunk 1: "Topic A discussion. Topic A more."
Semantic chunk 2: "Topic B discussion."
```

**Pros:** Most natural chunks, preserves topic coherence.
**Cons:** Requires additional models, slower, more complex.

### 4. Sliding window

Create overlapping chunks by sliding a window across the text.

```
Chunk size: 200, overlap: 50

Chunk 1: tokens 1-200
Chunk 2: tokens 150-350
Chunk 3: tokens 300-500
...
```

**Pros:** No information lost at chunk boundaries, captures context across chunks.
**Cons:** Duplicate embeddings (same text embedded multiple times), increased storage.

## Chunk overlap

**Chunk overlap** is the number of tokens/characters shared between consecutive chunks. It prevents:

1. **Boundary truncation**: A concept that spans two chunks won't be fully captured in either.
2. **Information loss**: Important details near chunk boundaries won't be missed.

```
Chunk 1: [words 1-200]
Overlap:  [words 150-200]
Chunk 2:        [words 150-350]
```

A typical overlap is 10-20% of the chunk size. For example, with 256-token chunks and 20% overlap, you'd use ~307 effective context with ~50 overlapping tokens.

## Recommended defaults

| Parameter | Small docs | Large docs | Reason |
|-----------|-----------|-----------|--------|
| Chunk size | 256-512 tokens | 500-1000 tokens | Smaller = more precise; larger = more context |
| Chunk overlap | 32-64 tokens | 50-100 tokens | 10-20% of chunk size |
| Chunking method | Recursive | Semantic or recursive | Semantic for complex docs, recursive for mixed content |

## Current implementation status

### What this project does

The current `add_document` and `add_documents` endpoints embed each document as a single vector:

```python
# app/api/routes.py:67-68
vector = emb.embed(doc.text)
payload = {"text": doc.text, "doc_id": doc.id, **(doc.metadata or {})}
```

There is **no chunking** — the entire `doc.text` is passed to `model.encode()`, which will truncate at 256 tokens.

### What should be added

A `chunk_text` utility function that splits text into chunks before embedding:

```python
def chunk_text(text: str, chunk_size: int = 256, chunk_overlap: int = 32) -> list[str]:
    """Split text into chunks for embedding."""
    # Implementation: recursive chunking by sentences
    ...
```

Each chunk would become a separate Qdrant point with:
- `id`: UUID5 of `doc_id + chunk_index` (e.g., `"doc-1__0"`, `"doc-1__1"`)
- `vector`: the chunk's embedding
- `payload`: `{"text": chunk, "doc_id": doc.id, "chunk_index": i, ...metadata}`

### Impact on search

With chunking, a single document becomes multiple points in Qdrant. Search results would return individual chunks, not entire documents. The search response would need to be updated to group chunks by `doc_id` if document-level results are desired.

### Impact on the API

The `add_document` and `add_documents` endpoints would gain optional `chunk_size` and `chunk_overlap` query parameters:

```
POST /api/v1/documents/?chunk_size=256&chunk_overlap=32
```

When `chunk_size` is omitted, the current behavior (no chunking) is preserved for backward compatibility.

## Trade-offs of chunking

| Decision | Trade-off |
|----------|-----------|
| **Chunk size** | Smaller chunks = more precise retrieval but more storage; larger chunks = more context but less precise |
| **Chunk overlap** | More overlap = less boundary loss but higher storage cost; less overlap = cheaper but risk of missing info |
| **Chunking on/off** | Chunking enables large document support but adds complexity; no chunking is simpler but truncates |
| **Chunk ID strategy** | UUID5(`doc_id + index`) = deterministic and reversible; separate IDs = simpler but need mapping table |