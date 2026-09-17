# RAG Flow: Retrieval and Generation

This page details the complete RAG pipeline as implemented in the codebase.

## Complete RAG Flow Diagram

```mermaid
flowchart TD
    subgraph "Ingestion (Offline)"
        DOCS[Documents] --> CHUNK[Chunking]
        CHUNK --> EMB_IN[Embedding Generation]
        EMB_IN --> STORE[Vector DB Storage]
        STORE --> INDEX[Indexed Vectors]
    end

    subgraph "Query (Online)"
        Q[User Question] --> EMB_Q[Query Embedding]
        EMB_Q --> SEARCH[Vector Search]
        INDEX --> SEARCH
        SEARCH --> HITS[Retrieved Chunks]
        HITS --> CONTEXT[Context Construction]
        CONTEXT --> PROMPT[Prompt Assembly]
        PROMPT --> LLM_CALL[LLM API Call]
        LLM_CALL --> ANSWER[Generated Answer]
    end

    subgraph "External"
        MODEL[Embedding Model]
        LLM_API[LLM Provider API]
    end

    EMB_IN --> MODEL
    EMB_Q --> MODEL
    LLM_CALL --> LLM_API

    style DOCS fill:#3498db,color:#fff
    style Q fill:#3498db,color:#fff
    style INDEX fill:#e74c3c,color:#fff
    style SEARCH fill:#e74c3c,color:#fff
    style ANSWER fill:#27ae60,color:#fff
    style MODEL fill:#9b59b6,color:#fff
    style LLM_API fill:#f39c12,color:#fff
```

## Code Walkthrough

### Entry Point: API Router

```python
# app/api/v1/rag.py
@router.post("/query", response_model=RAGResponse)
async def rag_query(request: RAGRequest) -> RAGResponse:
    """Full RAG pipeline: retrieve context + generate answer."""
    return await rag_pipeline.query(request)
```

### Step 1: Pipeline Orchestration

```python
# app/rag/pipeline.py
class RAGPipeline:
    async def query(self, request: RAGRequest) -> RAGResponse:
        # 1. Retrieve relevant context
        hits = await self.retrieve(
            question=request.question,
            top_k=request.top_k,
        )

        # 2. Generate answer using retrieved context
        response = await generate_answer(
            question=request.question,
            hits=hits,
            llm_service=self.llm,
            model=request.model,
            temperature=request.temperature,
        )

        return response
```

### Step 2: Retrieval

```python
# app/rag/retrieval.py
async def retrieve_context(
    question: str,
    vector_db_service,
    embedding_service,
    top_k: int | None = None,
) -> list[SearchHit]:
    # Embed the query
    query_embedding = await embedding_service.embed(question)

    # Search the vector database
    hits = await vector_db_service.search(
        query_vector=query_embedding,
        top_k=top_k or settings.rag_top_k,
    )

    return hits
```

### Step 3: Context Construction

```python
# app/rag/retrieval.py
def build_context(hits: list[SearchHit], max_chars: int = 3000) -> str:
    parts = []
    for i, hit in enumerate(hits):
        snippet = f"[Source {i + 1}] (score: {hit.score:.4f})\n{hit.text}"
        parts.append(snippet)
    return "\n---\n".join(parts)
```

### Step 4: Prompt Construction

```python
# app/rag/generation.py
messages = [
    ChatMessage(
        role=MessageRole.SYSTEM,
        content="You are a helpful assistant that answers questions "
                "based on the provided context. Do not make up facts."
    ),
    ChatMessage(
        role=MessageRole.USER,
        content=f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
    ),
]
```

### Step 5: LLM Generation

```python
# app/llm/service.py
response = await self.client.chat.completions.create(
    model=model,
    messages=messages,
    temperature=temperature,
    max_tokens=max_tokens,
)

return LLMResponse(
    id=response.id,
    model=response.model,
    content=response.choices[0].message.content,
    usage=response.usage.model_dump(),
)
```

## Component Interactions

```mermaid
flowchart LR
    A[FastAPI API] --> B[RAGPipeline]
    B --> C[Retrieval]
    B --> D[Generation]
    C --> E[EmbeddingService]
    C --> F[VectorDBService]
    D --> G[LLMService]
    E --> H[sentence-transformers]
    F --> I[Qdrant Server]
    G --> J[OpenAI API]

    style A fill:#27ae60,color:#fff
    style B fill:#f39c12,color:#fff
    style C fill:#e74c3c,color:#fff
    style D fill:#e74c3c,color:#fff
    style E fill:#9b59b6,color:#fff
    style F fill:#3498db,color:#fff
    style G fill:#e74c3c,color:#fff
    style H fill:#9b59b6,color:#fff
    style I fill:#3498db,color:#fff
    style J fill:#e74c3c,color:#fff
```

## Data Structures

### Flow: Question to Answer

```mermaid
graph TD
    Q["Question: 'What is ML?'"] --> E["Embedding: [0.23, -0.87, ...]"]
    E --> S["Search: top-5 hits in Qdrant"]
    S --> H1["Hit: 'ML is...' (score: 0.89)"]
    S --> H2["Hit: 'AI includes...' (score: 0.75)"]
    H1 --> C["Context: [Source 1]... --- [Source 2]..."]
    H2 --> C
    C --> P["Prompt: system + context + question"]
    P --> L["LLM: generates answer"]
    L --> A["Answer: 'Machine Learning is...'"]

    style Q fill:#3498db,color:#fff
    style E fill:#9b59b6,color:#fff
    style S fill:#e74c3c,color:#fff
    style C fill:#f39c12,color:#fff
    style P fill:#8e44ad,color:#fff
    style L fill:#27ae60,color:#fff
    style A fill:#27ae60,color:#fff
```

## Error Handling in the Flow

```mermaid
graph TD
    Q[User Question] --> R[Retrieve]
    R --> RQ[Query Embedding]
    RQ --> RS[Vector Search]
    RS -->|Empty| EH[Empty Hits Handler]
    EH -->|"I don't have enough info"| A1[Fallback Answer]
    RS -->|Hits found| H[Hits]
    H --> C[Context Build]
    C --> P[Prompt]
    P --> L[LLM Call]
    L -->|API Error| EH2[Error Handler]
    EH2 -->|"Error generating response"| A2[Error Response]
    L -->|Success| A3[Generated Answer]

    style A1 fill:#f39c12,color:#fff
    style A2 fill:#e74c3c,color:#fff
    style A3 fill:#27ae60,color:#fff
```

## Next Steps

- [Embedding Flow](embedding-flow.md)
- [Vector DB Interaction](vector-db-interaction.md)
- [Data Flow](data-flow.md)
