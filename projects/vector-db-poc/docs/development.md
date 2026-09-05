# Development

## Project structure

```
vector-db-poc/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application factory
│   ├── config.py            # Pydantic Settings (env-based)
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py        # API endpoints
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py       # Pydantic request/response models
│   └── services/
│       ├── __init__.py
│       ├── embedding.py     # sentence-transformers wrapper
│       └── vector_db.py     # Qdrant client wrapper
├── tests/
│   ├── __init__.py
│   └── test_routes.py
├── docs/                    # MkDocs documentation
│   ├── index.md
│   ├── api.md
│   ├── concepts.md
│   └── development.md
├── Dockerfile
├── Dockerfile.docs
├── docker-compose.yml
├── pyproject.toml
├── poetry.lock
├── mkdocs.yml
└── .env.example
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
