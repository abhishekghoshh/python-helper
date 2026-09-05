# Interview Q&A: Embedding Models

## Model Fundamentals

### Q1: How do you select an embedding model?

**A:** Consider these factors:

| Factor | Impact |
|--------|--------|
| **Domain** | Some models are trained on general text, others on specific domains (legal, medical, code) |
| **Language** | Multilingual models handle many languages; monolingual may be better for a single language |
| **Dimensions** | Lower = faster/cheaper; higher = potentially better quality |
| **Accuracy** | Measured on benchmarks like MTEB (Massive Text Embedding Benchmark) |
| **Latency** | Smaller models (768M params) are faster than large ones (1.3B+) |
| **Cost** | Local models have no per-call cost; API models charge per 1K tokens |
| **Model size** | Disk/RAM constraints for local deployment |
| **Context length** | Some models support 512 tokens, others 8K+ |

### Q2: What is MTEB?

**A:** **Massive Text Embedding Benchmark** — a standardized evaluation suite with 84 datasets across 49 languages, measuring embedding quality across tasks like:
- Semantic textual similarity (STS)
- Classification (sentiment, intent)
- Clustering
- Retrieval (BEIR benchmark)
- Pair classification

Models are ranked by average score across all tasks. Higher MTEB score = better overall embedding quality.

### Q3: What embedding dimensions should I use?

**A:** Trade-offs:

| Dimension | Use case | Pros | Cons |
|-----------|----------|------|------|
| 128–256 | Mobile, edge | Very fast, low storage | Lowest quality |
| 384 | General purpose | Good speed/quality balance | Moderate quality |
| 768 | Production | High quality | 2x storage, slower search |
| 1,024+ | High accuracy | Best quality | Expensive |

In this project, `all-MiniLM-L6-v2` produces 384 dimensions — a good balance for learning and prototyping.

### Q4: What is the difference between text-embedding-ada-002 and all-MiniLM-L6-v2?

**A:**

| Feature | ada-002 | MiniLM-L6-v2 |
|---------|---------|--------------|
| Provider | OpenAI | Sentence Transformers |
| Dimensions | 1,536 | 384 |
| Parameters | Unknown (proprietary) | ~22M |
| Context | 8,192 tokens | 256 tokens |
| Cost | $0.0004 / 1K tokens | Free (local) |
| MTEB score | ~61% | ~62% |
| Deployment | API only | Self-hosted |

For learning/prototyping: MiniLM (free, no API key needed).
For production: ada-002 if cost isn't an issue; MiniLM or `bge-small-en` for cost-sensitive apps.

### Q5: What is multilingual support in embeddings?

**A:** Multilingual models are trained on text in multiple languages, producing embeddings in a **shared vector space** — semantically similar texts in different languages have similar embeddings.

Examples:
- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` — 50+ languages, 384 dims
- `intfloat/multilingual-e5-large` — 100+ languages, 1024 dims

**Trade-off:** Multilingual models are often larger and slightly lower quality for any single language compared to monolingual models.

### Q6: What is an embedding model's context length?

**A:** The maximum number of tokens the model can process at once. Beyond this, text is truncated.

| Model | Context length |
|-------|----------------|
| all-MiniLM-L6-v2 | 256 tokens |
| all-mpnet-base-v2 | 512 tokens |
| text-embedding-ada-002 | 8,192 tokens |
| text-embedding-3-small/large | 8,192 tokens |

In this project, the 256-token limit means documents longer than ~200 words are **truncated** during embedding — this is why document chunking is important for long texts.

## Tokenization and Model Architecture

### Q7: What is tokenization?

**A:** Tokenization is the process of splitting text into smaller units called **tokens**. Modern models use **subword tokenization** (BPE or WordPiece):

```
Text: "I love machine learning!"
Tokens: ["I", " love", " machine", " learning", "!"]
IDs: [1045, 2342, 3800, 4231, 934]
```

Subword tokenization handles unknown words by breaking them into known subwords:

```
Text: "Uncharacteristically"
Tokens: ["Un", "##char", "##acter", "##istically"]
```

The `SentenceTransformer.encode()` method handles tokenization internally — you pass raw text and get back a vector.

### Q8: What is a transformer?

**A:** A **transformer** is a neural network architecture (introduced in the 2017 paper "Attention is All You Need") that uses **self-attention** to process all tokens in parallel:

1. **Self-attention**: Each token computes attention weights over all other tokens, learning relationships
2. **Multi-head**: Multiple attention patterns in parallel
3. **Feed-forward**: Each token is processed through a small MLP
4. **Layers**: Multiple transformer layers stacked (6 in MiniLM, 12 in BERT-base)

The key advantage: unlike RNNs (which process sequentially), transformers process all tokens simultaneously, enabling much faster training and inference.

### Q9: What is attention?

**A:** **Self-attention** allows each token to "attend to" (pay attention to) every other token in the sequence. For each token, the model computes:
1. **Query** (what I'm looking for)
2. **Key** (what I contain)
3. **Value** (what I contribute)

The attention score is: `softmax(query · key) × value`

This lets the model capture relationships like "the word 'it' refers to 'password' mentioned earlier."

In `all-MiniLM-L6-v2`:
- 12 attention heads
- Each head learns different types of relationships
- 6 transformer layers

### Q10: What is pooling?

**A:** After the transformer produces token-level embeddings, **pooling** combines them into a single sentence-level embedding:

| Strategy | How it works | Used by |
|----------|-------------|---------|
| **CLS** | Take the [CLS] token's hidden state | BERT classification |
| **Mean** | Average all token hidden states | Sentence-BERT |
| **Max** | Take max value per dimension | Some classification tasks |

`all-MiniLM-L6-v2` uses **mean pooling** with L2 normalization:

```python
# Internal to SentenceTransformer (not in this project's code)
# 1. Get token states from last transformer layer
# 2. Mean pool: average across tokens (weighted by attention mask)
# 3. L2 normalize: v / ||v||
```

This produces a fixed 384-dim vector regardless of input text length (up to 256 tokens).

## Model Comparisons

### Q11: Sentence Transformers vs. OpenAI Embeddings — which to choose?

**A:**

| Factor | Sentence Transformers | OpenAI Embeddings |
|--------|----------------------|-------------------|
| **Cost** | Free (local) | $0.0004 / 1K tokens |
| **Privacy** | Private (no data leaves) | Data sent to OpenAI |
| **Setup** | Download model (~90MB) | API key required |
| **Latency** | Model loads once, then fast | Network round-trip per call |
| **Quality** | Comparable (MTEB ~62%) | Good (MTEB ~61%) |
| **Control** | Full control over model, pooling | No control over internals |
| **Scalability** | Limited by local hardware | Scales to any volume |

**Recommendation:**
- **Learning/Prototyping**: Sentence Transformers (no API costs, full control)
- **Production at scale**: OpenAI (if budget allows; simpler deployment)
- **Production cost-sensitive**: `bge-small-en` or `all-MiniLM-L6-v2` locally

### Q12: What are contextual embeddings vs. static embeddings?

**A:**

```
"bank" in "I sat by the river bank"
  Static (Word2Vec): always the same vector for "bank"
  Contextual (BERT/SentenceTransformer): different vector for "bank" depending on context

"bank" in "I went to the bank to withdraw money"
  Static (Word2Vec): same vector for "bank" (ignores context)
  Contextual (BERT): different vector (financial meaning)
```

- **Static**: Word2Vec, GloVe — one vector per word, learned from co-occurrence
- **Contextual**: BERT, RoBERTa, MiniLM — token representations depend on surrounding context

SentenceTransformer produces **contextual sentence embeddings** — the embedding of a sentence depends on all its words and their relationships.

### Q13: What is distillation in embedding models?

**A:** **Distillation** trains a smaller "student" model to mimic a larger "teacher" model:

```
Teacher: BERT-base (12 layers, 110M params) → high-quality embeddings
                                    ↓
Student: MiniLM (6 layers, 22M params) → learns to produce similar embeddings
```

Benefits:
- **6x smaller** (22M vs 110M params)
- **2x faster** inference
- **4x less memory**
- Minimal quality loss (MiniLM achieves ~95% of BERT's MTEB score)

`all-MiniLM-L6-v2` is a distilled model — that's why it's fast enough for real-time use while maintaining good quality.

### Q14: What is the difference between embedding andreranking?

**A:** Not commonly asked, but interesting:

- **Embedding**: Convert text to a vector (one-way: text → vector)
- **Reranking**: Given a query and a set of candidate documents (already retrieved), use a cross-encoder model to produce a refined relevance score

Reranking is typically done as a second stage after initial vector retrieval:
1. Retrieve top-100 with vector search (fast)
2. Rerank top-100 with a cross-encoder (slower but more accurate)
3. Return top-10

This project does not implement reranking.

## Cost and Performance

### Q15: How do you estimate the cost of running embeddings?

**A:** Two models:

#### Local (Sentence Transformers)
```
Cost = GPU/CPU hardware cost only
- CPU: ~$0 (existing server)
- GPU: $0.50–$2/hour (cloud GPU)
- Memory: ~500MB RAM for all-MiniLM-L6-v2
- Throughput: 50–200 docs/sec on CPU, 500+/sec on GPU
```

#### API (OpenAI)
```
Cost = $0.0004 per 1K tokens
- 500-character document ≈ 125 tokens ≈ $0.00005 per embed
- 1M documents ≈ $50 to embed
- Ongoing: $0.0004 per 1K tokens for each search query
```

For this POC: local model (Sentence Transformers) — zero ongoing cost.

### Q16: How do you choose between embedding models for different tasks?

**A:**

| Task | Recommended model | Reason |
|------|-------------------|--------|
| Semantic search (general) | `all-MiniLM-L6-v2` (384d) or `bge-small-en` (384d) | Good quality, fast, small |
| High-accuracy search | `all-mpnet-base-v2` (768d) | Higher MTEB score |
| Multilingual | `paraphrase-multilingual-MiniLM-L12-v2` (384d) | 50+ languages |
| Code search | `thenlper/gte-code-base` | Trained on code |
| Long documents | `salesforce/sfr-embedding-mistral` (4096d) | 32K context length |
| Low latency | `all-MiniLM-L6-v2` | Smallest, fastest |
| OpenAI ecosystem | `text-embedding-3-small` | Optimized for OpenAI stack |

### Q17: What is the relationship between tokens and embedding dimensions?

**A:** These are **independent** properties:

- **Tokens**: How many words/subwords the model can process (context length, e.g., 256 for MiniLM)
- **Dimensions**: How many numbers the output vector has (e.g., 384 for MiniLM)

A model can have many dimensions but a short context:
- `all-MiniLM-L6-v2`: 256 max tokens, 384 dimensions

Or many dimensions and a long context:
- `text-embedding-3-large`: 8,192 tokens, 3,072 dimensions

Both properties affect the model's capabilities and resource usage independently.

### Q18: What are the limitations of embeddings?

**A:**

1. **Context window limit**: Text longer than the model's max tokens is truncated (256 tokens for MiniLM in this project)
2. **Semantic drift**: Embeddings capture training data patterns, not ground truth
3. **Language bias**: Models may perform unevenly across languages
4. **Domain mismatch**: Models trained on general text underperform on specialized domains
5. **No memory**: Embeddings don't update with new information — need to re-embed
6. **Black box**: Individual dimensions are not human-interpretable
7. **Bias**: Models inherit biases from training data
8. **Cost at scale**: Embedding millions of documents is computationally expensive