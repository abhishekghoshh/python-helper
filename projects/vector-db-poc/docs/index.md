# Vector DB POC

A proof-of-concept project to learn about **vector databases** and **vector embeddings** using Python, [FastAPI](https://fastapi.tiangolo.com/), and [Qdrant](https://qdrant.tech/).

## What this POC demonstrates

- **Generating embeddings** from text using [sentence-transformers](https://www.sbert.net/) (`all-MiniLM-L6-v2`)
- **Storing vectors** with metadata in a [Qdrant](https://qdrant.tech/) vector database
- **Document chunking** — split long documents into overlapping chunks for better retrieval
- **Semantic search** — find documents by meaning, not just keyword matching, with configurable score thresholds and top-K
- **Metadata filtering** — store and filter documents by metadata
- **Dockerized** deployment with `docker-compose`

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    FastAPI App                      │
│  (app/main.py, app/api/routes.py)                   │
│                                                     │
│  ┌──────────────┐    ┌────────────────────────┐    │
│  │ Embedding    │    │   VectorDB Service     │    │
│  │ Service      │◄──►│  (Qdrant client)       │
│  │              │    │                        │    │
│  │ sentence    │    │                        │    │
│  │ -transformers│    │  Qdrant (Docker)       │    │
│  └──────────────┘    └────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

## Quick start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/)
- Or: Python 3.11+ with [Poetry](https://python-poetry.org/) installed

### Run with Docker

```bash
cp .env.example .env
docker-compose up --build
```

The API will be available at `http://localhost:8000`.

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- API root: `http://localhost:8000/api/v1`

### Run locally

```bash
poetry install
# Start Qdrant (Docker)
docker-compose up -d qdrant
# Start the API
poetry run uvicorn app.main:app --reload
```

### Run the docs server

```bash
poetry run mkdocs serve
# Docs: http://localhost:8000
```

Or via Docker:

```bash
docker-compose up -d docs
# Docs: http://localhost:8001
```

## API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/api/v1/health` | Health check |
| POST   | `/api/v1/embed` | Generate embeddings for a text |
| POST   | `/api/v1/documents/` | Add a single document |
| POST   | `/api/v1/documents/batch/` | Add multiple documents |
| GET    | `/api/v1/documents/` | List all stored documents |
| POST   | `/api/v1/search` | Semantic search |
| DELETE | `/api/v1/documents/{doc_id}` | Delete a document |

## Usage examples

See the [API Guide](api.md) for detailed examples.

## Learn more

- [Architecture](architecture/architecture.md) — how the components connect
- [Concepts](concepts.md) — vectors, embeddings, similarity metrics
- [Vector Databases](vector-databases.md) — types of vector DBs, search algorithms
- [API Guide](api.md) — detailed API documentation
- [Interview Prep](interview/fundamentals.md) — Q&A for embeddings and vector DB interviews

## Documentation

Full documentation is available via [MkDocs](https://www.mkdocs.org/):

```bash
poetry run mkdocs serve
```
