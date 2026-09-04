# Vector DB POC

A proof-of-concept project to learn about **vector databases** and **vector embeddings** using Python, [FastAPI](https://fastapi.tiangolo.com/), and [Qdrant](https://qdrant.tech/).

## What this POC demonstrates

- **Generating embeddings** from text using [sentence-transformers](https://www.sbert.net/) (`all-MiniLM-L6-v2`)
- **Storing vectors** with metadata in a [Qdrant](https://qdrant.tech/) vector database
- **Semantic search** — find documents by meaning, not just keyword matching
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
- Or: Python 3.11+ with `requirements-dev.txt` installed

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
pip install -r requirements.txt
# Start Qdrant (Docker)
docker-compose up -d qdrant
# Start the API
uvicorn app.main:app --reload
```

## API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/api/v1/health` | Health check |
| POST   | `/api/v1/embed` | Generate embeddings for a text |
| POST   | `/api/v1/documents/` | Add a single document |
| POST   | `/api/v1/documents/batch/` | Add multiple documents |
| POST   | `/api/v1/search` | Semantic search |
| DELETE | `/api/v1/documents/{doc_id}` | Delete a document |

## Usage examples

See the [API Guide](api.md) for detailed examples.

## Learn more

- [Concepts](concepts.md) — vector embeddings, semantic search, and distance metrics
- [Vector Databases & Embeddings](vector-databases.md) — types of vector DBs, search algorithms, and use cases

## Documentation

Full documentation is available via [MkDocs](https://www.mkdocs.org/):

```bash
pip install -r requirements-docs.txt
mkdocs serve
```
