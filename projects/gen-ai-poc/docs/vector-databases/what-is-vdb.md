# What is a Vector Database?

## The Problem

Embedding models convert text into dense vectors (e.g., 384 numbers per text).
When you have thousands or millions of documents, you need to find which ones
are most similar to a query — fast.

```mermaid
flowchart LR
    subgraph "Ingestion"
        DOCS["Documents<br/>(raw text)"] --> EMB_DOC["Embedding Model<br/>sentence-transformers<br/>(384-dim vectors)"]
        EMB_DOC --> VECTORS["Stored Vectors<br/>in vector database"]
    end

    subgraph "Query"
        Q["Query<br/>(user text)"] --> EMB_Q["Query Embedding<br/>same model as above"]
        EMB_Q --> QVEC["Query Vector<br/>(384-dim)"]
    end

    QVEC --> SEARCH["Vector Search<br/>Compare query vector against<br/>all stored vectors"]
    VECTORS --> SEARCH
    SEARCH --> RESULTS["Top-K Similar Vectors<br/>ranked by similarity score"]
    RESULTS --> DOCS_OUT["Return matching documents<br/>+ metadata payloads"]

    style DOCS fill:#3498db,color:#fff
    style EMB_DOC fill:#9b59b6,color:#fff
    style VECTORS fill:#e74c3c,color:#fff
    style Q fill:#3498db,color:#fff
    style EMB_Q fill:#9b59b6,color:#fff
    style QVEC fill:#f39c12,color:#fff
    style SEARCH fill:#e74c3c,color:#fff
    style RESULTS fill:#27ae60,color:#fff
    style DOCS_OUT fill:#27ae60,color:#fff
```

### Why Not Just Use a Regular Database?

| Feature | Traditional DB | Vector DB |
|---------|---------------|-----------|
| **Search by** | Keywords, IDs | Semantic meaning (vectors) |
| **Index type** | B-trees, hash maps | HNSW, IVF, Annoy |
| **Distance** | Exact match | Approximate nearest neighbor |
| **Speed** | Fast exact lookup | Fast approximate search |
| **Scalability** | Good for exact queries | Designed for high-dimensional vectors |

### The Curse of Dimensionality

With high-dimensional vectors (384+ dimensions), traditional indexing methods
break down:

```mermaid
flowchart LR
    D2["2D Space<br/>Points clustered near each other<br/>Tree index finds neighbors in O(log n)<br/>e.g., KD-tree, Ball tree"] -->|Works well| IDX2["Efficient indexing<br/>fast lookups"]
    D384["384D Space<br/>All points equidistant<br/>distance concentration phenomenon<br/>tree partitions become meaningless"] -->|Breaks down| IDX384["Standard indexes useless<br/>brute-force O(n) required"]

    style D2 fill:#27ae60,color:#fff
    style IDX2 fill:#27ae60,color:#fff
    style D384 fill:#e74c3c,color:#fff
    style IDX384 fill:#e74c3c,color:#fff
```

## What a Vector Database Does

A **vector database** is a database optimized for storing, indexing, and querying
high-dimensional vectors.

### Core Capabilities

1. **Vector storage**: Store millions of vectors efficiently
2. **Similarity search**: Find the K nearest neighbors to a query vector
3. **Vector indexing**: Use specialized indexes (HNSW, IVF) for sub-linear search
4. **Metadata storage**: Store and filter by document metadata alongside vectors
5. **Filtering**: Combine vector search with metadata filters (hybrid search)

### How It Works

```mermaid
flowchart LR
    Q[Query Text] --> QE[Query Embedding]
    QE --> VS[Vector Search Engine]
    VS --> IDX[Vector Index]
    IDX --> H1[Vector 1]
    IDX --> H2[Vector 2]
    IDX --> H3[Vector N]
    H1 --> D[Documents + Metadata]
    VS --> Results[Top-K Results]

    style Q fill:#3498db,color:#fff
    style VS fill:#e74c3c,color:#fff
    style IDX fill:#9b59b6,color:#fff
    style Results fill:#27ae60,color:#fff
```

## Vector Indexing

### Exact Search (Brute Force)

```mermaid
flowchart LR
    QV["Query Vector<br/>(384-dim)"] --> BF["Brute Force Search<br/>Compare against every stored vector"]
    BF --> CALC["Compute exact distances<br/>cosine / euclidean / dot product"]
    CALC --> SORT["Sort all results by distance"]
    SORT --> TOPK["Return exact Top-K<br/>100% accurate but O(n × d)"]
    CALC --> PERF["Performance note:<br/>O(n × d) per query<br/>n = number of vectors<br/>d = vector dimensions"]

    style QV fill:#3498db,color:#fff
    style BF fill:#9b59b6,color:#fff
    style CALC fill:#f39c12,color:#fff
    style SORT fill:#e74c3c,color:#fff
    style TOPK fill:#27ae60,color:#fff
    style PERF fill:#8e44ad,color:#fff
```

### Approximate Search

For large datasets, approximate methods trade a small amount of accuracy
for big speed gains:

| Method | How it works | Tradeoff |
|--------|-------------|----------|
| **HNSW** (Hierarchical Navigable Small World) | Graph-based, builds layers of connections | Best balance |
| **IVF** (Inverted File) | Clusters vectors, only searches nearby clusters | Fast, configurable recall |
| **Annoy** (Approximate Nearest Neighbors Oh Yeah) | Random projection trees | Fast, memory-mapped |
| **FAISS** | Multiple index types | Very fast, Facebook-built |

### HNSW Intuition

```mermaid
flowchart TD
    subgraph "Layer 0 (all points)"
        A1[Node A] -->|edge| A2[Node B]
        A2 -->|edge| A3[Node C]
        A3 -->|edge| A4[Node D]
        A4 -->|edge| A1
    end
    subgraph "Layer 1 (subset of points)"
        B1[Node A] --> B2[Node C]
        B2 --> B1
    end
    subgraph "Layer 2 (few points)"
        C1[Node A]
        C2[Node D]
    end

    style A1 fill:#3498db,color:#fff
    style B1 fill:#e74c3c,color:#fff
    style C1 fill:#27ae60,color:#fff
```

HNSW builds a hierarchy of graphs — start searching from the top layer
(coarse), navigate down to finer layers, and converge on the nearest neighbors.

## Vector Storage

Vectors are stored alongside their **payload** (metadata):

```json
{
  "id": 42,
  "vector": [0.23, -0.87, 0.45, ...],
  "payload": {
    "text": "The capital of France is Paris.",
    "document_id": "doc_001",
    "category": "geography",
    "language": "en"
  }
}
```

## Similarity Search

### Basic Search

```python
results = client.search(
    collection_name="docs",
    query_vector=[0.1, 0.2, ...],  # 384-dim query embedding
    limit=5,  # Return Top-5
)
```

Returns:
```python
[
    ScoredPoint(id=42, score=0.89, payload={"text": "..."}),
    ScoredPoint(id=17, score=0.85, payload={"text": "..."}),
    ...
]
```

### Search Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `query_vector` | The embedding to search for | Required |
| `limit` | How many results to return | 10 |
| `with_payload` | Include metadata in results | true |
| `with_vectors` | Include raw vectors in results | false |
| `score_threshold` | Minimum similarity score | None |
| `query_filter` | Metadata filter | None |

## Metadata and Filtering

Vector databases support **metadata filtering** — combining vector search
with structured filters:

```python
# Find French articles about cooking, semantically similar to query
results = client.search(
    collection_name="docs",
    query_vector=query_embedding,
    query_filter=Filter(
        must=[FieldCondition(key="language", match=MatchValue(value="fr"))],
        must_not=[FieldCondition(key="category", match=MatchValue(value="politics"))],
    ),
    limit=5,
)
```

## Approximate Nearest Neighbor (ANN) vs. Exact

| Aspect | Exact | Approximate |
|--------|-------|-------------|
| **Accuracy** | 100% exact | Configurable (90-99%) |
| **Speed** | Slower (O(n)) | Fast (O(log n)) |
| **Memory** | Low | Higher (index overhead) |
| **Use case** | Small datasets (<10K) | Large datasets (>100K) |

In practice, approximate search with 95-99% recall is acceptable for most
applications.

## In Our POC

We use Qdrant as our vector database:

```python
# app/services/vectordb.py
client = QdrantClient(url="http://localhost:6333")

# Create collection with cosine distance
client.recreate_collection(
    collection_name="genai-documents",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
)

# Store embeddings with metadata
client.upsert("genai-documents", points=[
    PointStruct(id="chunk_0", vector=[...], payload={"text": "...", "doc_id": "1"})
])

# Search
results = client.search("genai-documents", query_vector=[...], limit=5)
```

## Next Steps

- [Vector Indexing](indexing.md) — How HNSW and IVF work
- [ANN Search](ann-search.md) — Approximate nearest neighbors in detail
- [Metadata & Filtering](metadata-filtering.md) — Hybrid search
- [Database Comparison](comparison.md) — Qdrant vs. alternatives
