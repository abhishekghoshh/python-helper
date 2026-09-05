# Vector Database Comparison

## What is a vector database?

A **vector database** (or **vector store**) is a database optimized for storing and querying high-dimensional vectors. Unlike traditional databases that index scalar values, vector databases build specialized indexes (like HNSW graphs) to enable **approximate nearest neighbor (ANN)** search in sub-linear time.

## Why use a vector database?

| Task | Traditional DB | Vector DB |
|------|---------------|-----------|
| Find documents with exact keyword "hello" | ✅ Fast (inverted index) | ❌ Slow (no text index) |
| Find documents similar to "hello" by meaning | ❌ Linear scan (O(n)) | ✅ Fast (ANN, sub-linear) |
| Filter by date AND find similar by meaning | ✅ SQL with WHERE | ✅ With payload filtering |

## Comparison of major vector databases

### 1. Qdrant

![Qdrant logo](https://qdrant.tech/)

| Aspect | Detail |
|--------|--------|
| **Type** | Standalone (single-node + cluster) |
| **Language** | Rust (with C++/Python clients) |
| **Deployment** | Docker, binary, cloud (Qdrant Cloud) |
| **Indexing** | HNSW (default), IVF, custom quantization |
| **Filtering** | Yes (payload-based pre/post-filtering) |
| **Scalability** | Horizontal clustering (sharding, replication) |
| **API** | REST + gRPC |
| **Strengths** | Easy setup, great Python client, good docs, hybrid search |
| **Limitations** | Cluster mode requires Qdrant Cloud or self-managed Kubernetes |
| **Use cases** | Prototypes, production apps, RAG, embeddings |
| **This project** | ✅ Used as the vector database |

In this project, Qdrant is configured with:
- **Distance**: COSINE
- **Dimensions**: 384 (matching `all-MiniLM-L6-v2`)
- **Payload**: `{"text": ..., "doc_id": ...}` + user metadata

### 2. Pinecone

| Aspect | Detail |
|--------|--------|
| **Type** | Fully managed cloud |
| **Language** | Go (server), Python/Node/Go clients |
| **Deployment** | Managed SaaS (no self-hosting) |
| **Indexing** | HNSW, IVF, disk-based |
| **Filtering** | Yes (metadata filtering) |
| **Scalability** | Automatic (serverless index scaling) |
| **API** | REST + client SDKs |
| **Strengths** | Zero-ops, serverless, pay-per-use, multi-region |
| **Limitations** | Vendor lock-in, costs scale with usage, no self-hosting |
| **Use cases** | Production apps where you want to avoid ops |

### 3. Milvus

| Aspect | Detail |
|--------|--------|
| **Type** | Standalone + distributed |
| **Language** | Go (server), Python/Go/Node/Java clients |
| **Deployment** | Docker, Kubernetes (Helm charts) |
| **Indexing** | HNSW, IVF_FLAT, IVF_PQ, ANNOY, DISK-ANN |
| **Filtering** | Yes (filter + range + full-text) |
| **Scalability** | Yes (distributed, horizontal sharding) |
| **API** | gRPC + REST |
| **Strengths** | Massive scale (billions of vectors), multiple index types, cloud-native |
| **Limitations** | Complex deployment, heavy resource usage, steep learning curve |
| **Use cases** | Enterprise-scale vector search, recommendation systems |

### 4. Weaviate

| Aspect | Detail |
|--------|--------|
| **Type** | Standalone + cloud |
| **Language** | Go (server), Python/JS/Go clients |
| **Deployment** | Docker, Kubernetes, Weaviate Cloud |
| **Indexing** | HNSW, IVF, PQ, flat |
| **Filtering** | Yes (GraphQL filters, REST filters) |
| **Scalability** | Yes (sharding, replication) |
| **API** | GraphQL + REST |
| **Strengths** | GraphQL API, built-in ML modules (embedders, rerankers), multi-tenancy |
| **Limitations** | More complex config, GraphQL learning curve |
| **Use cases** | Apps needing GraphQL, built-in ML pipeline |

### 5. Chroma

| Aspect | Detail |
|--------|--------|
| **Type** | Embedded / server |
| **Language** | Python |
| **Deployment** | pip install, Docker |
| **Indexing** | HNSW |
| **Filtering** | Yes (where clause) |
| **Scalability** | Limited (single-node) |
| **API** | Python API + REST (Chroma Server) |
| **Strengths** | Simple API, designed for LLM apps, in-process mode |
| **Limitations** | Single-node only, less mature than Qdrant/Milvus |
| **Use cases** | LLM apps, prototypes, personal projects |

### 6. pgvector (PostgreSQL extension)

| Aspect | Detail |
|--------|--------|
| **Type** | Database extension |
| **Language** | C (extension), Python/Node/Java clients |
| **Deployment** | PostgreSQL extension (apt, brew, Docker) |
| **Indexing** | IVFFLAT, HNSW |
| **Filtering** | Yes (full SQL) |
| **Scalability** | PostgreSQL's built-in (vertical + streaming replication) |
| **API** | SQL |
| **Strengths** | Runs in existing PostgreSQL, ACID transactions, SQL queries |
| **Limitations** | Slower than dedicated vector DBs, limited indexing options |
| **Use cases** | Apps already using PostgreSQL, need ACID + vector search |

### 7. FAISS (Library, not a database)

| Aspect | Detail |
|--------|--------|
| **Type** | Library (C++/Python) |
| **Language** | C++ (with Python bindings) |
| **Deployment** | pip install, build from source |
| **Indexing** | IVF, HNSW, PQ, OPQ, flat |
| **Filtering** | No (manual filtering required) |
| **Scalability** | In-memory (can be slow for large datasets) |
| **API** | Python/C++ API |
| **Strengths** | Highly optimized, Facebook/Meta production-tested, many index types |
| **Limitations** | No persistence, no server, manual filtering, Python bindings only |
| **Use cases** | Prototyping, research, when you need full control |

### 8. Vespa

| Aspect | Detail |
|--------|--------|
| **Type** | Standalone / managed |
| **Language** | C++ (server), Java/Python/JS clients |
| **Deployment** | Docker, Vespa Cloud |
| **Indexing** | HNSW, IVF, cBBS, grid |
| **Filtering** | Yes (rich filtering) |
| **Scalability** | Yes (autoscaling, multi-zone) |
| **API** | REST + Java API |
| **Strengths** | Real-time inference, ranking, personalization, hybrid search |
| **Limitations** | Complex configuration, fewer language bindings |
| **Use cases** | Large-scale serving, personalization, news feeds |

### 9. Redis Vector Search (RedisStack)

| Aspect | Detail |
|--------|--------|
| **Type** | Redis module |
| **Language** | C (module), various Redis clients |
| **Deployment** | Redis module (Docker, Redis Cloud) |
| **Indexing** | HNSW, FLAT (brute-force) |
| **Filtering** | Yes (Redis query syntax) |
| **Scalability** | Redis clustering (horizontal) |
| **API** | Redis commands (FT.SEARCH, etc.) |
| **Strengths** | In-memory, fast, existing Redis ecosystem |
| **Limitations** | Memory-bound (expensive for large vectors), Redis-only |
| **Use cases** | Caching + search, apps already using Redis |

### 10. Elasticsearch / OpenSearch kNN

| Aspect | Detail |
|--------|--------|
| **Type** | Search engine + vector plugin |
| **Language** | Java (server), various clients |
| **Deployment** | Docker, cloud (Elastic Cloud, AWS OpenSearch) |
| **Indexing** | HNSW, IVF (experimental) |
| **Filtering** | Yes (full DSL/query language) |
| **Scalability** | Yes (sharding, replicas) |
| **API** | REST |
| **Strengths** | Hybrid search (keyword + vector), mature ecosystem, full-text search |
| **Limitations** | Vector indexing is newer feature, higher memory usage |
| **Use cases** | Apps needing both keyword and vector search, existing Elastic users |

## Comparison table

| Database | Type | Indexing | Filtering | Scalability | Managed | Best for |
|----------|------|----------|-----------|-------------|---------|----------|
| **Qdrant** | Standalone | HNSW, IVF | ✅ Yes | Medium | ✅ Cloud | General-purpose, this POC |
| **Pinecone** | Managed | HNSW, IVF | ✅ Yes | Auto | ✅ Yes | Serverless, zero-ops |
| **Milvus** | Standalone/Distributed | Many | ✅ Yes | High | ❌ No | Massive scale |
| **Weaviate** | Standalone/Cloud | HNSW, IVF | ✅ Yes | High | ✅ Cloud | GraphQL, built-in ML |
| **Chroma** | Embedded/Server | HNSW | ✅ Yes | Low | ✅ Cloud | LLM apps, prototyping |
| **pgvector** | Extension | IVFFLAT, HNSW | ✅ Yes (SQL) | Medium | ❌ No | PostgreSQL users |
| **FAISS** | Library | Many | ❌ No | In-memory | ❌ No | Research, prototyping |
| **Vespa** | Standalone/Managed | Many | ✅ Yes | High | ✅ Cloud | Large-scale serving |
| **Redis** | Module | HNSW, FLAT | ✅ Yes | Medium | ✅ Cloud | Redis ecosystem |
| **Elasticsearch** | Engine | HNSW | ✅ Yes | High | ✅ Yes | Hybrid keyword+vector |

## Choosing a vector database

| If you need... | Choose |
|----------------|--------|
| Simplest setup for a POC | Qdrant, FAISS, Chroma |
| Zero operations | Pinecone, Weaviate Cloud, Vespa Cloud, Elastic Cloud |
| Maximum scale (billions of vectors) | Milvus, Vespa |
| Existing PostgreSQL investment | pgvector |
| LLM-native (simple Python API) | Chroma |
| GraphQL API | Weaviate |
| Both keyword AND vector search | Elasticsearch, Qdrant, pgvector |
| Full control / research | FAISS |
| In-memory speed | Redis Vector Search |
| Real-time personalization | Vespa |