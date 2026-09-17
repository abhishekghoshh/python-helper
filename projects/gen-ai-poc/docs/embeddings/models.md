# Embedding Models

## What is an Embedding Model?

An **embedding model** is a machine learning model that converts text into
dense vector representations. They are typically **encoder-only transformers**
trained specifically to produce good embeddings.

## How Embedding Models Are Trained

Unlike LLMs (which predict the next token), embedding models are trained with
**contrastive learning**:

```mermaid
flowchart LR
    A[Similar sentence pair] --> M[Model]
    B[Different sentence pair] --> M
    M --> S1[Embedding A]
    M --> S2[Embedding B]
    S1 --> C1[Contrastive Loss]
    S2 --> C1
    C1 --> LOWER[Lower loss: sim(A,B) ↑, sim(A,C) ↓]
    LOWER --> W[Update weights]

    style A fill:#3498db,color:#fff
    style B fill:#e74c3c,color:#fff
    style C1 fill:#f39c12,color:#fff
    style LOWER fill:#27ae60,color:#fff
```

The model is rewarded when:
- **Similar texts** have embeddings close together
- **Different texts** have embeddings far apart

## Popular Embedding Models

### Open-Source Models (sentence-transformers)

| Model | Dimensions | Performance | Speed | Use Case |
|-------|-----------|-------------|-------|----------|
| all-MiniLM-L6-v2 | 384 | Good | Fast | General purpose, POC |
| all-mpnet-base-v2 | 768 | Excellent | Slow | High quality needed |
| all-MiniLM-L12-v2 | 384 | Good | Medium | Balanced |
| multi-qa-MiniLM-L6-cos | 384 | Good | Fast | QA / search |
| parapharse-MiniLM-L3-v2 | 384 | Moderate | Very fast | Lightweight apps |

### OpenAI Models

| Model | Dimensions | Price | Notes |
|-------|-----------|-------|-------|
| text-embedding-3-small | 1536 | $0.00002/1K | Good balance |
| text-embedding-3-large | 3072 | $0.00013/1K | High quality |
| text-embedding-ada-002 | 1536 | $0.0001/1K | Legacy, still good |

### Cohere Models

| Model | Dimensions | Price | Notes |
|-------|-----------|-------|-------|
| embed-english-v3.0 | 1024 | $0.0001/1K | Good performance |
| embed-light-English-v3.0 | 384 | $0.00002/1K | Fast, lightweight |

## Choosing an Embedding Model

### Decision Factors

| Factor | Local (sentence-transformers) | Cloud (OpenAI) |
|--------|-------------------------------|----------------|
| **Cost per call** | Free (after download) | ~$0.00002 |
| **Speed (first call)** | Slow (model load) | Fast |
| **Speed (subsequent)** | Fast (CPU/GPU) | Network-dependent |
| **Privacy** | Data stays local | Data leaves your system |
| **Quality** | Good for most tasks | State-of-the-art |
| **Control** | Full control | Limited |
| **Internet needed** | No | Yes |

### Recommendations

| Task | Recommended Model |
|------|-------------------|
| **Learning POC** | all-MiniLM-L6-v2 (fast, simple) |
| **Production search** | text-embedding-3-small or all-mpnet-base-v2 |
| **Cost-sensitive** | all-MiniLM-L6-v2 (local) |
| **High quality needed** | text-embedding-3-large or all-mpnet-base-v2 |
| **Multilingual** | paraphrase-multilingual-MiniLM-L12-v2 |

## In Our POC

The configuration allows switching between local and cloud embeddings:

```python
# app/core/config.py
class Settings(BaseSettings):
    embedding_provider: str = "sentence-transformers"  # Default: local
    embedding_model: str = "all-MiniLM-L6-v2"          # 384 dimensions
    openai_embedding_model: str = "text-embedding-3-small"  # 1536 dimensions
    embedding_dimensions: int = 384  # Must match the model's output
```

### Using Local Embeddings

```bash
# .env
EMBEDDING_PROVIDER=sentence-transformers
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

### Using OpenAI Embeddings

```bash
# .env
EMBEDDING_PROVIDER=openai
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
```

## Embedding Quality: A Case Study

Let's compare how different models handle semantic similarity:

```python
# Test: "How to bake a cake?" vs "How to make a cake?"
# Expected: High similarity (same intent, different words)
```

| Model | Cosine Similarity | Notes |
|-------|------------------|-------|
| all-MiniLM-L6-v2 | ~0.85 | Good |
| all-mpnet-base-v2 | ~0.91 | Better |
| text-embedding-3-small | ~0.93 | Best |
| TF-IDF (baseline) | ~0.45 | Misses semantic match |

## Dimension Reduction

If you want lower-dimensional embeddings for efficiency:

```python
# OpenAI supports custom dimensions
response = await client.embeddings.create(
    model="text-embedding-3-large",
    input="Hello world",
    dimensions=256,  # Reduce from 3072 to 256
)
```

This is useful when:
- Storage is constrained
- Search speed matters
- You want to experiment with different dimensionalities

## Next Steps

- [Python Examples](python-examples.md) — See embeddings in action
- [Distance Metrics](distance-metrics.md) — How to compare embeddings

## References

- [Sentence Transformers Documentation](https://www.sbert.net/)
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
- [Hugging Face Model Hub](https://huggingface.co/models)
