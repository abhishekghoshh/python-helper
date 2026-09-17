# Learning Guide

This guide walks through the POC step by step, building understanding at each
stage. Follow along to understand how GenAI components work together.

## Prerequisites

Before starting, make sure you understand:
- Python basics (functions, classes, async/await)
- REST APIs (HTTP methods, JSON)
- Basic linear algebra (vectors, dot products)

## Step 0: Start the System

```bash
# Start everything
docker compose up

# Verify
curl http://localhost:8000/health
# → {"status": "healthy"}
```

## Step 1: Understand Embeddings

### What You'll Learn
- How text is converted to vectors
- How similar texts produce similar vectors
- The three similarity metrics

### Try It

```bash
# Generate an embedding
curl -X POST http://localhost:8000/api/v1/embeddings/generate \
  -H "Content-Type: application/json" \
  -d '{"text": "Machine learning is a subset of AI"}'

# Compute similarity
curl -X POST http://localhost:8000/api/v1/embeddings/similarity \
  -H "Content-Type: application/json" \
  -d '{
    "text_a": "The cat sat on the mat",
    "text_b": "A feline rested on a rug"
  }'
```

**Expected**: High cosine similarity (≈0.7-0.9) between semantically related texts.

### Learn More
- [What are Embeddings?](embeddings/what-are-embeddings.md)
- [Distance Metrics](embeddings/distance-metrics.md)
- [Embedding Models](embeddings/models.md)

---

## Step 2: Call an LLM

### What You'll Learn
- How chat messages work (system, user, assistant)
- How temperature and max_tokens affect output
- How streaming works

### Try It

```bash
# Non-streaming
curl -X POST http://localhost:8000/api/v1/llm/generate \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "You are a Python expert."},
      {"role": "user", "content": "What is a list comprehension?"}
    ],
    "temperature": 0.7,
    "max_tokens": 100
  }'

# Streaming
curl -N -X POST http://localhost:8000/api/v1/llm/generate-stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Tell me a joke"}],
    "stream": true
  }'
```

### Learn More
- [Prompt Engineering](prompting/what-is-a-prompt.md)
- [LLM APIs](llm/apis.md)
- [Temperature & Parameters](llm/parameters.md)

---

## Step 3: Ingest Documents

### What You'll Learn
- How documents are chunked
- How chunks are embedded and stored
- The relationship between chunks and embeddings

### Try It

```bash
# Ingest documents
curl -X POST http://localhost:8000/api/v1/rag/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "content": "Machine learning is a subset of artificial intelligence. It involves training models on data to make predictions or decisions.",
        "metadata": {"topic": "AI", "difficulty": "beginner"}
      },
      {
        "content": "Deep learning is a subset of machine learning that uses neural networks with many layers. It excels at processing unstructured data like images and text.",
        "metadata": {"topic": "AI", "difficulty": "intermediate"}
      }
    ]
  }'
```

**Expected Response**: Documents processed and chunks created.

### Learn More
- [What is RAG?](rag/what-is-rag.md)
- [Document Ingestion](rag/ingestion.md)
- [Chunking](rag/chunking.md)

---

## Step 4: Search Documents

### What You'll Learn
- How semantic search differs from keyword search
- How similarity scores rank results
- How vector databases work

### Try It

```bash
# Search for similar documents
curl -X POST http://localhost:8000/api/v1/rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is AI?",
    "top_k": 5
  }'
```

### Try the Demo

```bash
# See retrieval without LLM calls
curl "http://localhost:8000/api/v1/rag/demo?question=What+is+deep+learning&top_k=5"
```

This shows you exactly what context was retrieved and what prompt would be sent to the LLM.

### Learn More
- [Retrieval](rag/retrieval.md)
- [What is a Vector Database?](vector-databases/what-is-vdb.md)

---

## Step 5: Run Full RAG

### What You'll Learn
- The complete RAG flow
- How retrieved context grounds LLM responses
- How the LLM uses context to answer

### Try It

```bash
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the difference between AI and ML?",
    "top_k": 5
  }'
```

**Expected Response**: An answer grounded in the ingested documents, with
source citations.

### Learn More
- [RAG Flow](rag/rag-flow.md)
- [Context Construction](rag/context-construction.md)
- [Prompt Construction](rag/prompt-construction.md)

---

## Step 6: Explore Advanced Topics

### What You'll Learn
- How to improve RAG with query expansion
- How agents extend RAG with actions
- Safety considerations for production

### Try It

```bash
# Experiment with different chunk sizes
# Modify .env: RAG_CHUNK_SIZE=200 or RAG_CHUNK_SIZE=1000
docker compose restart app

# Try different temperatures
curl -X POST http://localhost:8000/api/v1/llm/generate \
  -d '{
    "messages": [{"role": "user", "content": "Write a creative haiku"}],
    "temperature": 1.2,
    "max_tokens": 50
  }'
```

### Learn More
- [Improving RAG](rag/improving-rag.md)
- [Hallucination](advanced/hallucination.md)
- [Security](advanced/security.md)
- [Agents](advanced/agents.md)

---

## Architecture Deep-Dive

After trying the hands-on examples, read the architecture docs:

1. [High-Level Architecture](architecture/high-level.md)
2. [Component Responsibilities](architecture/components.md)
3. [Data Flow](architecture/data-flow.md)
4. [RAG Flow](architecture/rag-flow.md)
5. [Embedding Flow](architecture/embedding-flow.md)
6. [Vector DB Interaction](architecture/vector-db-interaction.md)

## Key Takeaways

By completing this guide, you should be able to explain:

1. **What GenAI is** and how it differs from traditional AI
2. **How LLMs work** — transformers, attention, context windows
3. **How prompts influence** model behavior
4. **What embeddings are** — semantic vectors, similarity metrics
5. **What vector databases do** — store and search vectors efficiently
6. **How RAG works** — grounding LLMs with retrieved context
7. **How to build** a GenAI application with Python + FastAPI

## Next Steps

- Run the test suite: `poetry run pytest`
- Read the [experiments](experiments.md) page for ideas
- Modify the system: try different embedding models, chunking strategies
- Build your own application using this as a reference
