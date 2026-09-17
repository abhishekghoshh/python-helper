# Vector Indexing

## Why Indexing Matters

When you store millions of vectors, comparing a query against every single
vector (brute force) becomes prohibitively slow:

```mermaid
flowchart LR
    VEC["1M vectors × 384 dimensions<br/>= 384M comparisons per query"] --> BF["Brute Force<br/>Compares query against every vector<br/>~100ms on a fast machine"]
    VEC --> IDX["Proper Indexing (HNSW)<br/>Navigates graph structure,<br/>skips irrelevant vectors<br/>→ Milliseconds per query"]

    style VEC fill:#3498db,color:#fff
    style BF fill:#e74c3c,color:#fff
    style IDX fill:#27ae60,color:#fff
```

**Vector indexing** accelerates similarity search by organizing vectors so
the search algorithm can skip irrelevant regions of the vector space.

## Index Types

### 1. HNSW (Hierarchical Navigable Small World)

**What it is**: A graph-based index that builds multiple layers of connections
between vectors.

```mermaid
graph TD
    subgraph "Top Layer (sparse)"
        A1[A] --> A2[B]
        A2 --> A3[C]
    end
    subgraph "Middle Layer"
        B1[A] --> B2[C]
        B2 --> B3[D]
    end
    subgraph "Bottom Layer (all vectors)"
        C1[A] --> C2[B]
        C2 --> C3[C]
        C3 --> C4[D]
    end

    style A1 fill:#3498db,color:#fff
    style B1 fill:#e74c3c,color:#fff
    style C1 fill:#27ae60,color:#fff
```

**How it works**:
1. Start at the top (sparsest) layer
2. Greedily move to the neighbor closest to the query
3. Descend to the next layer and repeat
4. Continue until reaching the bottom layer

**Pros**:
- Excellent recall (>95%)
- Fast search (O(log n))
- Dynamic (can add new vectors)

**Cons**:
- Higher memory usage (graph structure)
- Slower to build

### 2. IVF (Inverted File Index)

**What it is**: Clusters vectors into groups (Voronoi cells). At search time,
only search clusters near the query.

```mermaid
flowchart LR
    Q[Query] --> IVF[Coarse Quantizer]
    IVF --> C1[Cluster 1]
    IVF --> C2[Cluster 2]
    IVF --> C3[Cluster 3]
    C2 --> List["Inverted Lists (vectors)"]
    List --> Search[Search within cluster]
    Search --> Results[Results]

    style Q fill:#3498db,color:#fff
    style IVF fill:#e74c3c,color:#fff
    style Search fill:#27ae60,color:#fff
```

**How it works**:
1. **Training**: Cluster vectors into K clusters
2. **Indexing**: For each cluster, store a list of vector IDs
3. **Search**: Find the nearest clusters to the query, search only those

**Pros**:
- Lower memory than HNSW
- Good recall with proper parameter tuning
- Works well with scalar quantization

**Cons**:
- Requires training phase
- Less dynamic (additions require re-clustering)

### 3. Quantization Indexes

#### Product Quantization (PQ)

Compresses vectors by splitting them into sub-vectors and quantizing each:

```mermaid
flowchart LR
    VEC["384-dim vector<br/>(1536 bytes, float32)"] --> SPLIT["Split into 32 sub-vectors<br/>12 dims each"]
    SPLIT --> SUB1["Sub-vector 1<br/>12 dims → 8-bit code<br/>(mapped to nearest centroid)"]
    SPLIT --> SUB2["Sub-vector 2<br/>12 dims → 8-bit code"]
    SPLIT --> SUB3["Sub-vector 3<br/>12 dims → 8-bit code"]
    SPLIT --> SUBN["... 32 sub-vectors total"]
    SUB1 --> COMBINE["Reconstruct compressed vector<br/>32 bytes total<br/>(98% size reduction)"]
    SUB2 --> COMBINE
    SUB3 --> COMBINE
    SUBN --> COMBINE
    COMBINE --> SEARCH_PQ["Fast Search<br/>Compare compressed representations<br/>Approximate but very memory-efficient"]

    style VEC fill:#3498db,color:#fff
    style SPLIT fill:#9b59b6,color:#fff
    style SUB1 fill:#e74c3c,color:#fff
    style COMBINE fill:#f39c12,color:#fff
    style SEARCH_PQ fill:#27ae60,color:#fff
```

**Pros**: Dramatically reduces memory usage
**Cons**: Lower accuracy (lossy compression)

#### Scalar Quantization

Simpler: quantize each dimension independently to 8 bits or less.

```mermaid
flowchart LR
    FP32["Float32 values<br/>[0.234, -0.876, 0.451, ...]<br/>32 bits per dimension<br/>1536 bytes for 384 dims"] --> QUANT["Scalar Quantization<br/>Map each value to 8-bit integer<br/>(uniform or learned quantization)"]
    QUANT --> INT8["Int8 values<br/>[60, 200, 115, ...]<br/>8 bits per dimension<br/>384 bytes for 384 dims<br/>(75% size reduction)"]
    QUANT --> QUAL["Some precision loss<br/>but much smaller memory footprint<br/>Good for large-scale deployments"]
    INT8 --> SEARCH_SQ["Fast Search<br/>Integer arithmetic<br/>~4x faster than float32"]

    style FP32 fill:#3498db,color:#fff
    style QUANT fill:#9b59b6,color:#fff
    style INT8 fill:#e74c3c,color:#fff
    style QUAL fill:#f39c12,color:#fff
    style SEARCH_SQ fill:#27ae60,color:#fff
```

### 4. Tree-Based Indexes (Annoy)

**What it is**: Random projection trees that partition space.

```mermaid
flowchart TD
    R[Root: all vectors] --> L1[Left half]
    R --> L2[Right half]
    L1 --> L3[Quarter 1]
    L1 --> L4[Quarter 2]
    L2 --> L5[Quarter 3]
    L2 --> L43[Quarter 4]

    style R fill:#3498db,color:#fff
    style L3 fill:#e74c3c,color:#fff
```

**Pros**: Simple, memory-mapped (fast file-based loading)
**Cons**: Slower than HNSW for high-recall search

## Choosing an Index

| Index | Search Speed | Recall | Memory | Dynamic? | Best For |
|-------|-------------|--------|--------|----------|----------|
| **HNSW** | Very fast | 95-99% | High | Yes | General purpose |
| **IVF** | Fast | 90-98% | Medium | No | Memory-constrained |
| **PQ** | Fast | 80-90% | Very low | No | Massive scale |
| **Annoy** | Medium | 90-95% | Low | No | Static datasets |
| **Brute Force** | Slow | 100% | Low | Yes | Small datasets |

## Index Parameters

### HNSW Parameters

| Parameter | Description | Typical Value | Effect |
|-----------|-------------|---------------|--------|
| `M` | Max connections per node | 16, 32 | Higher M = better recall, more memory |
| `ef` | Search scope | 100-500 | Higher ef = better recall, slower search |
| `efConstruction` | Build scope | 100-500 | Higher = better graph, slower build |

### IVF Parameters

| Parameter | Description | Typical Value |
|-----------|-------------|---------------|
| `nlist` | Number of clusters | 100-1000 |

## In Our POC

Qdrant uses HNSW as the default index for cosine distance:

```python
# The collection is created with default HNSW indexing
client.recreate_collection(
    collection_name="my-collection",
    vectors_config=VectorParams(
        size=384,
        distance=Distance.COSINE,
    ),
)
```

You can configure HNSW parameters for precision/speed tradeoffs:

```python
# Custom HNSW configuration
vectors_config=VectorParams(
    size=384,
    distance=Distance.COSINE,
    hnsw_config=HnswConfig(
        m=32,              # More connections
        ef_construct=200,  # Better graph quality
    ),
)
```

## Build vs. Search Tradeoff

| Goal | Strategy |
|------|----------|
| **Fast searches** | Increase `ef` (search scope) |
| **Fast builds** | Decrease `efConstruction` |
| **Low memory** | Use quantization or IVF |
| **High recall** | Use HNSW with high `M` and `ef` |

## Next Steps

- [ANN Search](ann-search.md) — Deep dive into approximate nearest neighbors
