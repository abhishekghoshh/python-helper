# Similarity and Distance Metrics

When we have vectors in a high-dimensional space, we need a way to measure how **similar** or **different** they are. This is done using **similarity metrics** (higher = more similar) or **distance metrics** (lower = more similar). The choice of metric affects search results and is configured at collection creation time.

---

## Overview

In this project, the vector database (Qdrant) is configured with **cosine similarity**:

```python
# app/services/vector_db.py:22-30
qmodels.VectorParams(
    size=self.embedding_dim,        # 384
    distance=qmodels.Distance.COSINE,  # cosine similarity
)
```

This means all searches in the `demo` collection use cosine similarity to rank results.

---

## 1. Cosine Similarity

### What it is

**Cosine similarity** measures the **angle** between two vectors, ignoring their magnitude. It answers: "Do these vectors point in the same direction?"

### Formula

```
cos(u, v) = (u · v) / (||u|| × ||v||)
```

Where:
- `u · v` is the dot product
- `||u||` and `||v||` are the magnitudes (L2 norms) of each vector

### Range

| Value | Meaning |
|-------|---------|
| `1.0` | Vectors point in the exact same direction (identical) |
| `0.7` | Vectors are somewhat similar |
| `0.0` | Vectors are orthogonal (unrelated) |
| `-0.5` | Vectors point in opposite directions |
| `-1.0` | Vectors are diametrically opposed |

For embeddings (which are typically non-negative after normalization), the practical range is `0.0` to `1.0`.

### Intuition

```
Vector A: [0.8, 0.1, 0.2]  (points mostly in the x-direction)
Vector B: [0.7, 0.2, 0.1]  (also points mostly in the x-direction)
Vector C: [0.1, 0.9, 0.0]  (points mostly in the y-direction)

cos(A, B) ≈ 0.94  (very similar — same direction)
cos(A, C) ≈ 0.15  (different — orthogonal-ish)
```

### Why it's popular for embeddings

1. **Magnitude independence**: Two sentences of different lengths may produce vectors with different magnitudes, but cosine similarity compares only direction.
2. **Semantic focus**: What matters for semantic similarity is the **pattern** of activation across dimensions, not the overall scale.
3. **Normalized equivalence**: When vectors are normalized to unit length (||v|| = 1), cosine similarity equals the dot product.

### In this project

The embedding model (`all-MiniLM-L6-v2`) produces vectors that are already L2-normalized (unit vectors). This means:

```
cos(u, v) = (u · v) / (1 × 1) = u · v
```

Qdrant computes cosine similarity internally when `distance=COSINE`. The `search` method returns scores in range [0, 1] for normalized embeddings:

```python
# app/api/routes.py:120-127
hits = [
    SearchHit(
        id=r["payload"].get("doc_id", r["id"]),
        text=r["payload"].get("text", ""),
        score=round(r["score"], 4),
        ...
    )
    for r in results
]
```

## 2. Euclidean Distance (L2)

### What it is

**Euclidean distance** is the straight-line distance between two points in space — the distance you'd measure with a ruler.

### Formula

```
L2(u, v) = √(Σ(uᵢ - vᵢ)²) = √((u₁-v₁)² + (u₂-v₂)² + ... + (uₙ-vₙ)²)
```

### Range

| Value | Meaning |
|-------|---------|
| `0.0` | Vectors are identical (same point in space) |
| `0.5` | Vectors are somewhat close |
| `1.41` | Vectors are orthogonal (√2 for unit vectors) |
| `2.0` | Vectors point in exactly opposite directions (for unit vectors) |

### Intuition

```
Vector A: [0.8, 0.1, 0.2]
Vector B: [0.7, 0.2, 0.1]
L2(A, B) = √((0.1)² + (0.1)² + (0.1)²) = √0.03 ≈ 0.17  (very close)

Vector C: [0.1, 0.9, 0.0]
L2(A, C) = √((0.7)² + (0.8)² + (0.2)²) = √1.17 ≈ 1.08  (far apart)
```

### When to use it

- When both **direction** and **magnitude** matter
- For spatial data (e.g., 2D/3D coordinates)
- When vectors are **not** normalized

### Relationship to cosine

For **unit vectors** (||u|| = ||v|| = 1):

```
L2²(u, v) = ||u||² + ||v||² - 2(u · v) = 2 - 2·cos(u, v)
```

So Euclidean distance and cosine similarity encode the same information for normalized vectors — but in different scales.

## 3. Dot Product

### What it is

The **dot product** is the sum of element-wise products of two vectors.

### Formula

```
dot(u, v) = Σ(uᵢ × vᵢ) = u₁v₁ + u₂v₂ + ... + uₙvₙ
```

### Range

| Constraint | Range |
|-----------|-------|
| Unit vectors | `[0, 1]` (0 = orthogonal, 1 = identical) |
| Non-normalized | `(-∞, ∞)` (unbounded) |

### Intuition

```
Vector A: [0.8, 0.1, 0.2]
Vector B: [0.7, 0.2, 0.1]
dot(A, B) = 0.56 + 0.02 + 0.02 = 0.60

Vector C: [0.1, 0.9, 0.0]
dot(A, C) = 0.08 + 0.09 + 0.00 = 0.17
```

### Why OpenAI uses it

OpenAI's `text-embedding-ada-002` and `text-embedding-3-small/large` models produce embeddings that are **not** L2-normalized, but they are designed so that **dot product** works as a similarity measure. This is why Pinecone and other services default to DOT product for OpenAI embeddings.

### Relationship to cosine

For **non-normalized** vectors:
```
cos(u, v) = dot(u, v) / (||u|| × ||v||)
```

For **normalized** vectors (||u|| = ||v|| = 1):
```
cos(u, v) = dot(u, v)
```

So **dot product = cosine similarity for normalized vectors**. This project's model produces normalized embeddings, but the collection uses COSINE (which Qdrant handles internally).

## 4. Manhattan Distance (L1)

### What it is

The **Manhattan distance** (L1) is the sum of absolute differences — like walking along city blocks.

### Formula

```
L1(u, v) = Σ|uᵢ - vᵢ| = |u₁-v₁| + |u₂-v₂| + ... + |uₙ-vₙ|
```

### Range

| Value | Meaning |
|-------|---------|
| `0.0` | Vectors are identical |
| Higher | More different |

### When to use it

- When you want **robustness to outliers** (single large differences don't dominate as much)
- For sparse vectors (e.g., TF-IDF)

### Less common for embeddings

Most embedding-based search uses cosine or dot product because direction matters more than absolute differences.

## Metric comparison

| Metric | Measures | Higher = ? | Range (unit vectors) | Sensitive to magnitude? | Best for |
|--------|----------|------------|---------------------|------------------------|----------|
| Cosine | Angle | More similar | [0, 1] | No | Text embeddings |
| Euclidean | Straight-line distance | More similar | [0, 2] | Yes | Spatial data |
| Dot product | Alignment | More similar | [0, 1] (unit) | Yes | OpenAI embeddings |
| Manhattan | Grid distance | More similar | [0, 2] (unit) | Yes | Sparse vectors |

## Normalization and its impact

### Why normalize?

Normalization scales vectors to unit length (||v|| = 1). This makes **cosine similarity equivalent to dot product**, and prevents magnitude from affecting comparison.

### With this project's model

The `all-MiniLM-L6-v2` model applies L2 normalization internally. This means:

1. All embedding vectors have magnitude 1
2. Cosine similarity and dot product give the same results
3. Euclidean distance ∈ [0, 2] where 0 = identical, 2 = opposite

### What if embeddings are NOT normalized?

If you use a model that doesn't normalize (e.g., some OpenAI models), the choice of metric matters more:

- **Cosine**: ignores magnitude → "A short document and a long document with the same meaning will match"
- **Dot product**: includes magnitude → "A long document with high-confidence features will score higher"
- **Euclidean**: includes magnitude → "Two documents with similar content but very different lengths will be far apart"

## Choosing a metric for your use case

| Scenario | Recommended metric | Reason |
|----------|-------------------|--------|
| Text search with SentenceTransformer | **Cosine** | Magnitude-independent, semantic focus |
| OpenAI embeddings | **Dot product** | OpenAI models are optimized for dot product |
| Multilingual search | **Cosine** | Works across languages regardless of confidence |
| Image search (CLIP) | **Cosine** | Embeddings are typically normalized |
| Spatial/geolocation data | **Euclidean** | Actual distance matters |
| Sparse vectors (TF-IDF) | **Dot product** or **Manhattan** | Efficient for sparse representations |

## How Qdrant handles metrics

In this project, the metric is set at collection creation time and cannot be changed afterward:

```python
# app/services/vector_db.py:22-30
self.client.recreate_collection(
    collection_name=self.collection_name,
    vectors_config=qmodels.VectorParams(
        size=self.embedding_dim,
        distance=qmodels.Distance.COSINE,
    ),
)
```

Qdrant supports three metrics:
- `qmodels.Distance.COSINE` — cosine similarity
- `qmodels.Distance.EUCLID` — Euclidean distance
- `qmodels.Distance.DOT` — dot product

The search endpoint (`app/api/routes.py:107-129`) uses the metric configured at collection creation:

```python
results = self.client.search(
    collection_name=self.collection_name,
    query_vector=vector,
    with_payload=True,
    with_vectors=False,
    limit=top_k,
)
```

No metric selection is needed at query time — Qdrant uses the collection's configured metric for all searches.