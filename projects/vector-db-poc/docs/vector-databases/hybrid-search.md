# Hybrid Search

## What is hybrid search?

**Hybrid search** combines multiple search methods to produce better results than any single method alone. In the vector search context, it typically means combining:

1. **Dense vector search** (semantic/embedding search) — finds results by meaning
2. **Sparse vector search** (keyword/BM25 search) — finds results by exact terms

## Why hybrid search?

### Limitations of pure vector search

| Problem | Example |
|---------|---------|
| **Hallucination of relevance** | Query "Java" → matches "coffee" articles (both are "Java," semantically related) |
| **Missing exact terms** | Query "iPhone 15 Pro Max" → misses documents that literally mention this model but use slightly different embedding context |
| **Rare entities** | Named entities (people, companies, products) may not have strong vector representations |
| **Boolean constraints** | Can't express "must contain X but not Y" with pure similarity search |

### Limitations of pure keyword search

| Problem | Example |
|---------|---------|
| **Synonyms missed** | Query "password reset" → misses "password recovery" |
| **Word order** | Query "dog bites man" vs "man bites dog" — same score |
| **Context** | "Apple" the company vs "apple" the fruit — can't distinguish |
| **No ranking by relevance meaning** | All keyword matches get roughly equal weight |

### Hybrid search advantages

Hybrid search mitigates both sets of limitations:

```
Query: "iPhone 15 Pro Max cases"

┌─────────────────┐    ┌──────────────────┐
│   Vector Search   │    │  Keyword Search   │
│                   │    │                   │
│ "iPhone case"     │    │ "iPhone" ✓        │
│ "phone case"      │    │ "15" ✓            │
│ "mobile cover"    │    │ "Pro" ✓           │
│ "cell phone guard"│    │ "Max" ✓           │
│ (missing: exact   │    │ (missing:         │
│  model match)     │    │  semantic match)  │
└────────┬──────────┘    └────────┬──────────┘
         │                        │
         └───────────┬────────────┘
                     │
            ┌────────▼────────┐
            │  Hybrid Fusion   │
            │                 │
            │ RRF or weighted │
            │  combination    │
            └────────┬────────┘
                     │
          ┌──────────▼──────────┐
          │ Final Results       │
          │ 1. "iPhone 15 Pro   │
          │    Max case"        │
          │ 2. "iPhone 15 Pro   │
          │    case"            │
          │ 3. "phone cases for │
          │    iPhone"          │
          └─────────────────────┘
```

## How hybrid search works

### Dense vector search

Dense vector search embeds the query text and finds similar vectors:

```
Query: "How to reset my password?"
→ Embedding: [0.012, -0.045, ...]
→ Search Qdrant for nearest vectors
→ Results: documents about password management (even if they use different words)
```

### Sparse vector search

Sparse vector search uses keyword matching (BM25 or TF-IDF):

```
Query: "How to reset my password?"
→ Keywords: "how", "reset", "password"
→ Match documents containing these terms
→ Results: documents that literally contain "reset" and "password"
```

### Combining results

The results from both searches need to be **merged and re-ranked**. Several strategies exist:

### 1. Reciprocal Rank Fusion (RRF)

**RRF** is the most common and robust hybrid fusion method:

```
For each result, compute:
score = Σ 1 / (k + rank_in_search_method)

Where:
- k is a constant (typically 60)
- rank is the position in the search results (1-indexed)
- The sum adds scores from both search methods

Example:
Result A: rank 1 in vector, rank 5 in keyword
  score = 1/(60+1) + 1/(60+5) = 0.0164 + 0.0152 = 0.0316

Result B: rank 2 in vector, rank 1 in keyword
  score = 1/(60+2) + 1/(60+1) = 0.0161 + 0.0164 = 0.0325

Result B wins (higher RRF score)
```

**Advantages of RRF:**
- No need to normalize scores between methods
- Works with different result counts per method
- Robust to outliers
- No hyperparameters to tune (k=60 is standard)

### 2. Weighted sum

Combine normalized scores with weights:

```
combined_score = w_vector × normalized_vector_score + w_keyword × normalized_keyword_score

Example:
  w_vector = 0.7, w_keyword = 0.3
  Result A: vector_score=0.85, keyword_score=0.6
    combined = 0.7×0.85 + 0.3×0.6 = 0.595 + 0.18 = 0.775
```

**Caveat:** Score normalization is tricky — vector scores (cosine 0–1) and keyword scores (BM25, often 0–10+) have very different ranges.

### 3. Cross-encoder re-ranking

After hybrid search returns top candidates, use a cross-encoder model to re-rank:

```
Initial results: [Doc A (0.85), Doc B (0.82), Doc C (0.79)]
Cross-encoder: compares query WITH each document
  → Doc A: 0.92 (strong match)
  → Doc B: 0.67 (weak match despite high vector score)
  → Doc C: 0.88 (better than B)
Final order: [Doc A, Doc C, Doc B]
```

This is more accurate but slower — typically used as a second stage with a small candidate set.

## Hybrid search in Qdrant

Qdrant supports hybrid search natively:

```python
# Qdrant supports both dense and sparse vectors in the same collection
results = client.search(
    collection_name="my_collection",
    query_text="iPhone cases",  # BM25 keyword search
    query_vector=[...],          # Dense vector search
    # Results are automatically fused using RRF
)
```

Or using the more explicit approach:

```python
from qdrant_client.http import models as qmodels

# Search with both dense vector and sparse vector (keyword)
results = client.search(
    collection_name="my_collection",
    query_vector=dense_vector,
    query_text="iPhone cases",
    with_payload=True,
    limit=10,
)
```

## Status in this project

**This POC does NOT implement hybrid search.** The current search endpoint (`app/api/routes.py:107-129`) uses only dense vector search:

```python
@router.post("/search", response_model=SearchResponse)
def search(
    query: str,
    top_k: int = 5,
    emb: EmbeddingService = Depends(get_embedding_service),
    vdb: VectorDBService = Depends(get_vector_db_service),
):
    if not vdb.client.collection_exists(settings.collection_name):
        raise HTTPException(404, "Collection does not exist.")
    query_vector = emb.embed(query)  # Only dense vector
    results = vdb.search(query_vector, top_k=top_k)
    # ... format results
```

**Why it's not implemented:**
- The current POC focuses on pure semantic search (dense vectors only)
- Adding keyword search requires a separate index (inverted index)
- Hybrid search is more complex and better demonstrated with a dedicated example

**How to add it (if desired):**
1. Store a sparse vector representation alongside the dense vector
2. Index the text field for BM25 search
3. Combine results using RRF or weighted sum
4. Re-rank the combined results

**Trade-offs of adding hybrid search to this POC:**
- **Pros**: More realistic, better search quality, demonstrates advanced concepts
- **Cons**: Significant complexity increase, moves beyond "simple learning POC"

## When to use hybrid search

| Scenario | Pure vector | Hybrid |
|----------|-------------|--------|
| Semantic-only queries | ✅ | Not needed |
| Queries with specific terms | ❌ (might miss exact matches) | ✅ |
| E-commerce search | ❌ (needs exact model names) | ✅ |
| Documentation search | ❌ (needs exact API names) | ✅ |
| Content discovery (recommendations) | ✅ | Not needed |
| Legal/medical search | ❌ (needs exact terms) | ✅ |

## BM25 in context

**BM25** (Best Match 25th variant) is the standard ranking function used in Elasticsearch, Lucene, and most search engines. It computes a relevance score based on:

1. **Term frequency (TF)**: How often the query term appears in the document
2. **Inverse document frequency (IDF)**: How rare the term is across all documents
3. **Document length**: Shorter documents matching a query term are ranked higher

```
BM25(query, doc) = Σ IDF(qᵢ) × TF(qᵢ, doc) × (k₁ + 1) / (TF(qᵢ, doc) + k₁ × (1 - b + b × |doc| / avgdl))

Where k₁ ≈ 1.2, b ≈ 0.75 are standard parameters
```

Compared to embedding-based search, BM25 is:
- **Fast**: Uses an inverted index, no neural model needed
- **Precise**: Exact term matching
- **Limited**: Misses synonyms and semantic relationships

Qdrant supports BM25 as part of its hybrid search capability, but this POC doesn't configure it.