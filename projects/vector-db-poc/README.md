# Vector DB POC

A proof-of-concept for learning about **vector databases** and **vector embeddings** with Python, FastAPI, and Qdrant.

## Features

- Generate embeddings from text using `sentence-transformers` (`all-MiniLM-L6-v2`)
- Store and retrieve vectors with metadata in Qdrant
- Semantic search by meaning (not keywords)
- Fully Dockerized with `docker-compose`
- Automated tests and MkDocs documentation

## Quick start

```bash
cp .env.example .env
docker-compose up --build
```

API: `http://localhost:8000` · Docs: `http://localhost:8000/docs`

See the [full documentation](docs/) or run locally with:

```bash
pip install -r requirements.txt
docker-compose up -d qdrant
uvicorn app.main:app --reload
```

Run tests:

```bash
pip install -r requirements-dev.txt
pytest -v
```
