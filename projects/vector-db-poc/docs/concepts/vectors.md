# Vectors

## What is a vector?

A **vector** is an ordered array of numbers. In machine learning and data science, vectors are the fundamental data structure for representing data in a numerical form that computers can process and compare.

Formally, a vector **v** of dimension *n* is:

```
v = [v₁, v₂, v₃, ..., vₙ]
```

For example, a 4-dimensional vector might look like:

```
[0.12, -0.45, 0.03, 0.78]
```

## Scalar vs vector

| Type | Description | Example |
|------|-------------|---------|
| **Scalar** | A single number | `42`, `3.14`, `-0.5` |
| **Vector** | An ordered array of numbers | `[0.12, -0.45, 0.03, 0.78]` |
| **Matrix** | A 2D array of numbers | `[[0.12, 0.45], [0.03, 0.78]]` |

## Vector dimensions

The **dimension** of a vector is the number of elements it contains. Each element corresponds to a dimension in a vector space.

- A **2D vector** exists in a 2D plane: `[x, y]`
- A **3D vector** exists in 3D space: `[x, y, z]`
- An **embedding vector** in this project has **384 dimensions**: `[v₁, v₂, ..., v₃₈₄]`

In the context of this project, the dimension is defined in `app/config.py`:

```python
class Settings(BaseSettings):
    embedding_dim: int = 384  # matches all-MiniLM-L6-v2 output
```

And used in collection creation in `app/services/vector_db.py`:

```python
qmodels.VectorParams(
    size=self.embedding_dim,  # 384
    distance=qmodels.Distance.COSINE,
)
```

**Key principle:** All vectors in the same collection must have the same dimension. You cannot store a 384-dimensional vector alongside a 768-dimensional one in the same Qdrant collection.

## Vector magnitude

The **magnitude** (or length, or norm) of a vector is calculated using the Euclidean (L2) norm:

```
||v|| = √(v₁² + v₂² + ... + vₙ²)
```

For example, the magnitude of `[3, 4]` is `√(9 + 16) = √25 = 5`.

In embedding space, magnitude represents the "strength" or "confidence" of the representation. However, for semantic search, **direction** (which dimensions are activated) is typically more important than magnitude.

## Vector normalization

**Normalization** scales a vector to have a magnitude (length) of 1, making it a **unit vector**.

```
v_normalized = v / ||v||
```

After normalization, `||v_normalized|| = 1`.

### Why normalization matters

In this project, the embedding model (`all-MiniLM-L6-v2`) does not automatically normalize vectors. However, Qdrant's **cosine similarity** metric measures only the angle between vectors, effectively ignoring magnitude:

```
cos(u, v) = (u · v) / (||u|| × ||v||)
```

This means:
- If vectors are normalized (||v|| = 1), cosine similarity equals dot product: `cos(u, v) = u · v`
- If vectors are not normalized, cosine similarity adjusts for magnitude differences

In the embedding service (`app/services/embedding.py`), the raw vectors from `model.encode()` are used directly — no normalization is applied:

```python
def embed(self, text: str) -> list[float]:
    self.load()
    vector = self.model.encode(text, convert_to_numpy=True)
    return vector.tolist()  # raw, not normalized
```

This works correctly because Qdrant handles the normalization internally when computing cosine similarity.

## Unit vectors

A **unit vector** is a vector with magnitude 1. It's obtained by dividing a vector by its magnitude:

```
û = u / ||u||
```

Unit vectors are useful because:
- They isolate **direction** from **magnitude**
- Cosine similarity between unit vectors simplifies to dot product
- They occupy a consistent range, making comparisons more meaningful

## High-dimensional vectors

Vectors in machine learning often have hundreds or thousands of dimensions. This is because high-dimensional spaces can capture nuanced relationships between data points.

For example:
- `all-MiniLM-L6-v2`: 384 dimensions
- `all-mpnet-base-v2`: 768 dimensions
- OpenAI `text-embedding-3-large`: 3,072 dimensions

### The curse of dimensionality

As dimensionality increases, the volume of the space grows exponentially, and data points become increasingly sparse. This makes exact nearest-neighbor search computationally expensive — a problem solved by **approximate nearest neighbor (ANN)** algorithms used in Qdrant and other vector databases.

## Sparse vectors

A **sparse vector** is one where most elements are zero. Sparse vectors are typically very high-dimensional (e.g., 30,000 dimensions for a vocabulary) but only a few dimensions are non-zero.

**Example — bag of words:**
```
Vocabulary: ["cat", "dog", "bird", "fish"]
Text: "The cat and the dog"
Sparse vector: [1, 1, 0, 0]  (cat=1, dog=1, bird=0, fish=0)
```

In this project, the `SentenceTransformer` model produces **dense** vectors (all dimensions typically non-zero), not sparse vectors.

## Dense vectors

A **dense vector** has most elements non-zero. Embedding models produce dense vectors because every dimension encodes some learned feature.

```
Dense vector (384 dims): [0.012, -0.045, 0.033, -0.019, ...]
All values are meaningful and non-zero.
```

### Dense vs. sparse: a comparison

| Property | Dense | Sparse |
|----------|-------|--------|
| Element values | Most are non-zero | Most are zero |
| Typical dimensions | 128–4,096 | 1,000–1,000,000+ |
| Storage | Array of N floats | Dictionary of (index, value) pairs |
| Use case | Neural embeddings | Bag of words, TF-IDF |
| Search method | ANN (HNSW, IVF) | Inverted index |
| This POC uses | ✅ Dense (SentenceTransformer) | ❌ Not used |

## Connection to this project

In this project, the vector representation flows through these components:

```
Text → SentenceTransformer.encode() → NumPy array → .tolist() → list[float]
                                                                  ↓
                                                           Qdrant PointStruct.vector
                                                                  ↓
                                                     COSINE distance search
                                                                  ↓
                                                          Similarity score
```

The vector dimension (384) is:
1. Defined in `app/config.py` as `embedding_dim: int = 384`
2. Verified at runtime via `EmbeddingService.dimension` property
3. Used to create the Qdrant collection with `VectorParams(size=384)`

Any mismatch between the embedding model's output dimension and the collection's configured dimension will cause Qdrant to reject points during insertion.