# Interview Q&A: Similarity Search

## Cosine Similarity

### Q1: What is cosine similarity?

**A:** Cosine similarity measures the **angle** between two vectors, ignoring their magnitude. It answers: "Do these vectors point in the same direction?"

```
cos(u, v) = (u · v) / (||u|| × ||v||)
```

- **Range**: [-1, 1], where 1 = identical direction, 0 = orthogonal, -1 = opposite
- For embeddings (typically non-negative), practical range is [0, 1]
- For **unit vectors** (normalized), cosine similarity = dot product

**Why popular for embeddings:**
- Direction encodes meaning, magnitude doesn't
- Insensitive to document length differences
- Works well for text embeddings regardless of whether they're normalized

### Q2: Why normalize vectors before computing similarity?

**A:** Normalization scales vectors to unit length (magnitude = 1). Benefits:

1. **Consistent scoring**: Non-normalized vectors may have very different magnitudes, making cosine similarity less interpretable
2. **Cosine = dot product**: For unit vectors, `cos(u, v) = u · v`, simplifying computation
3. **Numerical stability**: Prevents overflow/underflow with very large or small values

The `all-MiniLM-L6-v2` model in this project applies L2 normalization internally, so embeddings are already unit vectors.

### Q3: When would you use cosine similarity vs. dot product?

**A:**

- **Cosine similarity**: When vectors may not be normalized, or when you want to ignore magnitude. Standard for text embeddings.
- **Dot product**: When vectors are normalized (equivalent to cosine). Also used by OpenAI embeddings, which are designed for dot product similarity.
- For **unit vectors**: cosine similarity and dot product are mathematically equivalent.
- For **non-normalized vectors**: cosine normalizes for magnitude; dot product includes it.

### Q4: Can cosine similarity be negative?

**A:** Yes. Cosine similarity ranges from -1 to 1.

- **1**: Vectors point in the same direction (identical)
- **0**: Vectors are orthogonal (unrelated)
- **-1**: Vectors point in opposite directions (contradictory)

However, most text embedding models produce vectors with non-negative values, so cosine similarity is typically in [0, 1]. Negative values would indicate the models "disagree" on the meaning.

## Euclidean Distance

### Q5: What is Euclidean distance?

**A:** Euclidean distance (L2) is the straight-line distance between two points in space:

```
L2(u, v) = √(Σ(uᵢ - vᵢ)²)
```

- **Range**: [0, ∞), where 0 = identical
- **Sensitive to magnitude**: A longer vector and a shorter vector pointing the same direction will have a large distance
- **Use when magnitude matters**: Spatial data, image embeddings where vector norm carries information

### Q6: Cosine similarity vs. Euclidean distance — which should I use?

**A:**

| Scenario | Cosine | Euclidean |
|----------|--------|-----------|
| Text embeddings | ✅ Usually | ❌ Unless vectors are normalized |
| Image embeddings (CLIP) | ✅ Usually | ❌ Unless normalized |
| Spatial/geolocation | ❌ | ✅ (actual distance matters) |
| OpenAI embeddings | ❌ | ❌ (use dot product) |

For normalized vectors, cosine and Euclidean give equivalent ranking (just different scales):

```
L2²(u, v) = 2 - 2·cos(u, v)  (for unit vectors)
```

So if vectors are unit length, choosing between them is a matter of score interpretation.

## Dot Product

### Q7: What is the dot product and when is it used?

**A:** Dot product is the sum of element-wise products:

```
dot(u, v) = Σ(uᵢ × vᵢ)
```

- **Range**: (-∞, ∞) for non-normalized; [0, 1] for unit vectors
- **OpenAI embeddings**: `text-embedding-ada-002` and newer models are designed for dot product similarity
- **For normalized vectors**: dot product = cosine similarity

### Q8: Why does OpenAI recommend dot product?

**A:** OpenAI's embedding models are trained with a **contrastive loss** that optimizes for dot product similarity. Their embeddings are intentionally **not** L2-normalized, so:

- **Dot product** includes magnitude information (confidence)
- **Cosine similarity** would discard magnitude

Using dot product preserves the model's intended similarity metric. Using cosine similarity on OpenAI embeddings would give suboptimal results.

In contrast, `SentenceTransformer` models (used in this project) apply L2 normalization and are designed for cosine similarity.

## Nearest-Neighbor Search

### Q9: What is nearest-neighbor search?

**A:** Given a query vector and a collection of stored vectors, find the K vectors that are most similar to the query (by some distance/similarity metric).

```
Query: "How to reset password?"
→ vector_q
→ Find 5 most similar vectors in the database
→ Return those documents
```

### Q10: What is k-NN (k-Nearest Neighbors)?

**A:** k-NN is a search that returns the top-k most similar vectors to a query. The "k" is the number of results to return.

In this project:

```python
# app/api/routes.py:109
top_k: int = 5  # default

# app/services/vector_db.py:47-54
results = self.client.search(
    collection_name=self.collection_name,
    query_vector=vector,
    limit=top_k,
)
```

### Q11: What is Top-K search?

**A:** Top-K search is the same as k-NN — return the K nearest (most similar) neighbors. The "K" is typically small (1–20) because:

1. Users can't effectively review hundreds of results
2. Computational cost increases with K
3. Relevance typically drops sharply after the top few results

In this project, `top_k` defaults to 5 and can be adjusted via query parameter.

## Approximate Search

### Q12: What is approximate nearest-neighbor (ANN) search?

**A:** Exact NN search compares the query against every vector (O(N)). **Approximate NN** uses indexing structures to find results that are very likely the nearest, but not guaranteed — trading a tiny bit of accuracy for massive speed gains.

```
1,000,000 vectors:
  Exact: scan all 1,000,000 → ~1 second
  ANN:   examine 100 candidates → ~50 ms
```

### Q13: What is recall@k?

**A:** Recall@k measures the fraction of true top-k neighbors that the ANN search actually returns:

```
recall@k = |true_top_k ∩ returned_top_k| / k
```

Example: k=5, true nearest are [A,B,C,D,E], ANN returns [A,C,D,F,G] → recall = 3/5 = 60%

- **recall@100%**: Exact search
- **recall@95%**: Excellent for most applications
- **recall@80%**: Acceptable for some use cases

### Q14: Why is approximate search preferred over exact search?

**A:** At scale, exact search is prohibitively expensive:

| Vectors | Exact time | ANN time | Speedup |
|---------|-----------|----------|---------|
| 1,000 | 1 ms | 1 ms | 1x |
| 100K | 100 ms | 5 ms | 20x |
| 10M | 10 sec | 50 ms | 200x |
| 1B | 17 min | 800 ms | 1,275x |

For interactive applications (sub-100ms response), ANN is the only viable option.

## Score Thresholds

### Q15: What is a score threshold and why use it?

**A:** A **score threshold** filters out search results below a minimum similarity score. This prevents returning irrelevant results that have low similarity to the query.

```python
# Hypothetical: only return results with similarity > 0.3
results = client.search(query_vector, limit=10, score_threshold=0.3)
```

**Why use it:**
- Reduces noise in results
- Gives users confidence that returned results are relevant
- Allows returning fewer results but with higher quality

**Trade-off:** May return fewer than `top_k` results if not enough meet the threshold.

In this project, no score threshold is implemented — all top-k results are returned regardless of score.

### Q16: What do cosine similarity scores mean in practice?

**A:** For the `all-MiniLM-L6-v2` model (normalized embeddings, cosine metric):

| Score | Interpretation |
|-------|----------------|
| 0.90–1.00 | Nearly identical meaning |
| 0.70–0.90 | Strongly related |
| 0.50–0.70 | Moderately related |
| 0.30–0.50 | Somewhat related |
| 0.00–0.30 | Barely related |

Example from this project's search results:

```json
{
  "hits": [
    {"id": "doc-1", "score": 0.584, "text": "Vector databases store embeddings..."},
    {"id": "doc-3", "score": 0.5172, "text": "Semantic search finds results..."},
    {"id": "doc-2", "score": 0.1239, "text": "FastAPI is a modern web framework..."}
  ]
}
```

A score threshold of 0.3 would filter out `doc-2` (score 0.12), which is barely related to the query.

### Q17: How do you choose a similarity metric?

**A:**

| Factor | Recommendation |
|--------|----------------|
| SentenceTransformer embeddings | Cosine (model normalizes internally) |
| OpenAI embeddings | Dot product (model designed for it) |
| Image embeddings (CLIP) | Cosine (typically normalized) |
| Spatial/geolocation data | Euclidean (actual distance matters) |
| Sparse vectors (TF-IDF) | Dot product or BM25 |

Key consideration: **the metric must match the model's training objective**. If the model was trained with contrastive loss using cosine similarity, use cosine. If it used dot product, use dot product.

In this project, the metric is set at collection creation:

```python
# app/services/vector_db.py:28
distance=qmodels.Distance.COSINE,
```

This can be `COSINE`, `EUCLID`, or `DOT` depending on the embedding model used.