# Metadata Filtering

## What is metadata filtering?

**Metadata filtering** (also called **payload filtering**) allows you to search for vectors that also match certain metadata criteria. Instead of searching across all vectors, you search only within a subset defined by metadata conditions.

```
Query: "iPhone cases" (vector search)
Filter: category = "electronics" AND price < 50

Result: Only iPhone case vectors that are electronics and under $50
```

## How it works in Qdrant

Qdrant supports filtering via **payload conditions** in the search request. Filters can be applied before or after the vector search.

### Filter structure

Qdrant filters use a tree-like structure:

```python
from qdrant_client.http import models as qmodels

filter = qmodels.Filter(
    must=[  # ALL conditions must match (AND)
        qmodels.FieldCondition(
            key="category",
            match=qmodels.MatchValue(value="electronics"),
        ),
        qmodels.FieldCondition(
            key="price",
            match=qmodels.MatchValue(value=50),  # <= 50
            range=qmodels.Range(lte=50),
        ),
    ],
    should=[  # ANY condition matches (OR)
        qmodels.FieldCondition(
            key="brand",
            match=qmodels.MatchValue(value="Apple"),
        ),
        qmodels.FieldCondition(
            key="brand",
            match=qmodels.MatchValue(value="Samsung"),
        ),
    ],
)
```

### Supported filter operations

| Operation | Example |
|-----------|---------|
| Equality | `key = "value"` |
| Range | `price < 50`, `date >= "2024-01-01"` |
| In set | `category in ["electronics", "books"]` |
| Exists | `field exists` |
| Nested | `metadata.author.name = "Alice"` |
| Full-text | `match text in "long description"` |

## Pre-filtering vs. Post-filtering

The order of filtering relative to vector search significantly impacts performance and results.

### Pre-filtering

Filter first, then search only within the filtered subset:

```
All vectors: 1,000,000
Filter: category = "electronics" → 50,000 vectors
Vector search: search within 50,000 vectors
```

**Pros:**
- Faster search (fewer vectors to compare)
- Lower resource usage

**Cons:**
- May miss relevant results that were filtered out
- The filtered subset might not contain the true nearest neighbors
- Recall may decrease if the filter is too restrictive

### Post-filtering

Search across all vectors, then filter the results:

```
All vectors: 1,000,000
Vector search: search all 1,000,000 → top-100 results
Filter: category = "electronics" → 3 results (from top-100)
```

**Pros:**
- Higher recall (searches all vectors)
- Won't miss relevant vectors outside the filter
- More accurate final results

**Cons:**
- Slower (must search all vectors)
- If few results pass the filter, you waste computation on non-matching vectors
- May return fewer results than `top_k`

### Filter-first search

Some databases (like Qdrant) support **filter-first** search — if the filter is very selective (e.g., returns <1% of the dataset), the database can skip the index and scan only the filtered subset.

### Hybrid approach

Modern vector databases use adaptive strategies:

```
if filter_selectivity < 5%:
    use_pre_filtering()  # Filter is very selective
else:
    use_post_filtering()  # Filter matches many vectors
```

## Metadata in this project

### Current implementation

This POC stores metadata (payload) alongside each vector:

```python
# app/api/routes.py:68
payload = {"text": doc.text, "doc_id": doc.id, **(doc.metadata or {})}
```

Users can provide arbitrary metadata:

```json
{
  "id": "doc-1",
  "text": "Vector databases store embeddings...",
  "metadata": {
    "category": "database",
    "author": "Alice",
    "year": 2024
  }
}
```

This metadata is stored in Qdrant as payload and returned with search results.

### No filtering implemented

**The current search endpoint does NOT support filtering:**

```python
# app/api/routes.py:107-129
@router.post("/search", response_model=SearchResponse)
def search(
    query: str,
    top_k: int = 5,
    emb: EmbeddingService = Depends(get_embedding_service),
    vdb: VectorDBService = Depends(get_vector_db_service),
):
    query_vector = emb.embed(query)
    results = vdb.search(query_vector, top_k=top_k)
    # No filter parameter — searches all vectors
```

### How to add filtering (if desired)

To add metadata filtering to the search endpoint, you would:

1. Add a `filter` parameter to the search endpoint
2. Pass the filter to `VectorDBService.search()`
3. Use Qdrant's `Filter` model

```python
# Hypothetical enhancement to app/api/routes.py
@router.post("/search")
def search(
    query: str,
    top_k: int = 5,
    category: str | None = None,  # Filter parameter
    emb: EmbeddingService = Depends(get_embedding_service),
    vdb: VectorDBService = Depends(get_vector_db_service),
):
    query_vector = emb.embed(query)
    
    # Build Qdrant filter
    search_filter = None
    if category:
        search_filter = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="category",
                    match=qmodels.MatchValue(value=category),
                )
            ]
        )
    
    results = vdb.search(query_vector, top_k=top_k, filter=search_filter)
```

And update the `VectorDBService.search()` method:

```python
# Hypothetical enhancement to app/services/vector_db.py
def search(self, vector, top_k=5, filter=None):
    results = self.client.search(
        collection_name=self.collection_name,
        query_vector=vector,
        with_payload=True,
        with_vectors=False,
        limit=top_k,
        # Add filter:
        # filter=filter,  # Uncomment to enable
    )
```

## Practical filtering examples

If filtering were implemented, you could do:

### Filter by category

```bash
curl -X POST "http://localhost:8000/api/v1/search?query=database&top_k=3&category=database"
```

### Filter by date range

```bash
curl -X POST "http://localhost:8000/api/v1/search?query=password&top_k=5&created_after=2024-01-01"
```

### Filter by multiple criteria

```bash
curl -X POST "http://localhost:8000/api/v1/search?query=python&top_k=10&category=programming&author=Alice"
```

## Indexing metadata for fast filtering

Qdrant can **index** payload fields for faster filtering:

```python
# Configure index on collection creation
qmodels.VectorParams(
    size=384,
    distance=qmodels.Distance.COSINE,
)
# Also configure payload index:
# client.set_payload_index(collection_name, key="category")
```

### Indexed vs. non-indexed fields

| Field type | Indexed? | Filter speed |
|-----------|----------|-------------|
| `category` (low cardinality) | Yes | Fast (uses inverted index) |
| `author` (medium cardinality) | Yes | Fast |
| `text` (high cardinality) | No | Slow (linear scan) |
| `created_at` (date) | Yes | Fast (range query) |

### Index types

| Index type | Best for | Example |
|-----------|----------|---------|
| Keyword | Exact matches, low cardinality | `category = "database"` |
| Numeric | Range queries | `price < 50` |
| Geo | Geographic search | `location near (lat, lon)` |
| Text | Full-text search | `match text in description` |

## Pre-filtering vs. Post-filtering trade-offs summary

| Strategy | Best for | Trade-off |
|----------|----------|-----------|
| No filtering | Simple semantic search | Can't narrow by metadata |
| Pre-filtering | Very selective filters (<1% of data) | May miss relevant results |
| Post-filtering | Broad filters (>5% of data) | Slower but more complete |
| Hybrid (adaptive) | Mixed filter selectivity | Best overall, most complex |

## When to use metadata filtering

| Use case | Filter needed? |
|----------|----------------|
| Search across all documents | No |
| Filter by document type | Yes |
| Filter by source/author/date | Yes |
| Filter by access permissions | Yes (multi-tenant) |
| Search within a specific category | Yes |

Metadata filtering is essential for production vector search applications where users need to narrow results by structured criteria in addition to semantic relevance.