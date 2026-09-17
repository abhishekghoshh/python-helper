# High-Level Architecture

## System Overview

```mermaid
flowchart TD
    subgraph "External"
        User[User / Client]
        LLMAPI[LLM Provider<br/>OpenAI API]
    end

    subgraph "Docker Compose"
        API[FastAPI Application<br/>app/main.py]
        RAG["RAG Pipeline<br/>app/rag/"]
        Embed["Embedding Service<br/>app/embeddings/"]
        LLM["LLM Service<br/>app/llm/"]
        VDB["Vector DB Service<br/>app/services/vectordb.py"]
        Qdrant[(Qdrant<br/>Vector Database)]
    end

    subgraph "Containers"
        AppC["Container: app<br/>(Docker)"]
        QdrantC["Container: qdrant<br/>(Docker)"]
        DocsC["Container: mkdocs<br/>(Docker)"]
    end

    User -->|HTTP requests| API
    API --> RAG
    RAG --> Embed
    RAG --> LLM
    RAG --> VDB
    VDB --> Qdrant
    LLM -->|API calls| LLMAPI
    LLMAPI --> LLM
    Embed -->|Model inference| LLM
    RAG --> API

    style User fill:#3498db,color:#fff
    style API fill:#27ae60,color:#fff
    style RAG fill:#f39c12,color:#fff
    style VDB fill:#e74c3c,color:#fff
    style LLMAPI fill:#9b59b6,color:#fff
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Language** | Python 3.11 | Programming language |
| **Framework** | FastAPI | REST API server |
| **Dependency Mgmt** | Poetry | Package management |
| **LLM API** | OpenAI | Text generation |
| **Embeddings** | sentence-transformers | Local text-to-vector |
| **Vector DB** | Qdrant | Vector storage & search |
| **Documentation** | MkDocs + Material | Learning docs |
| **Containerization** | Docker | Deployment |
| **Orchestration** | Docker Compose | Multi-container setup |

## Architecture Patterns

### 1. Service Layer

Each major capability is a separate service:

```mermaid
graph TD
    AppDir["app/"]

    LLM["llm/ — LLM API wrapper<br/>Communicates with OpenAI/compatible APIs<br/>Non-streaming and streaming generation"]
    Emb["embeddings/ — Text-to-vector conversion<br/>Local sentence-transformers or OpenAI embeddings<br/>Batch and single embedding modes"]
    RAG["rag/ — RAG pipeline orchestration<br/>Ingestion, retrieval, and generation<br/>Pipeline, chunking, context, prompt assembly"]
    Svc["services/ — Vector database client<br/>Qdrant interactions<br/>Collection management, upsert, search"]

    AppDir --> LLM
    AppDir --> Emb
    AppDir --> RAG
    AppDir --> Svc

    RAG -->|uses| LLM
    RAG -->|uses| Emb
    RAG -->|uses| Svc

    style AppDir fill:#27ae60,color:#fff
    style LLM fill:#e74c3c,color:#fff
    style Emb fill:#9b59b6,color:#fff
    style RAG fill:#f39c12,color:#fff
    style Svc fill:#3498db,color:#fff
```

### 2. Dependency Injection

Services are injected into the RAG pipeline:

```python
# app/rag/pipeline.py
class RAGPipeline:
    def __init__(self, llm_service, embedding_service, vector_db_service):
        self.llm = llm_service
        self.embedding_service = embedding_service
        self.vector_db = vector_db_service
```

### 3. API Layer Separation

API endpoints are thin — they delegate to services:

```python
# app/api/v1/rag.py
async def rag_query(request: RAGRequest) -> RAGResponse:
    return await rag_pipeline.query(request)  # Business logic in service layer
```

## Data Flow Overview

```mermaid
flowchart TB
    subgraph "Ingestion Flow"
        D1[Documents] --> C1[Chunking]
        C1 --> E1[Embedding]
        E1 --> S1[Vector DB Storage]
    end

    subgraph "Query Flow"
        Q1[User Question] --> Q2[Query Embedding]
        Q2 --> VS1[Vector Search]
        VS1 --> R1[Retrieved Context]
        R1 --> P1[Prompt Construction]
        P1 --> L1[LLM Generation]
        L1 --> A1[Answer]
    end

    subgraph "External Services"
        LM[Local Model]
        OAI[OpenAI API]
    end

    E1 --> LM
    Q2 --> LM
    L1 --> OAI

    style D1 fill:#3498db,color:#fff
    style Q1 fill:#3498db,color:#fff
    style L1 fill:#27ae60,color:#fff
    style A1 fill:#27ae60,color:#fff
    style LM fill:#9b59b6,color:#fff
    style OAI fill:#e74c3c,color:#fff
```

## Configuration Management

```python
# app/core/config.py
class Settings(BaseSettings):
    # All configuration comes from environment variables
    llm_model: str = "gpt-3.5-turbo"
    embedding_model: str = "all-MiniLM-L6-v2"
    qdrant_collection: str = "genai-documents"
    ...
```

The `.env` file provides environment-specific values:

```bash
# .env (copy from .env.example)
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4
QDRANT_HOST=http://qdrant:6333
```

## Next Steps

- [Component Responsibilities](components.md)
- [Data Flow](data-flow.md)
- [API Documentation](api.md)
