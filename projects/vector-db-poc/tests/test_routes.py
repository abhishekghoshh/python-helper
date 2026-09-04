"""Tests for the Vector DB POC FastAPI app."""

import pytest
from httpx import AsyncClient
from fastapi import FastAPI

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "embedding_model" in data


@pytest.mark.asyncio
async def test_embed(client: AsyncClient):
    resp = await client.post("/api/v1/embed?text=hello+world")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["vector"]) > 0
    assert data["dimension"] == len(data["vector"])


@pytest.mark.asyncio
async def test_root(client: AsyncClient):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "message" in resp.json()
