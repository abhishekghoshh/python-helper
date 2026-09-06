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
│   └── chunking.py      # Text chunking utility
├── streamlit_app.py     # Streamlit web UI for the API
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
├── Dockerfile.streamlit
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
To include the Streamlit UI dependencies, add `--with streamlit`:

```bash
poetry install --with streamlit
```

## Running tests

```bash
poetry run pytest -v
```

## Running the docs server (local)

```bash
poetry run mkdocs serve
```

Open http://localhost:8000 in your browser.

## Running the Streamlit UI (local)

The Streamlit app provides a web interface for interacting with the vector
database API (embeddings, document CRUD, semantic search).

```bash
# 1. Start the API and Qdrant (via Docker Compose or locally)
docker-compose up -d api qdrant

# 2. Run Streamlit (install with: poetry install --with streamlit)
API_BASE_URL=http://localhost:8000 \
  poetry run streamlit run streamlit_app.py --server.port 8501
```

Or via Docker Compose — the `streamlit` service is pre-configured to
connect to the `api` service automatically.

## Docker commands

```bash
# Build and start all services
docker-compose up --build

# Start specific services
docker-compose up -d api qdrant streamlit

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
| `QDRANT_DISTANCE` | `cosine` | Distance metric: `cosine`, `euclidean`, or `dot` |
| `LOG_LEVEL` | `INFO` | Python log level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | `standard` | Log format: `standard` or `json` |
| `LOG_FILE` | (none) | Optional path for file logging |
| `API_BASE_URL` | `http://localhost:8000` | Backend API URL (Streamlit app) |
