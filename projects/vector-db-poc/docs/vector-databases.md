# Vector Databases & Embeddings

A deep dive into vector representations, embedding models, vector databases, and how they power modern AI applications.

## Table of contents

1. [Vectors and embeddings](#1-vectors-and-embeddings)
2. [How embedding models work](#2-how-embedding-models-work)
3. [Types of vector databases](#3-types-of-vector-databases)
4. [Vector search algorithms](#4-vector-search-algorithms)
5. [Distance and similarity metrics](#5-distance-and-similarity-metrics)
6. [Vector databases vs. traditional databases](#6-vector-databases-vs-traditional-databases)
7. [Hybrid search](#7-hybrid-search)
8. [Production considerations](#8-production-considerations)
9. [Applications and use cases](#9-applications-and-use-cases)
10. [Glossary](#10-glossary)

---

## 1. Vectors and Embeddings

### What is a vector?

In the context of machine learning and databases, a **vector** is an array of numbers (floats) that represents data in a high-dimensional space. Each number in the array is a **dimension**, and the position of the vector in that space encodes semantic or structural information about the original data.

For example, the sentence *"How do I reset my password?"* might be represented as:

```
[0.012, -0.045, 0.033, 0.008, -0.019, ...]  (384 dimensions)
```

### What is an embedding?

An **embedding** is the process of converting raw data (text, images, audio) into a vector representation. The resulting vector, called an **embedding vector** or simply **embedding**, captures the semantic meaning of the input in a way that mathematically similar inputs produce vectors that are geometrically close to each other.

### Properties of good embeddings

- **Semantic proximity**: Similar inputs produce similar vectors (e.g., "car" and "automobile" embed to nearby points)
- **Dimensionality**: Typically 128–4,096 dimensions. Lower dimensions are faster but less expressive; higher dimensions capture more nuance but are more expensive
- **Normalization**: Many systems normalize vectors to unit length, making cosine similarity equivalent to dot product

### How embeddings are generated

Modern embeddings are produced by deep neural networks — typically **neural language models** (transformers) for text:

```
text → tokenizer → tokens → transformer layers → hidden states → embedding vector
```

The network is trained on massive datasets so that semantically related inputs produce similar hidden states. The embedding is then extracted from one or more layers of the network.

---

## 2. How Embedding Models Work

### Text embedding models

| Model | Dimensions | Provider | Notes |
|-------|-----------|----------|-------|
| `all-MiniLM-L6-v2` | 384 | Sentence Transformers | Lightweight, good general-purpose |
| `all-mpnet-base-v2` | 768 | Sentence Transformers | Higher quality, larger model |
| `text-embedding-ada-002` | 1536 | OpenAI | API-based, very popular |
| `text-embedding-3-small` | 512 | OpenAI | Configurable dimensions |
| `text-embedding-3-large` | 3072 | OpenAI | Highest quality OpenAI model |
| `gte-base` | 768 | Thenlper | Google-funded bilingual model |
| `bge-small-en` | 384 | BAAI | Strong retrieval performance |
| `cohere-embed-english-v3.0` | 1024 | Cohere | API-based, supports multilingual |

### Choosing a model

Consider these factors:

- **Quality**: Measured by retrieval accuracy on benchmarks like MTEB (Massive Text Embedding Benchmark)
- **Speed**: Inference latency — smaller models (768M params) run faster than large ones (1.3B params)
- **Dimensions**: Affects storage cost and search speed (see [ScaNN paper](https://arxiv.org/abs/2105.07091) for analysis)
- **Cost**: Local models (sentence-transformers) have no per-query cost; API models charge per 1,000 tokens
- **Multilingual support**: Some models handle many languages; others are English-only

### Multi-modal embeddings

Embeddings aren't limited to text. **Multi-modal embedding models** produce vectors for images, audio, and other modalities:

- **Image embeddings**: CLIP, ResNet, ViT — images embedded into the same space as text
- **Audio embeddings**: CLAP, WAV2VEC — audio embedded alongside text
- **Unified models**: CLIP embeds both images and text into a shared space, enabling cross-modal search (e.g., find images using text queries)

---

## 3. Types of Vector Databases

Vector databases (or **vector stores**) are databases optimized for storing and querying high-dimensional vector data. They come in several flavors:

### 3.1 Purpose-built vector databases

These are databases designed primarily for vector search:

| Database | Type | Key Features |
|----------|------|-------------|
| **Qdrant** | Standalone / Rust | Full-text search hybrid, payload filtering, disk-based storage, gRPC + REST API |
| **Pinecone** | Managed cloud | Serverless, multi-region, pay-per-use, automatic indexing |
| **Weaviate** | Standalone / Go | GraphQL API, built-in ML modules, hybrid search, multi-tenancy |
| **Milvus** | Standalone / Go | Distributed, horizontal scaling, multiple index types, Kubernetes-native |
| **Vespa** | Standalone / C++ | Real-time, hybrid search, ranking, serving framework |
| **Chroma** | Embedded / Python | Lightweight, designed for LLM apps, in-process or server mode |
| **FAISS** | Library (C++/Python) | Facebook's similarity search library, no built-in server, high performance |

### 3.2 Vector search libraries (in-process)

These are libraries rather than databases — they provide vector search algorithms but no persistence or network API:

- **FAISS** (Facebook): Highly optimized C++ library with Python bindings
- **ScaNN** (Google): TensorFlow-based, optimized for recommendation systems
- **Annoy** (Spotify): Tree-based, memory-mapped, good for read-heavy workloads
- **NMSLIB** (Yahoo): Multiple algorithms, easy to use

### 3.3 Extended traditional databases

Some relational and NoSQL databases have added vector search extensions:

| Database | Extension | Notes |
|----------|-----------|-------|
| **PostgreSQL** | `pgvector` | SQL-based vector search, integrates with existing Postgres ecosystem |
| **Redis** | Redis Vector Set / RedisStack | In-memory, pub/sub integration, simple deployment |
| **Elasticsearch** | kNN plugin | Hybrid with full-text search, Lucene-based |
| **MongoDB** | Atlas Vector Search | Native vector type, integrates with document model |

### 3.4 Choosing a vector database

| Need | Recommendation |
|------|----------------|
| Learning / POC | Qdrant, FAISS, Chroma |
| Production with full control | Qdrant, Milvus, Weaviate |
| Serverless / managed | Pinecone, Weaviate Cloud |
| SQL integration | PostgreSQL + pgvector |
| LLM apps | Chroma, Pinecone |
| Massive scale | Milvus, Vespa |

---

## 4. Vector Search Algorithms

Finding the k most similar vectors (k-NN) in a dataset is the core operation of a vector database. Exact search is computationally expensive in high dimensions, so most databases use **approximate nearest neighbor (ANN)** algorithms.

### Exact search

- **Linear scan**: Compare query against every vector. Simple, accurate, but slow — O(n) per query
- **Brute-force**: Same as linear scan but optimized with matrix operations (BLAS)

### Approximate search

| Algorithm | How it works | Trade-offs |
|-----------|-------------|------------|
| **IVF** (Inverted File) | Clusters vectors into groups; only searches within nearby clusters | Fast, but can miss results in distant clusters |
| **HNSW** (Hierarchical NMS) | Builds a multi-layer graph; traverses from top layer down to find neighbors | Excellent recall, moderate memory overhead |
| **PQ** (Product Quantization) | Compresses vectors into codes; searches compressed space | Low memory, lower recall |
| **OPQ** (Optimized PQ) | Improves PQ with rotation | Better accuracy than PQ |
| **ANNOY** | Random projection trees; memory-mapped | Fast reads, immutable index (requires rebuild on insert) |
| **Scann** | Hybrid partitioning + quantization | Optimized for TensorFlow pipelines |

### Index types in Qdrant

Qdrant supports several index configurations via `VectorParams`:

```python
from qdrant_client.http import models as qmodels

# HNSW index (default for most workloads)
qmodels.VectorParams(
    size=384,
    distance=qmodels.Distance.COSINE,
    on_disk_payload=True,
)

# IVF (Inverted File) — faster for large datasets
qmodels.VectorParams(
    size=384,
    distance=qmodels.Distance.COSINE,
    quantization_config=qmodels.ScalarQuantization(
        quant_type=qmodels.QuantizationType.INT8,
        always_ram=True
    )
)
```

---

## 5. Distance and Similarity Metrics

The **distance metric** determines how vector similarity is computed. It must be consistent between embedding generation and storage/retrieval.

### Cosine similarity

Measures the angle between two vectors, ignoring magnitude:

```
cos(u, v) = (u · v) / (||u|| × ||v||)
```

- Range: `[-1, 1]` (typically `[0, 1]` for embeddings, where 1 = identical)
- Works well for normalized embeddings
- **Qdrant default** in this POC

### Euclidean distance (L2)

The straight-line distance between two points:

```
L2(u, v) = √(Σ(uᵢ - vᵢ)²)
```

- Range: `[0, ∞)` (0 = identical)
- Sensitive to vector magnitude
- Good when both direction and magnitude matter

### Dot product

The sum of element-wise products:

```
dot(u, v) = Σ(uᵢ × vᵢ)
```

- Range: `(-∞, ∞)` (unbounded)
- Equivalent to cosine similarity when vectors are normalized
- Used by OpenAI's `text-embedding-ada-002`

### Manhattan distance (L1)

Sum of absolute differences:

```
L1(u, v) = Σ|uᵢ - vᵢ|
```

- Less common for embeddings
- More robust to outliers than L2

### Choosing a metric

| Metric | Best for |
|--------|----------|
| Cosine | Semantic similarity, normalized embeddings |
| Dot product | OpenAI embeddings, normalized vectors |
| Euclidean | Spatial data, when magnitude matters |

---

## 6. Vector Databases vs. Traditional Databases

| Aspect | Traditional DB | Vector DB |
|--------|---------------|-----------|
| Primary query | Exact match, range, join | k-NN similarity |
| Data type | Structured (numbers, strings) | High-dimensional vectors |
| Query language | SQL | Vector query API or SQL extension |
| Indexing | B-tree, hash | HNSW, IVF, PQ |
| Consistency | ACID | Eventual consistency in distributed setups |
| Scaling | Vertical or sharding | Horizontal (partitions, sharding) |

### When to use each

- **Traditional DB**: Exact lookups, transactions, joins, aggregations
- **Vector DB**: Similarity search, recommendation, semantic search, LLM retrieval
- **Hybrid**: Many applications need both — use a traditional DB alongside a vector DB, or use extended databases (e.g., PostgreSQL + pgvector)

---

## 7. Hybrid Search

**Hybrid search** combines vector (semantic) search with keyword (sparse) search to improve results.

### How it works

1. Run a keyword search (BM25) to find documents matching exact terms
2. Run a vector search to find semantically similar documents
3. **Reciprocal Rank Fusion (RRF)** merges and re-ranks results:

```
score(d) = Σ 1 / (rank_fusion_constant + rank_query(d))
```

### In Qdrant

Qdrant supports hybrid search natively:

```python
# Sparse vector (keyword) + dense vector (semantic)
results = client.search(
    collection_name="my_collection",
    query_text="how to reset password",  # BM25
    query_vector=embedding,               # dense embedding
)
```

### Benefits

- Catches documents that match keywords but not semantics
- Reduces false positives from purely semantic search
- Improves overall recall and precision

---

## 8. Production Considerations

### Vector dimensionality

- **Lower** (128–384): Faster search, less storage, lower quality
- **Higher** (768–3,072): Better quality, more storage, slower search

### Storage and memory

- Vectors are typically stored in RAM for fast access, or on disk for large datasets
- Payloads (metadata) can be stored on disk separately
- Quantization can compress vectors (e.g., 384 floats → 384 int8 values)

### Indexing time and updates

- Building an index takes time — HNSW graphs need to be constructed or updated
- **Insert-heavy** workloads benefit from batch upserts
- Some indexes are **immutable** (e.g., Annoy) and require rebuilding on insert

### Scalability

- **Vertical**: Single node with sufficient RAM — simple, limited by hardware
- **Horizontal**: Distributed across multiple nodes (Milvus, Weaviate clusters, Qdrant clusters)
- **Sharding**: Vectors partitioned by hash or range; queries fan out to all shards

### Monitoring

Key metrics to track:
- Query latency (p50, p95, p99)
- Recall@k (ratio of relevant results retrieved)
- Throughput (queries per second)
- Memory usage and index size
- Cache hit rates

---

## 9. Applications and Use Cases

### Semantic search

Instead of matching keywords, find documents based on meaning:

```
Query: "How do I change my password?"
Matches: "Password reset instructions", "Account security settings"
```

### Recommendation systems

Find similar items based on embeddings:

```
User likes: Item A, Item B
→ Find items with similar embeddings → Recommend Item C, Item D
```

### LLM / RAG (Retrieval-Augmented Generation)

1. User asks a question
2. Retrieve relevant documents from a vector DB
3. Pass retrieved context to an LLM along with the query
4. LLM generates an answer grounded in the retrieved documents

### Anomaly detection

Find outliers in data:

```
1. Embed all data points
2. Find points farthest from their neighbors
3. Flag as anomalies
```

### Duplicate detection

Find near-duplicate items (documents, images, products):

```
1. Embed all items
2. Search for each item's nearest neighbor
3. If the neighbor is very close → potential duplicate
```

### Cross-modal search

Using multi-modal embeddings:

```
Query: "a dog playing in the snow" (text)
→ Find: images of dogs in snow
```

---

## 10. Glossary

- **Vector**: An array of numbers representing data in a high-dimensional space
- **Embedding**: The process or result of converting data into a vector representation
- **Embedding model**: A machine learning model that produces embeddings (e.g., sentence-transformers, OpenAI text-embedding models)
- **Dimensionality**: The number of elements in a vector (e.g., 384, 768, 1536)
- **k-NN (k-Nearest Neighbors)**: Finding the k most similar vectors to a query vector
- **ANN (Approximate Nearest Neighbor)**: Algorithms that find approximate nearest neighbors faster than exact search
- **Cosine similarity**: Similarity metric based on the angle between vectors
- **Euclidean distance (L2)**: Straight-line distance between two points in space
- **Dot product**: Sum of element-wise products of two vectors
- **Payload**: Metadata associated with a vector (e.g., text content, category, timestamp)
- **Collection**: A logical grouping of vectors in a vector database (analagous to a table)
- **Point**: A single vector plus its ID and optional payload
- **Index**: A data structure that accelerates vector search (e.g., HNSW, IVF, PQ)
- **Quantization**: Reducing the precision of vector values (e.g., float32 → int8) to save memory
- **Hybrid search**: Combining keyword search and vector search
- **RRF (Reciprocal Rank Fusion)**: A method for combining ranked results from multiple search methods
- **MTEB**: Massive Text Embedding Benchmark — a standard evaluation suite for embedding models
- **ScaNN**: Scalable Nearest Neighbors — Google's library for efficient vector search
