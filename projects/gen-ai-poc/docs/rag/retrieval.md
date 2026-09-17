# Retrieval: Similarity Search

Retrieval is the "R" in RAG — finding the most relevant document chunks
for a user's query.

## The Retrieval Flow

```mermaid
flowchart LR
    Q[User Question] --> QE[Query Embedding]
    QE --> VS[Vector Search]
    VS --> VDB[(Vector DB)]
    VDB --> Results[Ranked Results]
    Results --> TopK[Top-K Chunks]

    style Q fill:#3498db,color:#fff
    style QE fill:#9b59b6,color:#fff
    style VS fill:#e74c3c,color:#fff
    style VDB fill:#e74c3c,color:#fff
    style Results fill:#f39c12,color:#fff
    style TopK fill:#27ae60,color:#fff
```

## Step 1: Embed the Query

The user's question is converted to a vector using the **same embedding model**
used during document ingestion.

```python
# app/embeddings/service.py
query_embedding = await embedding_service.embed(question)
# → [0.23, -0.87, 0.45, 0.12, ...]  (384 dimensions)
```

**Critical**: The query and documents must use the same embedding model and
dimensions. Otherwise, the vector space is misaligned and similarity scores
are meaningless.

## Step 2: Vector Search

The query embedding is compared against all stored document embeddings:

```python
# app/services/vectordb.py
hits = await vector_db.search(
    query_vector=query_embedding,
    top_k=5,  # Return top-5 most similar
)
```

### What Happens Inside the Vector DB?

1. **Index lookup**: Qdrant uses the HNSW graph index to navigate the vector space
2. **Candidate selection**: Selects candidate vectors near the query
3. **Distance computation**: Calculates exact distances to candidates
4. **Ranking**: Sorts by similarity score (highest first)
5. **Filtering**: Optionally applies metadata filters

## Top-K Retrieval

**Top-K** refers to the number of most similar results to return:

| K | Use Case |
|---|----------|
| **1-3** | Very focused queries, small knowledge base |
| **5** | Standard (POC default) |
| **10-20** | Broader queries, large knowledge base |
| **50+** | Maximum recall, slower, larger context |

### Configuring Top-K

```bash
# .env
RAG_TOP_K=5
```

You can also override per-query:

```bash
# POST /api/v1/rag/query
{"question": "...", "top_k": 10}
```

## Similarity Scores

Each result includes a **similarity score**:

| Metric | Score Range | Higher = |
|--------|-------------|----------|
| Cosine | [-1, 1] | More similar |
| Euclidean | [0, ∞) | More similar (lower is better) |
| Dot product | (-∞, ∞) | More similar |

```python
# Example results
[
    SearchHit(id="chunk_1", score=0.89, text="..."),
    SearchHit(id="chunk_3", score=0.75, text="..."),
    SearchHit(id="chunk_2", score=0.68, text="..."),
]
```

## Metadata Filtering

You can constrain the search to specific metadata:

```python
# app/services/vectordb.py
hits = await vector_db.search(
    query_vector=query_embedding,
    top_k=5,
    filter_condition={"category": "technical"},
)
```

This combines **semantic search** (find by meaning) with **structured filtering**
(find by category, date, etc.) — called **hybrid search**.

## In Our POC

### The Retrieve Method

```python
# app/rag/retrieval.py
async def retrieve_context(
    question: str,
    vector_db_service,
    embedding_service,
    top_k: int | None = None,
) -> list[SearchHit]:
    # 1. Embed the query
    query_embedding = await embedding_service.embed(question)

    # 2. Search the vector DB
    hits = await vector_db_service.search(
        query_vector=query_embedding,
        top_k=top_k or settings.rag_top_k,
    )

    return hits
```

### API Endpoint

```bash
# POST /api/v1/rag/search
curl -X POST http://localhost:8000/api/v1/rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is machine learning?",
    "top_k": 5
  }'
```

Response:
```json
{
  "query": "What is machine learning?",
  "hits": [
    {"id": "chunk_1", "score": 0.89, "text": "...", "metadata": {...}},
    {"id": "chunk_3", "score": 0.75, "text": "...", "metadata": {...}}
  ],
  "collection": "genai-documents"
}
```

## Retrieval Quality

### Measuring Quality

| Metric | Description |
|--------|-------------|
| **Recall@K** | Fraction of true relevant docs found in top-K |
| **Precision@K** | Fraction of top-K results that are relevant |
| **Mean Reciprocal Rank (MRR)** | Rank of the first relevant result |
| **NDCG** | Normalized discounted cumulative gain |

### Improving Retrieval Quality

1. **Better embeddings** — use a higher-quality model
2. **Query expansion** — add synonyms to the query
3. **Re-ranking** — use a cross-encoder to re-rank top candidates
4. **Hybrid search** — combine vector + keyword search
5. **Query reformulation** — generate multiple queries and merge results

## Next Steps

- [Context Construction](context-construction.md) — How retrieved chunks become a prompt
- [Prompt Construction](prompt-construction.md) — How context guides LLM output
