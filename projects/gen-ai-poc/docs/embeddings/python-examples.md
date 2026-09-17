# Embeddings: Python Examples

This page provides hands-on Python examples for working with embeddings,
similarity computation, and semantic search.

## Setup

### Installing dependencies

```bash
# Local embeddings (no API key needed)
poetry add sentence-transformers scikit-learn numpy

# Cloud embeddings (requires API key)
poetry add openai
```

## Example 1: Generate Embeddings with sentence-transformers

```python
from sentence_transformers import SentenceTransformer
import numpy as np

# Load a pre-trained embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Text to embed
texts = [
    "The cat sat on the mat.",
    "A feline rested on a rug.",
    "The stock market crashed today.",
]

# Generate embeddings
embeddings = model.encode(texts)

print(f"Shape: {embeddings.shape}")  # (3, 384)
print(f"Dimensions: {len(embeddings[0])}")  # 384
```

## Example 2: Compute Similarity Metrics

```python
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances

# Assume we have embeddings from Example 1
emb_cat = embeddings[0]  # "The cat sat on the mat"
emb_feline = embeddings[1]  # "A feline rested on a rug"
emb_stock = embeddings[2]  # "The stock market crashed"

# Cosine similarity
cos_sim = cosine_similarity([emb_cat], [emb_feline])[0][0]
print(f"Cosine (cat/feline): {cos_sim:.4f}")  # ~0.7-0.9

cos_diff = cosine_similarity([emb_cat], [emb_stock])[0][0]
print(f"Cosine (cat/stock): {cos_diff:.4f}")  # Lower

# Euclidean distance
euclid_same = euclidean_distances([emb_cat], [emb_feline])[0][0]
euclid_diff = euclidean_distances([emb_cat], [emb_stock])[0][0]
print(f"Euclidean (same meaning): {euclid_same:.4f}")  # Smaller
print(f"Euclidean (different): {euclid_diff:.4f}")  # Larger

# Dot product
dot_same = np.dot(emb_cat, emb_feline)
dot_diff = np.dot(emb_cat, emb_stock)
print(f"Dot product (same): {dot_same:.4f}")  # Larger
print(f"Dot product (different): {dot_diff:.4f}")  # Smaller
```

## Example 3: Semantic Search

```python
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")

# Documents in a knowledge base
documents = [
    "Python is a programming language created by Guido van Rossum.",
    "The Eiffel Tower is in Paris, France.",
    "Machine learning is a subset of artificial intelligence.",
    "The capital of Japan is Tokyo.",
    "Docker is a platform for building and running containers.",
]

# Index documents
doc_embeddings = model.encode(documents)

# User query
query = "How do I containerize my application?"
query_embedding = model.encode([query])[0]

# Find the most similar document
scores = cosine_similarity([query_embedding], doc_embeddings)[0]
best_idx = np.argmax(scores)

print(f"Query: {query}")
print(f"Best match: {documents[best_idx]}")
print(f"Score: {scores[best_idx]:.4f}")
```

## Example 4: OpenAI Embeddings

```python
import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key="your-api-key")

async def embed_with_openai(texts: list[str]) -> list[list[float]]:
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )
    # Sort by index to preserve order
    data = sorted(response.data, key=lambda d: d.index)
    return [d.embedding for d in data]

# Usage
texts = ["Hello", "World", "Foo"]
embeddings = asyncio.run(embed_with_openai(texts))
print(f"Dimensions: {len(embeddings[0])}")  # 1536
```

## Example 5: Embedding a Vector Database

```python
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")
client = QdrantClient(url="http://localhost:6333")

# 1. Create collection
client.recreate_collection(
    collection_name="my-docs",
    vectors_config=models.VectorParams(
        size=384,  # Match embedding dimensions
        distance=models.Distance.COSINE,
    ),
)

# 2. Add documents with embeddings
documents = ["AI is transforming software.", "The sky is blue."]
embeddings = model.encode(documents)

for i, (doc, emb) in enumerate(zip(documents, embeddings)):
    client.upsert(
        collection_name="my-docs",
        points=[models.PointStruct(
            id=i,
            vector=emb.tolist(),
            payload={"text": doc},
        )],
    )

# 3. Search
query = "What's changing in software development?"
query_emb = model.encode([query])[0].tolist()

results = client.search(
    collection_name="my-docs",
    query_vector=query_emb,
    limit=3,
)

for r in results:
    print(f"Score: {r.score:.4f}, Text: {r.payload['text']}")
```

## Example 6: All Three Metrics from Our POC

The POC's embedding service computes all metrics in one call:

```bash
curl -X POST http://localhost:8000/api/v1/embeddings/similarity \
  -H "Content-Type: application/json" \
  -d '{
    "text_a": "A happy dog playfully runs through the park",
    "text_b": "A joyful canine dashes across the field"
  }'
```

Response:
```json
{
  "cosine": 0.8923,
  "euclidean": 1.12,
  "dot_product": 84.3
}
```

## Key Takeaways

1. **Embeddings convert text to vectors** — the same way every model does it,
   just with different training objectives
2. **Cosine similarity** is best for semantic similarity (ignores vector length)
3. **Euclidean distance** measures absolute distance in space
4. **Dot product** is fast for search but combines magnitude and direction
5. **Semantic search** beats keyword search when meaning matters more than exact words
6. **Local models** are free and fast; **cloud models** are higher quality but cost money

## Next Steps

- Try the POC's `/api/v1/embeddings/similarity` endpoint
- Try the POC's `/api/v1/embeddings/generate` endpoint
- Read [Vector Databases](../vector-databases/what-is-vdb.md) for storing and searching embeddings
