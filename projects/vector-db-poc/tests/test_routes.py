"""Tests for API routes.

Unit tests for health, embed, and root endpoints run without any external
services. Integration tests for document CRUD and search require a running
Qdrant instance and are skipped automatically when Qdrant is unavailable.
"""

import pytest
from httpx import AsyncClient

from app.main import app


# ---------------------------------------------------------------------------
# Unit tests (no external services required)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_health(client: AsyncClient):
    """Health endpoint confirms the app is running."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "embedding_model" in data


@pytest.mark.anyio
async def test_embed(client: AsyncClient):
    """Embed endpoint produces a non-empty vector of expected dimension."""
    response = await client.post(
        "/api/v1/embed",
        json={"text": "Hello, vector databases!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["vector"]) > 0
    assert data["vector"][0] is not None
    assert data["dimension"] == 384


@pytest.mark.anyio
async def test_root(client: AsyncClient):
    """Root endpoint returns project information."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Vector DB POC"
    assert data["docs"] == "/docs"


# ---------------------------------------------------------------------------
# Integration tests (require a running Qdrant instance)
# ---------------------------------------------------------------------------

@pytest.fixture
def vdb(qdrant_available):
    """Provide a fresh VectorDBService, ensuring the collection exists."""
    from app.api.routes import get_vector_db_service
    from app.config import settings

    service = get_vector_db_service()
    service.ensure_collection()
    yield service
    # teardown – remove collection so tests are isolated
    try:
        service.client.delete_collection(settings.collection_name)
    except Exception:
        pass


@pytest.mark.anyio
async def test_add_and_list_document(client: AsyncClient, vdb):
    """Adding a document then listing should show it."""
    response = await client.post(
        "/api/v1/documents/",
        json={
            "id": "doc-1",
            "text": "Vector databases store embeddings for fast search.",
            "metadata": {"category": "database"},
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "doc-1"
    assert data["inserted_chunks"] == 1
    assert "chunk_index" not in data.get("metadata", {})

    response = await client.get("/api/v1/documents/")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    docs = [d for d in data["documents"] if d["id"] == "doc-1"]
    assert len(docs) == 1


@pytest.mark.anyio
async def test_add_document_with_chunking(client: AsyncClient, vdb):
    """Large documents are split into multiple chunks."""
    long_text = "This is a long document about vector search. " * 20
    response = await client.post(
        "/api/v1/documents/",
        json={
            "id": "doc-chunked",
            "text": long_text,
            "metadata": {"category": "example"},
            "chunk_size": 100,
            "chunk_overlap": 10,
        },
    )
    assert response.status_code == 201
    assert response.json()["inserted_chunks"] > 1


@pytest.mark.anyio
async def test_batch_add_and_chunking(client: AsyncClient, vdb):
    """Batch endpoint accepts multiple documents with per-doc chunking."""
    response = await client.post(
        "/api/v1/documents/batch/",
        json=[
            {"id": "batch-1", "text": "Short text.", "metadata": {"cat": "a"}},
            {
                "id": "batch-2",
                "text": "Another long document about embeddings. " * 10,
                "metadata": {"cat": "b"},
                "chunk_size": 80,
                "chunk_overlap": 10,
            },
        ],
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["ids"]) == 2
    assert data["inserted"] >= 2


@pytest.mark.anyio
async def test_search_returns_results(client: AsyncClient, vdb):
    """Search returns semantically relevant results."""
    await client.post(
        "/api/v1/documents/",
        json={
            "id": "search-demo",
            "text": "Vector databases store embeddings for fast similarity search.",
            "metadata": {"category": "database"},
        },
    )

    response = await client.post("/api/v1/search", json={"query": "vector search"})
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "vector search"
    assert len(data["hits"]) > 0
    for hit in data["hits"]:
        assert "chunk_index" not in hit.get("metadata", {})


@pytest.mark.anyio
async def test_search_with_score_threshold(client: AsyncClient, vdb):
    """Score threshold filters out low-similarity results."""
    await client.post(
        "/api/v1/documents/",
        json={
            "id": "threshold-demo",
            "text": "Vector databases store embeddings for fast similarity search.",
            "metadata": {"category": "database"},
        },
    )

    response = await client.post(
        "/api/v1/search",
        json={"query": "vector database", "score_threshold": 0.5},
    )
    assert response.status_code == 200
    for hit in response.json()["hits"]:
        assert hit["score"] >= 0.5


@pytest.mark.anyio
async def test_search_no_collection(client: AsyncClient, qdrant_available):
    """Search on a non-existent collection returns 404."""
    from app.config import settings

    qdrant_available.delete_collection(settings.collection_name)

    response = await client.post("/api/v1/search", json={"query": "test"})
    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_document(client: AsyncClient, vdb):
    """Deleting a document removes it from search results."""
    await client.post(
        "/api/v1/documents/",
        json={
            "id": "delete-me",
            "text": "This document will be deleted.",
            "metadata": {"category": "temp"},
        },
    )

    response = await client.delete("/api/v1/documents/delete-me")
    assert response.status_code == 204

    response = await client.get("/api/v1/documents/")
    ids = [d["id"] for d in response.json()["documents"]]
    assert "delete-me" not in ids


@pytest.mark.anyio
async def test_health_includes_embedding_dim(client: AsyncClient, vdb):
    """Health endpoint reports the embedding dimension."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["embedding_dim"] == 384
