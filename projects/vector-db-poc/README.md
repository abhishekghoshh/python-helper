# Vector DB POC

A proof-of-concept for learning about **vector databases** and **vector embeddings** with Python, FastAPI, and Qdrant.

## Features

- Generate embeddings from text using `sentence-transformers` (`all-MiniLM-L6-v2`)
- Store and retrieve vectors with metadata in Qdrant
- Document chunking with configurable size and overlap
- Semantic search by meaning (not keywords), with score thresholds
- List and filter stored documents
- Configurable similarity metrics (cosine, euclidean, dot product)
- Fully Dockerized with `docker-compose` (API + Qdrant + MkDocs + Streamlit)
- Configurable logging via `LOG_LEVEL` and `LOG_FORMAT` environment variables

## Quick start

```bash
cp .env.example .env
docker-compose up --build
```

API: `http://localhost:8000` · Docs: `http://localhost:8001` · App: `http://localhost:8501` · API Docs: `http://localhost:8000/docs`

See the [full documentation](docs/) or run locally with [Poetry](https://python-poetry.org/):

```bash
poetry install
docker-compose up -d qdrant
poetry run uvicorn app.main:app --reload
```

Run tests:

```bash
poetry run pytest -v
```
