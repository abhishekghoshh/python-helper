# Concepts

## What is a vector embedding?

A **vector embedding** is a dense numeric array that represents the semantic meaning of a piece of data — typically text, but also images, audio, or any modality that can be projected into a vector space.

For example, the sentence *"How do I reset my password?"* might embed to a 384-dimensional vector like:

```
[0.012, -0.045, 0.033, ...]
```

The key property: **semantically similar inputs produce similar vectors**. So *"How do I change my password?"* will have a vector very close to the one above, even though the words differ.

This POC uses the `all-MiniLM-L6-v2` model from sentence-transformers, which maps text to 384-dimensional vectors.

## Why vectors instead of keywords?

| Keywords (BM25)           | Vectors (Embedding Search)              |
|---------------------------|------------------------------------------|
| Match exact tokens        | Match meaning, not just words            |
| Misses synonyms           | "car" ≈ "automobile"                     |
| No ranking by relevance   | Ranked by semantic similarity            |
| No context awareness      | Context-aware representation             |

## What is a vector database?

A **vector database** (or **vector store**) is a database optimized for storing and querying high-dimensional vectors. Key operations:

1. **Insert**: store a vector alongside metadata (payload)
2. **Search (k-NN)**: find the `k` nearest neighbors to a query vector
3. **Delete**: remove vectors by ID

Qdrant (used in this POC) supports:
- Multiple distance metrics (cosine, Euclidean, dot product)
- Payload filtering during search
- Horizontal scaling and replication
- Disk-based and in-memory storage

## Distance metrics

This POC uses **cosine similarity**, which measures the angle between two vectors regardless of magnitude. The score ranges from 0 (completely dissimilar) to 1 (identical direction).

Other common metrics:

- **Euclidean distance** (`L2`): straight-line distance
- **Dot product** (`Dot`): used by some models (e.g., OpenAI), scores can be negative
