"""Shared test fixtures for the Vector DB POC test suite."""

import pytest
from httpx import AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """Async HTTP client for testing the FastAPI app in-process."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset service singletons before and after each test."""
    import app.api.routes as routes

    routes._embedding_service = None
    routes._vdb_service = None
    yield
    routes._embedding_service = None
    routes._vdb_service = None


@pytest.fixture
def qdrant_available():
    """Check if Qdrant is running; skip test if not."""
    from qdrant_client import QdrantClient
    from app.config import settings

    try:
        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        client.get_collections()
        yield client
    except Exception:
        pytest.skip("Qdrant is not running")
