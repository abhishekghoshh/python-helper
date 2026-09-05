# Development

## Project structure

```
vector-db-poc/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Pydantic Settings (env-based)
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py        # API endpoints (health, embed, documents, search, delete)
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py       # Pydantic request/response models
│   └── services/
│       ├── __init__.py
│       ├── embedding.py     # sentence-transformers wrapper
│       ├── vector_db.py     # Qdrant client wrapper
│       └── chunking.py      # Text chunking utility
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Shared fixtures
│   ├── test_routes.py       # API integration tests
│   └── test_chunking.py     # Unit tests for chunking
├── docs/                    # MkDocs documentation
│   ├── api.md
│   ├── concepts.md
│   ├── concepts/
│   │   ├── vectors.md
│   │   ├── embeddings.md
│   │   ├── embedding-models.md
│   │   ├── similarity.md
│   │   ├── chunking.md
│   │   └── metadata.md
│   ├── vector-databases.md
│   ├── vector-databases/
│   │   ├── comparison.md
│   │   ├── indexing.md
│   │   ├── ann.md
│   │   ├── hybrid-search.md
│   │   └── metadata-filtering.md
│   ├── architecture/
│   │   ├── architecture.md
│   │   ├── data-flow.md
│   │   ├── embedding-service.md
│   │   ├── vector-db-service.md
│   │   └── api-routes.md
│   ├── development.md
│   ├── interview/
│   │   ├── fundamentals.md
│   │   ├── similarity-search.md
│   │   ├── vector-databases.md
│   │   ├── embedding-models.md
│   │   ├── system-design.md
│   │   └── scenarios.md
│   ├── index.md
│   └── project-review.md
├── Dockerfile
├── Dockerfile.docs
├── docker-compose.yml
├── pyproject.toml
├── poetry.lock
└── mkdocs.yml
```

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/)
- [Poetry](https://python-poetry.org/) for local development
- Python 3.11+

## Installation

```bash
poetry install
```

This installs the main dependencies plus the `dev` and `docs` groups.

## Running tests

```bash
poetry run pytest -v
```

## Running the docs server (local)

```bash
poetry run mkdocs serve
```

## Docker commands

```bash
# Build and start
docker-compose up --build

# Stop and clean
docker-compose down -v

# Rebuild
docker-compose up --build --force-recreate
```

## Environment variables

Copy `.env.example` to `.env` and adjust:

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_HOST` | `localhost` | Qdrant host |
| `QDRANT_PORT` | `6333` | Qdrant REST port |
| `COLLECTION_NAME` | `demo` | Qdrant collection name |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model |
| `EMBEDDING_DIM` | `384` | Expected embedding dimension |
| `QDRANT_DISTANCE` | `cosine` | Distance metric: `cosine`, `euclidean`, or `dot` |
