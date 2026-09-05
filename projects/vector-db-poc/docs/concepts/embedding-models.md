# How Embedding Models Work

## Overview

Embedding models are neural networks that convert text (or other data) into dense vectors. This document explains the process step-by-step, connecting the theory to how `SentenceTransformer` works in this project.

## The full pipeline

```
Text
  ↓
Tokenization
  ↓
Tokens
  ↓
Transformer layers
  ↓
Token representations
  ↓
Pooling
  ↓
Embedding vector
```

## 1. Text

The input is any text — a single word, a sentence, or an entire document:

```
What is a vector database?
```

## 2. Tokenization

**Tokenization** is the process of splitting text into smaller units called **tokens**. Tokens can be whole words, subwords, or characters, depending on the tokenizer.

### Subword tokenization

Modern models use **subword tokenization** (e.g., Byte Pair Encoding or WordPiece). This handles unknown words by breaking them into known subwords:

```
Text: "Vector databases are amazing!"
Tokens: ["Vector", " databases", " are", " amazing", "!"]

Text: "VectorDBs"
Tokens: ["Vector", "DB", "s"]  (split into known subwords)
```

### Tokens

A **token** is the fundamental unit of input to a language model. Each token is mapped to an integer ID from the model's vocabulary:

```
"Vector" → 2274
" databases" → 12345
" are" → 372
```

These integer IDs are then converted to **embeddings** (vectors) using the model's embedding lookup table — starting vectors that the model learns to refine during training.

## 3. Transformer model

A **transformer** is a type of neural network architecture introduced in the 2017 paper "Attention Is All You Need." Key features:

- **Self-attention**: Each token can "attend to" every other token, learning relationships between them
- **Parallel processing**: Unlike RNNs, transformers process all tokens simultaneously
- **Positional encoding**: Since there's no recurrence, position information is added explicitly

### Attention

**Attention** allows the model to weigh the importance of different tokens relative to each other. For each token, the model computes attention scores that determine how much to "pay attention" to other tokens when encoding that token.

```
Token: "bank"
Other tokens: "river" (weight: 0.8), "money" (weight: 0.1), "fish" (weight: 0.05)
→ The model knows "bank" is likely the riverbank meaning
```

### Layers

Transformers are composed of multiple layers stacked on top of each other. Each layer refines the token representations. The `all-MiniLM-L6-v2` model has:

- **6 layers** (L6 in the name)
- **12 attention heads**
- **22M parameters**

This is a **distilled** model — smaller and faster than the full BERT model, while retaining most of the semantic quality.

## 4. Token representations

After passing through the transformer layers, each token has a **hidden state** — a vector representation that encodes the token's meaning in the context of the surrounding text.

```
Layer 0 (input):     [token_emb_1, token_emb_2, ...]
Layer 1:             [hidden_1_1,  hidden_1_2,  ...]
Layer 2:             [hidden_2_1,  hidden_2_2,  ...]
...
Layer 6 (output):    [final_1,     final_2,     ...]
```

Each `final_i` is a vector (same dimension as the model's hidden size) that represents token `i` in context.

## 5. Pooling

The transformer produces **one vector per token**, but we want **one vector for the entire text**. **Pooling** reduces the token-level representations into a single sentence-level embedding.

### Common pooling strategies

| Strategy | How it works | Used by |
|----------|-------------|---------|
| **CLS** | Take the hidden state of the `[CLS]` token | BERT classification |
| **Mean** | Average all token hidden states | Sentence-BERT |
| **Max** | Take the maximum value across each dimension | Some classification tasks |

### Sentence-BERT pooling

The `all-MiniLM-L6-v2` model (used in this project) uses **mean pooling** with a **layer normalization** step:

1. Take the hidden states from the last transformer layer
2. **Mean pool**: Average the hidden states across all tokens (weighted by the attention mask)
3. **Normalize**: Apply L2 normalization to produce a unit vector

```
Token states: [t₁, t₂, t₃, ...]  (each is 384-dim)
Mean pooling: (t₁ + t₂ + t₃ + ...) / N
L2 normalization: v / ||v||
→ Final embedding: 384-dim unit vector
```

## How SentenceTransformer works in this project

### 1. Loading the model

When you first call `EmbeddingService.load()` (in `app/services/embedding.py`):

```python
def load(self) -> None:
    if self.model is None:
        self.model = SentenceTransformer(self.model_name)
```

`SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")`:
1. Downloads the model from HuggingFace Hub (first time only)
2. Loads the model weights into memory
3. Configures the tokenizer, transformer, and pooling layers

### 2. Generating an embedding

```python
def embed(self, text: str) -> list[float]:
    self.load()
    vector = self.model.encode(text, convert_to_numpy=True)
    return vector.tolist()
```

`self.model.encode(text, convert_to_numpy=True)`:
1. Tokenizes the input text (adds `[CLS]` and `[SEP]` tokens)
2. Passes tokens through the 6 transformer layers
3. Mean-pools the token representations
4. Applies L2 normalization
5. Returns a 384-dimensional NumPy array

`.tolist()` converts the NumPy array to a Python list of floats for JSON serialization and Qdrant compatibility.

### 3. Getting the dimension

```python
@property
def dimension(self) -> int:
    self.load()
    return self.model.get_sentence_embedding_dimension()
```

`get_sentence_embedding_dimension()` returns the model's configured embedding size (384 for `all-MiniLM-L6-v2`).

### 4. Batch embedding

```python
def embed_batch(self, texts: list[str]) -> list[list[float]]:
    self.load()
    vectors = self.model.encode(
        texts, convert_to_numpy=True, show_progress_bar=False
    )
    return vectors.tolist()
```

Batch processing is more efficient because:
- Tokenization is vectorized across all texts
- The transformer processes all sequences in a single matrix operation
- GPU/CPU utilization is higher (less per-call overhead)

## Model internals: all-MiniLM-L6-v2

### Architecture

| Component | Detail |
|-----------|--------|
| Base model | `distilbert-base-uncased` (distilled from BERT) |
| Layers | 6 transformer layers (vs. 12 in full BERT) |
| Attention heads | 12 |
| Hidden size | 384 |
| Vocabulary size | 30,522 |
| Parameters | ~22M (vs. ~110M in full BERT) |
| Pooling | Mean pooling + L2 normalization |
| Max sequence length | 256 tokens |

### Training

The model was trained using **contrastive learning** (specifically, the MultipleNegativesRankingLoss):

1. Given a sentence and its embedding, find positive examples (same meaning) and negative examples (different meaning)
2. Train so that positive examples have high similarity (close to 1.0) and negative examples have low similarity (close to 0.0)
3. This encourages semantically similar sentences to cluster together in the vector space

### Why "MiniLM"?

**MiniLM** (Minimum Layer) is a technique that distills a large teacher model into a smaller student model with fewer layers. The student learns to approximate the teacher's representations with much lower computational cost.

## Limitations of embeddings

1. **Fixed context**: Models like `all-MiniLM-L6-v2` have a maximum sequence length (256 tokens). Longer texts are truncated, potentially losing information.
2. **Semantic drift**: Embeddings capture patterns from training data, not ground truth. Unusual phrasings may produce unexpected vectors.
3. **Language**: This model is English-focused. Multilingual models (like `paraphrase-multilingual-MiniLM-L12-v2`) handle multiple languages.
4. **Static representation**: The same input always produces the same vector. There's no way to update an embedding without re-embedding.
5. **Dimensionality**: 384 dimensions capture general semantic relationships but may miss domain-specific nuances.
6. **No metadata awareness**: The embedding only represents the text content, not external context (date, author, etc.) — this is stored separately as payload in Qdrant.
7. **Black box**: The specific meaning of each dimension is learned and not human-interpretable.