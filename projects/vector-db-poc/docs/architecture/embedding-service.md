# Embedding Service — Learning Guide

## 1. What problem does it solve?

To convert human-readable text into a **mathematical vector** that a computer can process. Machine learning models and vector databases don't understand words — they understand numbers. The embedding service bridges this gap by transforming text into dense numerical vectors (embeddings).

## 2. Why is it required?

Vector databases like Qdrant store and search **vectors**, not text. To perform semantic search (finding documents by meaning, not keywords), we must first convert both:
- The **stored documents** into vectors
- The **user's search query** into a vector

Only then can we compare vectors for similarity. The embedding service provides this conversion.

## 3. What concept does it demonstrate?

- **Dense vector embeddings** — text represented as a fixed-length array of floats
- **Pre-trained transformer models** — using models that have already learned language representations
- **Lazy initialization** — loading a heavy model only when first needed
- **Batch processing** — efficiently generating embeddings for multiple texts at once

## 4. How does it work internally?

### Theory

The `SentenceTransformer` model internally:

1. **Tokenizes** input text into tokens (subword units)
2. **Passes tokens** through transformer layers (attention-based neural network)
3. **Pools** the output token representations into a single fixed-size vector

```
Text → Tokenizer → Tokens → Transformer → Token States → Pooling → Embedding Vector
```

The `all-MiniLM-L6-v2` model produces **384-dimensional** vectors using a 6-layer transformer with ~22M parameters. It's compact and fast, making it ideal for learning.

### Implementation in this project

The `EmbeddingService` class (`app/services/embedding.py`) is a thin wrapper:

```python
class EmbeddingService:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model: SentenceTransformer | None = None

    def load(self) -> None:
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)

    def embed(self, text: str) -> list[float]:
        self.load()
        vector = self.model.encode(text, convert_to_numpy=True)
        return vector.tolist()
```

Key design decisions:

- **Lazy loading**: `self.model` starts as `None`. The model is only downloaded and loaded on the first call to `embed()`, `embed_batch()`, or `dimension`. This means the API starts quickly and doesn't download a 90MB model until it's actually needed.
- **`convert_to_numpy=True`**: Returns a NumPy array instead of a PyTorch tensor, avoiding GPU/CUDA dependencies.
- **`.tolist()`**: Converts the NumPy array to a Python `list[float]`, which is JSON-serializable for API responses and accepted by Qdrant's client.

## 5. Important classes and methods

### `EmbeddingService`

| Method | Purpose | Code reference |
|--------|---------|----------------|
| `__init__(model_name)` | Store model name, defer loading | `embedding.py:7-9` |
| `load()` | Lazy-load the SentenceTransformer model | `embedding.py:11-13` |
| `embed(text)` | Generate a single embedding | `embedding.py:15-19` |
| `embed_batch(texts)` | Generate embeddings for multiple texts | `embedding.py:21-25` |
| `dimension` (property) | Return the model's embedding dimension | `embedding.py:27-31` |

### How it's wired in the API

In `app/api/routes.py`, the `EmbeddingService` is lazily instantiated as a singleton:

```python
_embedding_service: EmbeddingService | None = None

def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(settings.embedding_model)
    return _embedding_service
```

Endpoints use FastAPI's `Depends()` to get the service:

```python
@router.post("/embed", response_model=EmbeddingResponse)
def embed(
    text: str,
    emb: EmbeddingService = Depends(get_embedding_service),
):
    vector = emb.embed(text)
    return EmbeddingResponse(vector=vector, dimension=len(vector))
```

## 6. Alternatives

| Approach | Pros | Cons |
|----------|------|------|
| **Sentence Transformers (this project)** | Offline, no API costs, many pre-trained models | Model download on first use, Python-only |
| **OpenAI Embeddings API** | High quality, managed, no local setup | API cost, network dependency, vendor lock-in |
| **Cohere Embeddings API** | Good quality, managed | API cost |
| **HuggingFace Transformers (manual)** | Full control over pooling/tokenization | More code, more complexity |
| **Ollama / LLM embeddings** | Uses LLM hidden states | Slow, expensive, overkill for POC |

## 7. Trade-offs

- **Latency vs. quality**: `all-MiniLM-L6-v2` is fast but not the highest quality. Larger models like `all-mpnet-base-v2` (768 dims) produce better embeddings but are slower and larger.
- **Local vs. API**: Local models have no per-call cost but require disk/RAM. API models charge per token but scale effortlessly.
- **Dimensionality**: 384 dimensions is compact for storage and search, but higher dimensions (768+) can capture more nuanced meaning.
- **Lazy loading**: Defers the model download cost to the first request, which can cause a cold-start delay. For production, pre-loading at startup is preferred.