# Data Flow

This page documents how data moves through the system — both for
**ingestion** (loading documents) and **querying** (answering questions).

## Ingestion Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant Ingestion
    participant Embedding
    participant VectorDB
    participant Qdrant

    Client->>FastAPI: POST /rag/ingest {documents}
    FastAPI->>Ingestion: ingest_documents(docs)
    Ingestion->>Ingestion: chunk_text()
    Ingestion->>Embedding: embed_many(texts)
    Embedding->>Embedding: model.encode() [sentence-transformers]
    Embedding-->>Ingestion: list[list[float]]
    Ingestion->>VectorDB: upsert_chunks(chunks, embeddings)
    VectorDB->>Qdrant: upsert({id, vector, payload})
    Qdrant-->>VectorDB: Ack
    VectorDB-->>Ingestion: Success
    Ingestion-->>FastAPI: (docs_processed, chunks_created)
    FastAPI-->>Client: IngestResponse
```

### Step-by-Step

1. **Client** sends documents to `/api/v1/rag/ingest`
2. **FastAPI** validates the request and passes documents to the RAG pipeline
3. **Ingestion** splits documents into chunks using `chunk_text()`
4. **Embedding** converts each chunk to a vector using sentence-transformers
5. **VectorDB** upserts chunks + vectors + metadata to Qdrant
6. **Qdrant** stores vectors in the HNSW index
7. **Response** returns count of documents processed and chunks created

## Query (RAG) Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant Pipeline
    participant Retrieval
    participant Embedding
    participant VectorDB
    participant Qdrant
    participant Generation
    participant LLM
    participant LLMProvider

    Client->>FastAPI: POST /rag/query {question}
    FastAPI->>Pipeline: query(RAGRequest)
    
    Note over Pipeline: Step 1: Retrieve
    Pipeline->>Retrieval: retrieve_context(question)
    Retrieval->>Embedding: embed(question)
    Embedding-->>Retrieval: query_vector
    Retrieval->>VectorDB: search(query_vector, top_k=5)
    VectorDB->>Qdrant: search(query_vector, k=5)
    Qdrant-->>VectorDB: ScoredPoints[]
    VectorDB-->>Retrieval: SearchHit[]
    
    Note over Pipeline: Step 2: Generate
    Pipeline->>Generation: generate_answer(hits, question)
    Generation->>Generation: build_context(hits)
    Generation->>Generation: build_rag_prompt(question, context)
    Generation->>LLM: generate(messages)
    LLM->>LLMProvider: POST /chat/completions
    LLMProvider-->>LLM: ChatCompletion
    LLM-->>Generation: LLMResponse
    Generation-->>Pipeline: RAGResponse
    Pipeline-->>FastAPI: RAGResponse
    FastAPI-->>Client: {answer, sources, context}
```

### Step-by-Step

1. **Client** sends a question to `/api/v1/rag/query`
2. **Pipeline** orchestrates the RAG flow
3. **Retrieval** embeds the question and searches the vector DB
4. **VectorDB** sends the query vector to Qdrant's HNSW index
5. Qdrant returns ranked document chunks (SearchHits)
6. **Generation** builds a context string from the retrieved chunks
7. **Generation** constructs a prompt: system + context + question
8. **LLM** sends the prompt to the OpenAI API
9. **LLM Provider** generates a grounded answer
10. **Response** includes the answer, source chunks, and context

## Embedding Service Flow

```mermaid
flowchart LR
    T[Text] --> Token[Tokenizer]
    Token --> Model[Transformer Model]
    Model --> Hidden[Hidden States]
    Hidden --> Pool[Pooling Layer]
    Pool --> V[Vector]

    subgraph "Backend Options"
        ST["sentence-transformers\n(all-MiniLM-L6-v2)"]
        OAI["OpenAI API\n(text-embedding-3-small)"]
    end

    Model --> ST
    Model --> OAI
    ST --> V
    OAI --> V

    style T fill:#3498db,color:#fff
    style Model fill:#e74c3c,color:#fff
    style V fill:#27ae60,color:#fff
    style ST fill:#f39c12,color:#fff
    style OAI fill:#f39c12,color:#fff
```

## LLM Call Flow

```mermaid
sequenceDiagram
    participant Pipeline
    participant LLMService
    participant OpenAI

    Pipeline->>LLMService: generate(messages, params)
    LLMService->>LLMService: resolve_parameters()
    LLMService->>OpenAI: POST /chat/completions
    OpenAI-->>LLMService: {id, choices, usage}
    LLMService-->>Pipeline: LLMResponse

    Note over Pipeline: messages = system + context + question
    Note over OpenAI: temperature=0.7, max_tokens=1024
```

## Error Handling

```mermaid
flowchart TD
    Start[API Request] --> Validate[Validate Input]
    Validate -->|Invalid| RE[400 BadRequest]
    
    Validate --> Call[Call Service]
    Call -->|API Error| Err[502 Bad Gateway]
    Call -->|Timeout| TO[504 Gateway Timeout]
    Call -->|Success| Resp[200 OK]
    
    Err --> Log[Log Error]
    TO --> Log
    Log --> Client[Return Error to Client]
    
    style RE fill:#e74c3c,color:#fff
    style Err fill:#e74c3c,color:#fff
    style TO fill:#e74c3c,color:#fff
    style Resp fill:#27ae60,color:#fff
    style Log fill:#f39c12,color:#fff

    Start -->|Invalid API Key| AuthErr[401 Unauthorized]
    AuthErr --> Err
```

## Data Formats

### Document (Input)

```json
{
  "content": "Machine learning is a subset of AI...",
  "metadata": {
    "source": "lecture_notes",
    "category": "AI",
    "author": "Dr. Smith"
  }
}
```

### Chunk (Internal)

```json
{
  "id": "doc_001_chunk_0",
  "text": "Machine learning is a subset of AI...",
  "document_id": "doc_001",
  "chunk_index": 0,
  "metadata": {"source": "lecture_notes", "category": "AI"}
}
```

### SearchHit (Output)

```json
{
  "id": "doc_001_chunk_0",
  "score": 0.8923,
  "text": "Machine learning is a subset of AI...",
  "metadata": {"source": "lecture_notes", "document_id": "doc_001"}
}
```

### RAGResponse (Output)

```json
{
  "answer": "Machine learning is a subset of AI...",
  "sources": [
    {"id": "chunk_0", "score": 0.89, "text": "...", "metadata": {...}}
  ],
  "context": "[Source 1] (score: 0.89)\n..."
}
```

## Next Steps

- [API Documentation](api.md)
- [RAG Flow](rag-flow.md) — The core pipeline detail
- [Embedding Flow](embedding-flow.md)
