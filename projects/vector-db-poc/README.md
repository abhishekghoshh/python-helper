# Vector DB POC

A proof-of-concept for learning about **vector databases** and **vector embeddings** with Python, FastAPI, and Qdrant.

## Features

- Generate embeddings from text using `sentence-transformers` (`all-MiniLM-L6-v2`)
- Store and retrieve vectors with metadata in Qdrant
- Semantic search by meaning (not keywords)
- Fully Dockerized with `docker-compose` (API + Qdrant + MkDocs)
- Automated tests and MkDocs documentation

## Quick start

```bash
cp .env.example .env
docker-compose up --build
```

API: `http://localhost:8000` · Docs: `http://localhost:8000/docs`

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
