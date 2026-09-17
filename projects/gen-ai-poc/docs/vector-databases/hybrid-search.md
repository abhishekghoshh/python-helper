# Hybrid Search

## What Is Hybrid Search?

Hybrid search is a retrieval technique that **combines multiple search methods**
to improve the quality and relevance of results. In the context of vector databases
and RAG, hybrid search typically combines:

1. **Semantic search** (vector similarity) — finds documents semantically related
   to the query, even if exact words don't match.
2. **Keyword search** (lexical/Boolean search) — finds documents that contain exact
   term matches.

By combining both approaches, hybrid search can overcome the limitations of each
individual method.

## Why Hybrid Search?

### Limitations of Pure Semantic Search

Vector-based semantic search is powerful but has blind spots:

- **Rare entities**: Named entities, SKUs, technical codes, or unusual terminology
  may not have strong vector representations.
- **Exact matching needed**: Sometimes you need exact matches for filters, tags,
  or identifiers.
- **Over-generalization**: Very common terms can produce high-recall but low-precision
  results.

### Limitations of Pure Keyword Search

Traditional keyword search (BM25, TF-IDF) is precise but brittle:

- **Synonyms and paraphrases**: "car" won't match "automobile".
- **Conceptual queries**: "how to fix a leaking pipe" won't match documents about
  "plumbing repair".
- **Context ignored**: Keywords don't capture meaning.

## How Hybrid Search Works

The core idea is to compute scores from both methods and combine them. The two
most common strategies are:

### 1. Score Reciprocal Rank Fusion (RRF)

Reciprocal Rank Fusion combines rankings from multiple result sets:

```python
def reciprocal_rank_fusion(ranked_lists, k=60):
    """
    Combine multiple ranked result lists using RRF.
    
    k: a constant (typically 60) that controls the
       weight given to higher-ranked results.
    """
    scores = {}
    for ranked_list in ranked_lists:
        for rank, doc_id in enumerate(ranked_list):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
    return sorted(scores.keys(), key=scores.get, reverse=True)
```

RRF doesn't require score normalization since it works with ranks, not scores.

### 2. Weighted Score Combination

Scores are normalized and combined with weights:

```python
# Example: 70% semantic, 30% keyword
final_score = 0.7 * normalized_vector_score + 0.3 * normalized_keyword_score
```

This approach requires normalization because different methods produce scores
on different scales.

## Hybrid Search in Vector Databases

### Qdrant

Qdrant supports hybrid search via `query_points` with a `FusionQuery`:

```python
from qdrant_client import QdrantClient
from qdrant_client.http import models

results = client.query_points(
    collection_name="documents",
    query=models.FusionQuery(
        fusion=models.Fusion.DFR  # Reciprocal Rank Fusion
    ),
    with_payload=True,
    limit=5,
)(collection_name="documents")
```

Qdrant can also combine sparse (keyword) and dense (embedding) vectors
in a single search.

### Weaviate

Weaviate supports hybrid search natively through its
[Hybrid Search API](https://weaviate.io/developers/weaviate/api/graphql/additional-parameters#hybrid):

```graphql
{
  Get {
    Article(
      hybrid: {
        query: "machine learning pipelines",
        alpha: 0.7,  # weight: 0.7 vector, 0.3 keyword
        fusionType: RRF
      }
    ) {
      title
      content
    }
  }
}
```

### Elasticsearch

Elasticsearch 7.3+ supports `script_score` queries that combine `knn`
(vector) and `match` (keyword) scores:

```json
{
  "query": {
    "script_score": {
      "query": { "match": { "content": "neural networks" } },
      "script": {
        "source": "doc['vector'].l2norm(param('query_vector'))"
      }
    }
  }
}
```

### pgvector (PostgreSQL)

pgvector supports hybrid search using the `sql_sparse_dictionary`
extension or custom queries combining `ts_rank` (keyword) with
embedding distance:

```sql
SELECT *, 
  0.7 * (1 - embedding <#> '[...]' ) + 
  0.3 * ts_rank(text_tsv, plainto_tsquery('neural networks'))
  AS combined_score
FROM documents
ORDER BY combined_score DESC
LIMIT 5;
```

## When to Use Hybrid Search

| Scenario | Pure Vector | Pure Keyword | Hybrid |
|----------|------------|-------------|--------|
| Conceptual queries | ✅ | ❌ | ✅ |
| Exact term matching | ❌ | ✅ | ✅ |
| Named entities / SKUs | ⚠️ | ✅ | ✅ |
| Multi-language | ✅ | ❌ | ✅ |
| Short queries | ⚠️ | ⚠️ | ✅ |

## Summary

Hybrid search is a powerful technique that leverages both semantic
understanding and lexical precision. Most production RAG systems use
hybrid retrieval to improve recall and precision simultaneously.

Key takeaways:

- Hybrid search combines vector search + keyword search.
- **RRF** is the most common fusion method (no score normalization needed).
- Most modern vector databases support hybrid search natively.
- Use hybrid search when you need both semantic understanding and exact matching.

## Next Steps

- Read [What is a Vector Database?](what-is-vdb.md)
- Read [Approximate Nearest-Neighbor Search](ann-search.md)
- Read the [RAG Retrieval Guide](../rag/retrieval.md)
