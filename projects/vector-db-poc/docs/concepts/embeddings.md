# Embeddings

## What is an embedding?

An **embedding** is a dense vector of numbers that represents the semantic meaning of a piece of data — typically text, but also images, audio, or any modality that can be projected into a vector space.

The key property: **semantically similar inputs produce similar vectors**. Two sentences that mean the same thing will have vectors that are close together in the vector space, even if the actual words differ.

For example, with the `all-MiniLM-L6-v2` model used in this project:

```
Text: "How do I reset my password?"
Embedding: [0.012, -0.045, 0.033, -0.019, ..., 0.022]  (384 dimensions)

Text: "How do I change my password?"
Embedding: [0.011, -0.043, 0.031, -0.018, ..., 0.021]  (384 dimensions)

Cosine similarity: 0.94  (very similar)
```

Even though the sentences use different words, their embeddings are close because they carry the same meaning.

## Why embeddings are useful

### Keyword search limitations

Traditional keyword search (like BM25 used in Elasticsearch) matches documents containing the exact query terms:

```
Query: "reset password"
Matches: documents containing "reset" AND "password"
Misses: documents about "password recovery" (different words, same meaning)
```

### Semantic search with embeddings

Embedding-based search matches by meaning:

```
Query: "reset password" → vector_q
Documents:
  - "How to change your password" → vector_a, similarity: 0.89 ✓
  - "Password reset instructions" → vector_b, similarity: 0.85 ✓
  - "Contact customer support"   → vector_c, similarity: 0.12 ✗
```

Even though "change" ≠ "reset", the semantic similarity captures that both relate to password management.

## How embeddings represent meaning

Embeddings work because the underlying neural networks are trained on massive text corpora. During training, the network learns that certain patterns of activation across dimensions correspond to certain meanings.

### The vector space model

Think of each dimension as an **implicit feature** — the model learns what each dimension should represent. For example:

- Dimension 127 might encode "technical vs. casual tone"
- Dimension 42 might encode "question vs. statement"
- Dimension 256 might encode "positive vs. negative sentiment"

These features are **latent** — the model learns them automatically, and we don't need to know what each individual dimension means. The collective pattern across all 384 dimensions encodes the semantic essence of the text.

### Geometric interpretation

In the vector space:
- **Distance** between vectors = dissimilarity
- **Angle** between vectors = semantic difference
- Vectors pointing in the same direction are semantically similar

```
       "password reset" ──────●
                              \
                               \  "change password"
                                ●
       "technical docs"     ●    \
                                 \
                                   ● "contact support"
```

## Text embeddings in this project

This POC uses `sentence-transformers/all-MiniLM-L6-v2`, which is a **sentence-level** embedding model. It takes a text input and produces a 384-dimensional vector.

### Where it's used

```python
# app/services/embedding.py
from sentence_transformers import SentenceTransformer

class EmbeddingService:
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> list[float]:
        vector = self.model.encode(text, convert_to_numpy=True)
        return vector.tolist()
```

The `model_name` comes from `app/config.py`:

```python
class Settings(BaseSettings):
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
```

### Practical usage

When you call `POST /api/v1/embed?text=hello+world`:

1. `EmbeddingService.embed("hello world")` calls `model.encode("hello world")`
2. The model tokenizes, processes through 6 transformer layers, and pools the output
3. Returns a 384-element list of floats

## Image embeddings

Image embedding models convert images into vectors. For example, **CLIP** (Contrastive Language-Image Pretraining) maps both images and text into a shared vector space, enabling cross-modal search:

```
Image: "a dog playing in the snow" → vector_img
Text:  "a dog playing in the snow" → vector_text
Cosine similarity: ~1.0 (they match!)
```

This is why you can search for images using text queries, or find text that matches an image.

## Multimodal embeddings

A **multimodal embedding model** processes multiple types of data (text, images, audio) and produces embeddings in a **shared vector space**. This allows:

- **Cross-modal search**: Find images using text, or text using images
- **Unified retrieval**: Search across text and image documents in a single query
- **Multi-modal generation**: Combine text and image understanding

CLIP is a famous example: it embeds both images and text into the same 512-dimensional space, so a photo of a "golden retriever" and the text "golden retriever" will have nearly identical embeddings.

## Embedding dimensions

### What they are

The **dimension** of an embedding is the number of elements in the vector. `all-MiniLM-L6-v2` produces 384-dimensional vectors.

### Trade-offs

| Dimension | Pros | Cons |
|-----------|------|------|
| 128–256 | Fast, low memory, cheap storage | Lower quality, less nuance |
| 384 (this project) | Good balance of quality/speed | Moderate quality |
| 768 | Higher quality | 2x storage, slower search |
| 1,536+ | Best quality for complex tasks | Expensive storage and compute |

### Why 384?

The `all-MiniLM-L6-v2` model uses 4-bit quantization and a 6-layer transformer distilled from `BERT-base`, producing 384 dimensions. It's designed for efficiency while maintaining good semantic quality — making it ideal for a learning project.

## Dense embeddings

**Dense embeddings** have most dimensions non-zero. Neural embedding models (like `SentenceTransformer`) produce dense embeddings because the network activates across many learned features for any given input.

```
Dense: [0.012, -0.045, 0.033, -0.019, ...]  (384 non-zero values)
```

### Dense vs. sparse embeddings

| Property | Dense | Sparse |
|----------|-------|--------|
| Values | Most are non-zero | Most are zero |
| Dimensions | 128–4,096 | 1,000–1,000,000+ |
| Storage | Dense array | Sparse dictionary |
| Use case | Neural embeddings | TF-IDF, bag of words |
| Search | ANN (HNSW) | Inverted index |
| This project | ✅ Dense | ❌ |

## Contextual embeddings

**Contextual embeddings** change based on the surrounding text. The embedding of a word depends on other words in the sentence.

```
Word: "bank"
In "I sat by the river bank":     embedding ≈ [0.2, -0.1, ...]  (financial meaning)
In "I went to the bank to withdraw": embedding ≈ [-0.3, 0.5, ...]  (financial institution)
```

Models like BERT and SentenceTransformer produce contextual embeddings. The `SentenceTransformer` model processes the entire sentence and pools token representations into a single vector, capturing context.

### Static embeddings

**Static embeddings** (like Word2Vec) assign a single fixed vector to each word, regardless of context. These are simpler but cannot disambiguate meaning.

| Type | Example | Context-aware? | Use case |
|------|---------|----------------|----------|
| Static | Word2Vec, GloVe | No | Word similarity, lightweight tasks |
| Contextual | BERT, SentenceTransformer | Yes | Semantic search, RAG, complex NLP |

## Limitations of embeddings

1. **Dimensionality curse**: High-dimensional spaces are sparse, making exact search expensive (mitigated by ANN algorithms)
2. **Semantic drift**: Similar embeddings don't always mean the same thing — embeddings encode patterns, not ground truth
3. **Language dependency**: Not all embedding models handle multiple languages equally well
4. **Domain mismatch**: Models trained on general text may underperform on specialized domains (legal, medical)
5. **Irreversibility**: You can't reliably reconstruct the original text from an embedding (they're lossy representations)
6. **Computational cost**: Generating embeddings requires running a neural model, which is slower than keyword matching
7. **Bias**: Embeddings inherit biases from training data (e.g., gender stereotypes in word associations)

## Keyword similarity vs. semantic similarity

### Keyword similarity (BM25)

Matches documents based on exact term overlap:

| Query | Document | Keyword match? |
|-------|----------|----------------|
| "reset password" | "reset password instructions" | ✓ (exact terms) |
| "reset password" | "change your passcode" | ✗ (no matching terms) |
| "reset password" | "how to restart your device" | ✗ |

### Semantic similarity (embeddings)

Matches documents based on meaning:

| Query | Document | Semantic match? |
|-------|----------|----------------|
| "reset password" | "reset password instructions" | ✓ (0.89 similarity) |
| "reset password" | "change your passcode" | ✓ (0.82 similarity) |
| "reset password" | "how to restart your device" | ✗ (0.12 similarity) |

The second row shows the key advantage: even though "reset" and "change" are different words, the semantic similarity captures their related meaning — something keyword search cannot do.