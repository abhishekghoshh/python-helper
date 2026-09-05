# Vector Indexing

## Why indexing is necessary

Searching for the nearest neighbors of a query vector in a dataset of *n* vectors requires comparing the query against every vector — a **brute-force** or **flat** search. This is O(n) per query.

For small datasets (thousands of vectors), this is fine. But for larger datasets:

| Vectors | Brute-force time (1ms per comparison) |
|---------|--------------------------------------|
| 1,000 | ~1 ms |
| 10,000 | ~10 ms |
| 100,000 | ~100 ms |
| 1,000,000 | ~1 second |
| 10,000,000 | ~10 seconds |
| 1,000,000,000 | ~2.7 minutes |

At scale, brute-force search is too slow for interactive applications. **Indexing** solves this by organizing vectors so that only a subset needs to be examined during search.

## Exact vs. approximate nearest neighbor

### Exact nearest neighbor (ANN = Approximate Nearest Neighbor)

- **Exact**: Guaranteed to find the true k nearest neighbors
- **Method**: Linear scan (flat index) — compare against all vectors
- **Pros**: Perfect accuracy
- **Cons**: O(n) time, impractically slow at scale

### Approximate nearest neighbor (ANN)

- **Approximate**: Finds neighbors that are *very likely* the nearest, but not guaranteed
- **Method**: Indexing structures that skip over most vectors
- **Pros**: Sub-linear time (O(log n) or better), fast at scale
- **Cons**: May miss some true neighbors (lower recall)

The key question: **how accurate is the approximation?** This is measured by **recall**.

## Recall

**Recall** measures the fraction of true nearest neighbors that the ANN search actually finds:

```
recall = (true neighbors found by ANN) / (total true neighbors)

Example: Query has 3 truly nearest neighbors. ANN returns 2 of them.
recall = 2/3 = 67%
```

| Recall | Meaning |
|--------|---------|
| 100% | Perfect (exact) |
| 95% | Excellent (almost perfect) |
| 80% | Good (acceptable for most apps) |
| 50% | Poor (too many misses) |

Most production systems target 90–99% recall, which provides excellent speed with minimal accuracy loss.

## Index types

### 1. Flat (exact) index

- No indexing structure — brute-force comparison
- **Recall**: 100% (exact)
- **Speed**: Slowest
- **Memory**: Stores raw vectors
- **Use case**: Small datasets, or as a baseline for comparison

In Qdrant, this is the default when no HNSW index is configured. You can force flat search by setting `index.hnsw` to `null` in the collection config.

### 2. HNSW (Hierarchical Navigable Small World)

![HNSW](https://qdrant.tech/)

**HNSW** builds a multi-layer graph to navigate toward nearest neighbors:

1. **Top layer**: A sparse graph with few nodes — provides a "coarse" view
2. **Lower layers**: Progressively denser graphs with more nodes — provides "fine" detail
3. **Search**: Start at the top layer, navigate toward the query, then descend to lower layers

### HNSW parameters

| Parameter | Description | Trade-off |
|-----------|-------------|-----------|
| `M` | Max edges per node (graph connectivity) | Higher M = better recall, more memory |
| `efConstruction` | Size of the candidate list during index building | Higher = better index quality, slower build |
| `ef` | Size of the candidate list during search | Higher = better recall, slower search |

### HNSW in Qdrant

Qdrant uses HNSW by default. The configuration is set at collection creation:

```python
# app/services/vector_db.py:24-30
qmodels.VectorParams(
    size=self.embedding_dim,  # 384
    distance=qmodels.Distance.COSINE,
)
```

Qdrant automatically builds an HNSW index on top of the vectors. The default HNSW parameters are:
- `M = 16` — 16 links per node
- `efConstruction = 100` — candidate list size for building
- `ef = 16` (or `top_k * 2`) — candidate list size for searching

### HNSW trade-offs

| Metric | HNSW |
|--------|------|
| Recall | Very high (95%+ with default params) |
| Speed | Fast (sub-linear) |
| Memory | Moderate (graph overhead ~20-30% of vector storage) |
| Index build | Slower than flat (but incremental) |
| Insert/delete | Supported (graph is updated) |

### 3. IVF (Inverted File)

**IVF** clusters vectors into groups (cells). During search, only the nearest clusters are searched:

1. **Training**: Cluster the vectors into k clusters (using k-means)
2. **Search**: Find the nearest cluster(s), then search within those clusters only

```
Vectors: [v1, v2, v3, v4, v5, v6, v7, v8, v9, v10]
Clusters: {v1,v3,v7} {v2,v4,v5} {v6,v8,v9} {v10}

Query → nearest cluster = {v2,v4,v5} → search only these
```

### IVF parameters

| Parameter | Description | Trade-off |
|-----------|-------------|-----------|
| `nlist` | Number of clusters (partitions) | More clusters = smaller cells = faster search but lower recall |
| `nprobe` | Number of clusters to search | Higher nprobe = better recall, slower search |

### IVF trade-offs

| Metric | IVF |
|--------|-----|
| Recall | Moderate (depends on nlist/nprobe) |
| Speed | Very fast (searches subset of vectors) |
| Memory | Low overhead (only stores centroids + vectors) |
| Index build | Slower (k-means clustering) |
| Insert/delete | Requires re-clustering (expensive) |

### 4. Product Quantization (PQ)

**PQ** compresses vectors by splitting them into sub-vectors and quantizing each:

1. Split a 384-dim vector into 32 sub-vectors of 12 dims each
2. For each sub-vector, store only which of 256 centroid it's closest to (8 bits = 1 byte)
3. The compressed vector is 32 bytes instead of 384 × 4 = 1,536 bytes

### PQ trade-offs

| Metric | PQ |
|--------|----|
| Recall | Lower (lossy compression) |
| Speed | Fast (smaller vectors, less memory bandwidth) |
| Memory | Very low (10-50x compression) |
| Index build | Moderate (k-means per sub-space) |
| Insert/delete | Requires decompression for comparison |

### 5. OPQ (Optimized Product Quantization)

**OPQ** improves PQ by applying a rotation to the vector space before quantization, aligning the rotation with high-variance dimensions:

```
Original vector → Rotation matrix → Rotated vector → PQ compression
```

This can improve recall by 5-15% over standard PQ.

## The indexing trade-off

```
Accuracy ←→ Search Speed ←→ Memory Usage ←→ Index Build Time
```

| Strategy | Accuracy | Speed | Memory | Build Time |
|----------|----------|-------|--------|------------|
| Flat (exact) | 100% | Slow | Low | Immediate |
| HNSW | 95–99% | Fast | Medium | Slow |
| IVF | 80–95% | Fast | Low | Slow |
| PQ | 70–90% | Fast | Very Low | Moderate |
| OPQ | 80–95% | Fast | Very Low | Moderate |

## Combining indexes

Many vector databases (including Qdrant) support **combining** indexing strategies:

- **IVF + HNSW + PQ**: IVF narrows down the candidate set, HNSW finds nearest within each cell, PQ compresses for memory efficiency
- **HNSW + PQ**: HNSW graph with compressed vectors for lower memory

## Choosing an index

| Dataset size | Recommended | Reason |
|-------------|------------|--------|
| < 10K vectors | Flat | Brute-force is fast enough, no indexing overhead |
| 10K–1M vectors | HNSW | Best balance of speed, recall, and ease of use |
| 1M–100M vectors | IVF or HNSW | IVF for read-heavy, HNSW for mixed read/write |
| > 100M vectors | IVF + PQ or clustered HNSW | Memory efficiency critical at this scale |

## HNSW in this project

This project uses Qdrant's default HNSW index with no custom configuration. The relevant code:

```python
# app/services/vector_db.py:22-30
def create_collection(self) -> None:
    if not self.client.collection_exists(self.collection_name):
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=qmodels.VectorParams(
                size=self.embedding_dim,        # 384
                distance=qmodels.Distance.COSINE,
            ),
        )
```

No HNSW-specific parameters are set — Qdrant uses its defaults:
- M=16 (graph connectivity)
- efConstruction=100 (build quality)
- ef=16 (search quality)

For a POC with small datasets (hundreds to thousands of documents), the default HNSW configuration provides excellent performance with near-100% recall. No tuning is needed.

For production with millions of vectors, you would tune these parameters based on your recall and latency targets.