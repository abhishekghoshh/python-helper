# Approximate Nearest Neighbor Search (ANN)

## What is nearest-neighbor search?

Given a query vector **q** and a collection of N stored vectors, **nearest-neighbor search** finds the K vectors that are most similar to the query (where K is typically small, like 5 or 10).

```
Query: "How do I reset my password?" → vector_q

Stored vectors:
  v1: "Password reset instructions"      → 0.85 similarity
  v2: "Account security settings"        → 0.72 similarity
  v3: "How to install software"          → 0.11 similarity
  v4: "Change your passcode"             → 0.81 similarity
  ...

Top-K=2 nearest neighbors: v1, v4
```

## What is approximate nearest-neighbor (ANN)?

**Exact nearest-neighbor search** compares the query against every vector — O(N) per query. **Approximate nearest-neighbor (ANN)** search uses indexing structures to find results that are *very likely* the nearest, but not guaranteed.

### Why approximation is necessary

As datasets grow, exact search becomes prohibitively slow:

| Vectors | Exact search time (1μs per comparison) | ANN search time |
|---------|----------------------------------------|-----------------|
| 1,000 | 1 ms | ~1 ms |
| 100,000 | 100 ms | ~5 ms |
| 10,000,000 | 10 seconds | ~50 ms |
| 1,000,000,000 | ~17 minutes | ~800 ms |

ANN achieves sub-linear search time (roughly O(log N)) by examining only a small fraction of vectors.

## How ANN works (simplified)

### Brute-force (exact)

```
Query vector
  │
  ├── Compare against vector 1 → score
  ├── Compare against vector 2 → score
  ├── Compare against vector 3 → score
  ├── ... (millions of comparisons)
  ├── Compare against vector N → score
  │
  └── Return top-K by score
```

### HNSW (approximate)

```
Query vector
  │
  ├── Enter graph at top layer
  ├── Navigate graph: follow nearest neighbor links
  ├── Descend to lower layers (more connections)
  ├── Explore candidates in ef-sized list
  │
  └── Return top-K from candidate list (not all vectors)
```

HNSW typically examines only 10–50 vectors to find the top-K, regardless of dataset size.

## Key metrics

### Recall

**Recall** measures how many of the true nearest neighbors the ANN search actually found:

```
recall@K = |true_top_K ∩ ann_top_K| / K

Example: K=5
True nearest: [A, B, C, D, E]
ANN returned: [A, C, D, F, G]
recall@5 = |{A, C, D}| / 5 = 3/5 = 60%
```

### Precision

**Precision** measures how many of the returned results are actually relevant:

```
precision@K = |true_top_K ∩ ann_top_K| / K

(Same as recall@K when both are top-K)
```

### Latency

**Latency** is the time from query to result. ANN trades a small amount of recall for significant latency improvements.

### Trade-off: recall vs. latency

| Configuration | Recall | Latency |
|---------------|--------|---------|
| Flat (exact) | 100% | High |
| HNSW (default) | ~95% | Low |
| HNSW (high ef) | ~99% | Medium |
| IVF (low nprobe) | ~80% | Very low |
| IVF (high nprobe) | ~90% | Low |

## Why approximate search is used

1. **Speed**: Sub-linear search time enables interactive applications
2. **Cost**: Less computation per query = lower infrastructure costs
3. **Scalability**: Can handle billions of vectors
4. **Diminishing returns**: Going from 95% to 100% recall often requires 10x more computation

For most applications, 95% recall is perfectly acceptable. A search that returns results in 50ms with 95% recall is far more useful than one that takes 5 seconds with 100% recall.

## Interview discussion: How to search billions of embeddings?

### Q: How would you build a system to search through billions of embeddings efficiently?

### A: Several approaches, depending on requirements:

#### Approach 1: Distributed vector database

```
1. Use Milvus or Vespa (designed for billions of vectors)
2. Shard vectors across multiple nodes
3. Each node runs HNSW on its shard
4. Query fans out to all shards in parallel
5. Merge and rank results across shards

Estimated: ~100ms latency, 95% recall, 1B vectors
```

#### Approach 2: Two-stage retrieval

```
Stage 1: Coarse filtering (fast, low recall)
  - Use a lightweight model to reduce candidates (e.g., BM25 or a small neural model)
  - Reduces 1B → 100K candidates

Stage 2: Fine-grained search (slower, high recall)
  - Use the full embedding model + HNSW on the 100K candidates
  - Returns final top-K results

Estimated: ~50ms latency, 98% recall, 1B vectors
```

#### Approach 3: Hierarchical retrieval

```
Level 1: Cluster all vectors (e.g., 10,000 clusters)
  - Store centroids only (10,000 vectors)
  - Fast search on centroids

Level 2: For each top cluster centroid, search within that cluster
  - Each cluster has ~100K vectors
  - HNSW search within cluster

Estimated: ~30ms latency, 90% recall, 1B vectors
```

### Trade-offs

| Approach | Speed | Accuracy | Complexity |
|----------|-------|----------|------------|
| Distributed DB | Fast | High | Medium |
| Two-stage | Fast | High | High |
| Hierarchical | Fastest | Medium | High |

### Key considerations

1. **Data distribution**: Are vectors evenly distributed or skewed?
2. **Update frequency**: How often do vectors change? (Affects index rebuild strategy)
3. **Query patterns**: Are queries evenly distributed or hot-spotted?
4. **Hardware**: GPU acceleration can speed up certain operations
5. **Caching**: Frequently accessed results can be cached
6. **Quantization**: Compressing vectors (PQ) trades memory for speed

## ANN in this project (Qdrant)

This project uses Qdrant's built-in HNSW index:

```python
# app/services/vector_db.py:47-62
results = self.client.search(
    collection_name=self.collection_name,
    query_vector=vector,
    with_payload=True,
    with_vectors=False,
    limit=top_k,  # default: 5
)
```

**Default behavior:**
- HNSW index with default parameters (M=16, ef=16)
- `limit=top_k` (default 5) — returns 5 nearest neighbors
- No `score_threshold` filtering (all results returned, even low-scoring ones)

**What's missing from this POC:**
- No `ef` parameter tuning (affects recall/latency trade-off)
- No `score_threshold` (can't filter out low-quality matches)
- No fallback to exact search for high-recall requirements

**Example scores from this project's search:**

```json
{
  "query": "How do similarity search engines work",
  "hits": [
    {"id": "doc-1", "score": 0.584, "text": "Vector databases store embeddings..."},
    {"id": "doc-3", "score": 0.5172, "text": "Semantic search finds results..."},
    {"id": "doc-2", "score": 0.1239, "text": "FastAPI is a modern web framework..."}
  ]
}
```

The cosine similarity scores (0 to 1) indicate:
- 0.58 — moderately similar (relevant but not exact match)
- 0.52 — somewhat similar
- 0.12 — barely related (likely not useful)

A `score_threshold=0.3` would filter out the last result, showing only the two relevant documents.