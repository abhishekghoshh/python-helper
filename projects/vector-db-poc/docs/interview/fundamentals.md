# Interview Q&A: Fundamentals

## Vectors and Embeddings

### Q1: What is a vector?

**A:** A vector is an ordered array of numbers that represents data in a high-dimensional space. In machine learning, vectors encode semantic or structural information about data (text, images, etc.) in a numerical format that computers can process and compare.

Each number in the array is a dimension. For example, a 384-dimensional vector (used by `all-MiniLM-L6-v2` in this project) looks like:

```
[0.012, -0.045, 0.033, -0.019, ..., 0.022]
```

Vectors have **magnitude** (length) and **direction** (the pattern of which dimensions are activated).

### Q2: What is an embedding?

**A:** An embedding is the process of converting raw data (text, image, audio) into a vector representation. The resulting embedding vector captures the semantic meaning of the input in a way that similar inputs produce vectors that are close together in the vector space.

For example, "How do I reset my password?" and "How do I change my password?" will have embedding vectors that are close together, even though the words differ — because they carry the same semantic meaning.

### Q3: What is the difference between an embedding and a feature vector?

**A:**

- **Feature vector**: A hand-engineered representation where each dimension has a human-interpretable meaning (e.g., `[age=25, income=50000, is_student=0]`). Created by feature engineering.
- **Embedding**: A learned representation where dimensions are **latent** (human-uninterpretable). The model learns what each dimension should represent during training on large datasets.

Key difference: embeddings are learned automatically from data, while feature vectors are manually constructed by engineers.

### Q4: What is semantic similarity?

**A:** Semantic similarity measures whether two pieces of text have the same **meaning**, regardless of whether they use the same words.

Contrast with **lexical similarity** (keyword matching):

- Lexical: "car" and "automobile" are different (no shared characters)
- Semantic: "car" and "automobile" are very similar (same meaning)

Embeddings capture semantic similarity because they are trained on text where semantically similar inputs produce similar hidden states.

### Q5: Why are embeddings high-dimensional?

**A:** High-dimensional spaces can capture nuanced relationships between data points. More dimensions allow the embedding to encode more features:

- 2D/3D: Can only capture very coarse distinctions (useful for visualization only)
- 128–384 dims: Good for general text similarity (e.g., `all-MiniLM-L6-v2`)
- 768+ dims: Capture more nuanced meaning, better for complex tasks

The dimensionality is a trade-off between:
- **Quality**: More dimensions = more expressive = better quality (up to a point)
- **Storage**: More dimensions = more bytes per vector
- **Search speed**: More dimensions = slower comparison
- **Curse of dimensionality**: At very high dimensions, distance concentration occurs

### Q6: What does embedding dimension mean?

**A:** The embedding dimension is the number of elements in the embedding vector. For `all-MiniLM-L6-v2`, this is 384.

Implications:
- All vectors in the same collection must have the same dimension
- Higher dimensions = more storage and computation
- The dimension is a property of the model — different models produce different dimensions

In this project, the dimension is stored in configuration:

```python
# app/config.py
embedding_dim: int = 384
```

And used in collection creation:

```python
# app/services/vector_db.py
qmodels.VectorParams(size=self.embedding_dim, distance=qmodels.Distance.COSINE)
```

### Q7: What is vector normalization?

**A:** Normalization scales a vector to have a magnitude (length) of 1, making it a **unit vector**.

```
v_normalized = v / ||v||
```

Where `||v||` is the L2 norm (magnitude): `√(v₁² + v₂² + ... + vₙ²)`.

**Why it matters:**
- Makes cosine similarity equivalent to dot product (for normalized vectors)
- Prevents magnitude from dominating similarity comparisons
- Ensures consistent score ranges

The `all-MiniLM-L6-v2` model applies L2 normalization internally, so its embeddings are already unit vectors.

### Q8: Dense vs. sparse vectors?

**A:**

| Type | Description | Example | Use case |
|------|-------------|---------|----------|
| **Dense** | Most elements are non-zero | `[0.012, -0.045, 0.033, ...]` (384 values) | Neural embeddings |
| **Sparse** | Most elements are zero | `{0: 1, 45: 3, 120: 1}` (3 non-zero out of 30,000) | Bag of words, TF-IDF |

- **Dense** vectors use array storage (memory-intensive but fast to compare)
- **Sparse** vectors use dictionary storage {index: value} (memory-efficient but slower similarity computation)
- This project uses **dense** vectors from `SentenceTransformer`

### Q9: Static vs. contextual embeddings?

**A:**

- **Static embeddings** (Word2Vec, GloVe): Each word has a single fixed vector regardless of context. "bank" always has the same embedding, whether in "river bank" or "bank account."
- **Contextual embeddings** (BERT, SentenceTransformer): The embedding of a word changes based on surrounding context. "bank" in "river bank" and "bank account" produce different embeddings.

This project uses **contextual embeddings** — `SentenceTransformer` processes the entire sentence and the embedding reflects word meanings in context.

### Q10: How are embeddings generated?

**A:** The process:

1. **Tokenization**: Split text into tokens (words or subwords)
2. **Transformer processing**: Pass tokens through a transformer neural network with self-attention
3. **Pooling**: Combine token-level representations into a single sentence-level vector
4. **Normalization**: Optionally apply L2 normalization

In this project:

```python
# app/services/embedding.py
from sentence_transformers import SentenceTransformer

class EmbeddingService:
    def embed(self, text: str) -> list[float]:
        self.load()  # Lazy-load the model
        vector = self.model.encode(text, convert_to_numpy=True)
        return vector.tolist()
```

The `model.encode()` method handles tokenization, transformer inference, pooling, and normalization internally.

### Q11: What happens if two texts have the same embedding?

**A:** If two different texts produce identical embeddings, they are **semantically indistinguishable** to the embedding model. This is a limitation called **embedding collapse** — different inputs mapping to the same vector.

This can happen with:
- Very short or empty texts
- Texts that differ only in ways the model doesn't capture
- Adversarial inputs

In practice, this is rare with well-trained models like `all-MiniLM-L6-v2`.

### Q12: Can embeddings be reversed back to text?

**A:** No — embeddings are **lossy** representations. The model learns a one-way mapping from text to vectors. There's no decoder that can reconstruct the original text from the embedding.

This is by design — embeddings capture meaning, not verbatim content.

### Q13: What is the difference between word embeddings and sentence embeddings?

**A:**

- **Word embeddings**: Represent individual words (e.g., Word2Vec: `"king"` → `[0.2, -0.5, ...]`)
- **Sentence embeddings**: Represent entire sentences or documents (e.g., Sentence-BERT: `"How are you?"` → `[0.012, -0.045, ...]`)

Sentence embeddings are produced by:
1. Getting word/token embeddings from the transformer
2. **Pooling** them into a single vector (mean pooling, CLS token, max pooling)

This project produces **sentence embeddings** — the `SentenceTransformer` model processes input text and returns a single 384-dimensional vector regardless of input length (truncated to 256 tokens).

### Q14: What is the curse of dimensionality?

**A:** As the number of dimensions increases, the volume of the space grows exponentially, causing:

1. **Distance concentration**: All vectors become approximately the same distance from each other. The difference between the nearest and farthest neighbor becomes negligible.
2. **Sparsity**: Data points become increasingly isolated in the high-dimensional space.
3. **Computational cost**: Each distance computation requires more operations.

This is why **approximate nearest neighbor (ANN)** algorithms are essential — exact search becomes both slow and less meaningful in high dimensions.

### Q15: What are the trade-offs of using higher-dimensional embeddings?

**A:**

| Dimension | Pros | Cons |
|-----------|------|------|
| Low (128–256) | Fast, low memory, cheap storage | Lower quality, less nuance |
| Medium (384–768) | Good balance of quality/speed | Moderate cost |
| High (1024+) | Best quality, captures nuances | Expensive, slower search, curse of dimensionality |

In this project, 384 dimensions (from `all-MiniLM-L6-v2`) provides a good balance for learning and prototyping.