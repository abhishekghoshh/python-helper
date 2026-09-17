# Chunking Strategies

## What is Chunking?

**Chunking** is the process of splitting a document into smaller, manageable
pieces. Each chunk becomes a single vector in the vector database.

```mermaid
flowchart LR
    DOC["Document<br/>(10,000 characters)"] --> SPLIT["Character-based Splitter<br/>chunk_size=500, overlap=100"]
    SPLIT --> CH1["Chunk 1<br/>chars 0-500"]
    SPLIT --> CH2["Chunk 2<br/>chars 400-900"]
    SPLIT --> CH3["Chunk 3<br/>chars 800-1300"]
    SPLIT --> CH4["Chunk 4<br/>chars 1200-1700"]
    SPLIT --> CH5["Chunk 5<br/>chars 1600-2000"]
    SPLIT --> CHN["... (20 chunks total)"]
    CH1 --> EMB1["Embedding 1<br/>(384-dim vector)"]
    CH2 --> EMB2["Embedding 2"]
    CH3 --> EMB3["Embedding 3"]
    CH4 --> EMB4["Embedding 4"]
    CH5 --> EMB5["Embedding 5"]
    CHN --> EMBN["... (20 embeddings)"]

    style DOC fill:#3498db,color:#fff
    style SPLIT fill:#f39c12,color:#fff
    style CH1 fill:#e74c3c,color:#fff
    style CH2 fill:#e74c3c,color:#fff
    style CH3 fill:#e74c3c,color:#fff
    style CH4 fill:#e74c3c,color:#fff
    style CH5 fill:#e74c3c,color:#fff
    style EMB1 fill:#9b59b6,color:#fff
    style EMB2 fill:#9b59b6,color:#fff
    style EMB3 fill:#9b59b6,color:#fff
    style EMB4 fill:#9b59b6,color:#fff
    style EMB5 fill:#9b59b6,color:#fff
```

## Why Chunk?

### Context Window Limits

LLMs have finite context windows (e.g., 8K-128K tokens). You can't pass an
entire book to an LLM. Chunking breaks content into digestible pieces.

### Embedding Input Limits

Embedding models also have token limits (e.g., 512 or 8192 tokens). Long texts
must be split before embedding.

### Retrieval Precision

Smaller chunks mean more targeted retrieval — the LLM sees only the relevant
portion, not the entire document.

## Chunking Parameters

### Chunk Size

The maximum size of each chunk (in characters or tokens):

| Size | Characteristics |
|------|-----------------|
| **100-200** | Very focused, may miss context |
| **500** | Balanced (POC default) |
| **1000-2000** | More context, less precise |

### Chunk Overlap

The number of characters/tokens that overlap between adjacent chunks:

```mermaid
flowchart LR
    CH1["Chunk 1<br/>chars 0–500"] --> OVL[["Overlap<br/>chars 400–500<br/>(100 chars)"]]
    OVL --> CH2["Chunk 2<br/>chars 400–900"]
    CH2 --> OVL2[["Overlap<br/>chars 800–900<br/>(100 chars)"]]
    OVL2 --> CH3["Chunk 3<br/>chars 800–1300"]
    CH3 --> OVL3[["Overlap<br/>chars 1200–1300<br/>(100 chars)"]]
    OVL3 --> CH4["Chunk 4<br/>chars 1200–1700"]

    style CH1 fill:#3498db,color:#fff
    style CH2 fill:#3498db,color:#fff
    style CH3 fill:#3498db,color:#fff
    style CH4 fill:#3498db,color:#fff
    style OVL fill:#e74c3c,color:#fff
    style OVL2 fill:#e74c3c,color:#fff
    style OVL3 fill:#e74c3c,color:#fff
```

Overlap ensures that information spanning chunk boundaries is not lost.
When a concept falls at the boundary between two chunks, the overlap
guarantees that at least one chunk contains the complete context.

| Overlap | Characteristics |
|---------|-----------------|
| **0** | No context sharing (risky) |
| **50-100** | Light overlap (POC default: 100) |
| **200+** | Heavy overlap (redundant storage) |

## Chunking Strategies

### 1. Fixed-Size Splitting

Split text at fixed intervals, ignoring sentence boundaries:

```python
def fixed_size_chunk(text, chunk_size=500, overlap=100):
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start + chunk_size])
        start += chunk_size - overlap
    return chunks
```

**Pros:** Simple, predictable
**Cons:** May cut sentences mid-way

### 2. Sentence-Based Splitting

Split at sentence boundaries:

```python
import re

def sentence_chunk(text, max_chars=500):
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks = []
    current = []
    current_len = 0

    for sentence in sentences:
        if current_len + len(sentence) > max_chars and current:
            chunks.append(" ".join(current))
            current = [sentence]
            current_len = len(sentence)
        else:
            current.append(sentence)
            current_len += len(sentence)

    if current:
        chunks.append(" ".join(current))
    return chunks
```

**Pros:** Preserves sentence boundaries
**Cons:** Variable chunk sizes

### 3. Recursive/RecursiveCharacter Splitting

Try multiple separators in order (used by LangChain):

```python
# Try to split by:
# 1. Paragraph breaks (\n\n)
# 2. Line breaks (\n)
# 3. Sentences (.!?)
# 4. Words (" ")
# 5. Characters
```

This produces the most natural chunks.

### 4. Token-Based Splitting

Split by token count rather than characters:

```python
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

def token_chunk(text, max_tokens=128):
    tokens = tokenizer.tokenize(text)
    chunks = []
    for i in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[i:i + max_tokens]
        chunks.append(tokenizer.convert_tokens_to_string(chunk_tokens))
    return chunks
```

**Pros:** Respects model token limits
**Cons:** Tokenizer overhead

## In Our POC

We use a simple character-based splitter:

```python
# app/rag/ingestion.py
def chunk_text(
    text: str,
    chunk_size: int = 500,    # ~125 words, ~75 tokens
    chunk_overlap: int = 100,  # 20% overlap
) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - chunk_overlap
    return chunks
```

### Configuration

```bash
# .env
RAG_CHUNK_SIZE=500
RAG_CHUNK_OVERLAP=100
```

### Why Character-Based for the POC?

1. **No extra dependencies** — uses pure Python
2. **Easy to understand** — the algorithm is visible and simple
3. **Works with any text** — no tokenizer coupling
4. **Sufficient for learning** — the concepts are the same

## Visualizing Chunks

```mermaid
flowchart LR
    D[Document: 2000 chars] --> C1[Chunk 1: chars 0-500]
    D --> C2[Chunk 2: chars 400-900]
    D --> C3[Chunk 3: chars 800-1300]
    D --> C4[Chunk 4: chars 1200-1700]
    D --> C5[Chunk 5: chars 1600-2000]

    C1 -->|overlap| C2
    C2 -->|overlap| C3
    C3 -->|overlap| C4
    C4 -->|overlap| C5

    style D fill:#3498db,color:#fff
    style C1 fill:#e74c3c,color:#fff
    style C2 fill:#e74c3c,color:#fff
    style C3 fill:#e74c3c,color:#fff
    style C4 fill:#e74c3c,color:#fff
    style C5 fill:#e74c3c,color:#fff
```

## Chunk Size Trade-offs

| Chunk Size | Pro | Con |
|-----------|-----|-----|
| **Small (100-200)** | Precise retrieval, more chunks | May lose context, higher storage cost |
| **Medium (500-1000)** | Good balance | May miss broader context |
| **Large (2000+)** | Full context preserved | Less precise retrieval, may exceed context window |

## Next Steps

- [Retrieval](retrieval.md) — How chunks are searched
- [Context Construction](context-construction.md) — How chunks are assembled
