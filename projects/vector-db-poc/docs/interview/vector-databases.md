# Interview Q&A: Vector Databases

## Fundamentals

### Q1: Why do we need a vector database?

**A:** A vector database is optimized for **similarity search** — finding the most similar vectors to a query. Traditional databases (PostgreSQL, MongoDB) are built for exact-match queries and aggregations. They can store vectors but can't efficiently search them:

- **Exact match**: `WHERE id = 123` — B-tree index, O(log n)
- **Vector search**: `nearest neighbors of vector X` — requires comparing against all vectors, O(n) for brute-force

Vector databases use **ANN indexing** (HNSW, IVF) to achieve sub-linear search time while supporting semantic filtering.

### Q2: Can PostgreSQL store vectors?

**A:** Yes, via the `pgvector` extension. pgvector adds:
- A `vector` column type
- HNSW and IVFFLAT indexing
- SQL-based vector operations

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE items (id serial, embedding vector(384));
INSERT INTO items VALUES (1, '[0.1, 0.2, ...]');
SELECT * FROM items ORDER BY embedding <-> '[0.1, 0.2, ...]' LIMIT 5;
```

**Trade-offs vs. dedicated vector DBs:**
- **pgvector**: ACID transactions, SQL, easy migration — but slower search, fewer index options
- **Qdrant/Milvus**: Optimized for vector search, better performance — but no SQL, no ACID

### Q3: What is the difference between a vector database and a traditional database?

**A:**

| Aspect | Traditional DB | Vector DB |
|--------|----------------|-----------|
| Primary query | Exact match, range, join | k-NN similarity |
| Data type | Structured (numbers, strings) | High-dimensional vectors |
| Indexing | B-tree, hash, inverted index | HNSW, IVF, PQ |
| Query language | SQL | Vector query API or SQL extension |
| Consistency | Strong (ACID) | Eventual (usually) |

### Q4: What is ANN?

**A:** **Approximate Nearest Neighbor (ANN)** — finding the nearest vectors using an index structure that skips most vectors. Trade a small amount of accuracy (recall) for massive speed gains.

### Q5: What is HNSW?

**A:** **Hierarchical Navigable Small World** — an ANN algorithm that builds a multi-layer graph:

1. **Top layer**: Sparse graph for coarse navigation
2. **Lower layers**: Denser graphs for fine-grained search
3. **Search**: Start at top, navigate down, find candidates in the ef-sized list

- **Recall**: 95%+ with default parameters
- **Memory overhead**: ~20-30% of vector storage
- **Used by**: Qdrant (default), Pinecone, Milvus, Weaviate, Vespa

### Q6: What is IVF?

**A:** **Inverted File** — clusters vectors into cells (k-means), searches only the nearest cells:

1. **Training**: Cluster all vectors into k groups
2. **Search**: Find nearest cluster(s), search within them only

- **Parameters**: `nlist` (number of clusters), `nprobe` (clusters to search)
- **Pros**: Low memory, fast search
- **Cons**: Lower recall, requires re-clustering on insert
- **Used by**: FAISS, Qdrant, Milvus, Pinecone

### Q7: What is Product Quantization (PQ)?

**A:** **PQ** compresses vectors by splitting into sub-vectors and quantizing each:

1. Split a 384-dim vector into 32 sub-vectors of 12 dims
2. For each sub-vector, store only the closest of 256 centroids (1 byte)
3. Compressed vector: 32 bytes instead of 1,536 bytes

- **Compression ratio**: ~50x
- **Pros**: Massive memory savings, faster distance computation
- **Cons**: Lossy, lower recall
- **Variants**: OPQ (Optimized PQ) with rotation for better accuracy

### Q8: What is recall?

**A:** Recall measures the fraction of true nearest neighbors that the ANN search finds:

```
recall@k = |true_top_k ∩ ann_top_k| / k
```

Example: k=5, true nearest are [A,B,C,D,E], ANN returns [A,C,D,F,G] → recall = 3/5 = 60%.

- **recall@100%**: Exact search (brute-force)
- **recall@95%**: Excellent for most applications
- Trade speed for higher recall by tuning index parameters (ef, nprobe, etc.)

### Q9: What is precision?

**A:** Precision measures how many of the returned results are actually relevant:

```
precision@k = |true_top_k ∩ returned_top_k| / k
```

When both return exactly k results, precision@k = recall@k. They differ when:
- The search returns fewer results than k (e.g., due to score threshold)
- The search returns more results and you filter

### Q10: Exact search vs. approximate search?

**A:**

| Aspect | Exact | Approximate |
|--------|-------|-------------|
| Correctness | Guaranteed | Probabilistic (95%+ recall typically) |
| Speed | O(N) — linear scan | O(log N) — sub-linear |
| Memory | Low (just vectors) | Higher (index structures) |
| Scale | Millions max | Billions |
| Use case | Small datasets, critical accuracy | Production apps, large datasets |

### Q11: How do you scale vector search?

**A:** Several strategies:

1. **Sharding**: Partition vectors across multiple nodes (horizontal scaling)
2. **Replication**: Multiple copies of the index for read scalability
3. **Clustering**: HNSG graphs can be built per-shard
4. **Quantization**: Compress vectors (PQ) to fit more in memory
5. **Caching**: Cache frequent query results
6. **Hierarchical retrieval**: Use a coarse index to narrow down, then fine search
7. **Hybrid filtering**: Use keyword search to narrow candidates, then vector search the subset

Example at 1B scale:
- 10 shards × 100M vectors each
- HNSW index per shard
- Query fans out to all 10 shards in parallel
- Results merged and re-ranked

### Q12: What is a vector index?

**A:** A **vector index** is a data structure optimized for nearest-neighbor search in high-dimensional spaces. Unlike B-trees (for 1D values), vector indexes organize multi-dimensional data spatially.

Common types:
- **HNSW**: Graph-based, excellent balance of speed/accuracy
- **IVF**: Clustering-based, fast but lower recall
- **PQ**: Compression-based, lowest memory
- **FLAT**: No index, brute-force (exact)

### Q13: What is metadata filtering?

**A:** Also called **payload filtering** — restricting search to only vectors whose metadata matches certain conditions:

```
Search: "iPhone cases"
Filter: category = "electronics" AND price < 50

→ Only search vectors where category is "electronics" and price < 50
```

In Qdrant, this uses `Filter` and `FieldCondition` objects. The current POC stores metadata but does not implement filtering in its search endpoint.

### Q14: What is hybrid search?

**A:** Combining **keyword search** (BM25) and **vector search** (semantic) to improve results. Each method catches what the other misses:

- Vector search: catches synonyms ("car" → "automobile")
- Keyword search: catches exact terms ("iPhone 15 Pro")

Results can be fused using **Reciprocal Rank Fusion (RRF)** or **weighted sum**.

### Q15: What is the difference between metadata filtering and hybrid search?

**A:**

- **Metadata filtering**: Uses metadata to restrict which vectors to search (pre-filter) or which results to return (post-filter). It's a binary yes/no per vector.
- **Hybrid search**: Combines two different search methods (keyword + semantic) and merges their rankings. Both methods are active searches, not filters.

Filtering is about **eligibility**; hybrid search is about **ranking**.

## Database-Specific

### Q16: Why does this POC use Qdrant?

**A:** Qdrant is ideal for a learning POC because:

1. **Easy setup**: Single Docker container, REST + gRPC API
2. **Python client**: Clean API (`qdrant-client` package)
3. **HNSW by default**: Production-grade indexing out of the box
4. **Payload filtering**: Supports metadata alongside vectors
5. **Good documentation**: Clear examples and API reference
6. **ACID-like operations**: Upsert, delete, search in single transactions
7. **No vendor lock-in**: Self-hostable, open-source

### Q17: How does Qdrant store vectors internally?

**A:** Qdrant stores each vector as a **point** with:

1. **ID**: A UUID (Qdrant's internal ID, derived from UUID5 in this project)
2. **Vector**: The dense embedding array
3. **Payload**: JSON metadata (text, doc_id, user metadata)
4. **Index**: HNSW graph on top of vectors for fast search

When a search is performed, Qdrant:
1. Traverses the HNSW graph to find candidate neighbors
2. Computes exact cosine similarity for candidates
3. Returns top-K by score with their payloads

### Q18: What happens when you delete a point in Qdrant?

**A:** In this project, the delete operation:

1. Takes the original string ID (e.g., `"doc-2"`)
2. Converts it to UUID5: `uuid5(NAMESPACE_DNS, "doc-2")`
3. Tells Qdrant to delete that specific UUID

```python
# app/services/vector_db.py:64-68
def delete(self, ids: list[str]) -> int:
    self.client.delete(
        collection_name=self.collection_name,
        points_selector=qmodels.PointIdsList(
            points=[str(to_uuid(i)) for i in ids]
        ),
    )
```

Qdrant marks the point as deleted (tombstone) and updates the HNSW graph. The actual removal may happen asynchronously during compaction.