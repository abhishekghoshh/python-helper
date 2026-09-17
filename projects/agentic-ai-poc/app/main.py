"""
FastAPI application entry point for the Agentic AI POC.

Creates the FastAPI application and registers the API router. The agent
factory (which selects mock vs. real LLM, builds tools, and wires
memory) lives in ``app/api/dependencies.py``.

Run locally:

    poetry run uvicorn app.main:app --reload

Run with Docker:

    docker-compose up --build
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    description=(
        "An Agentic AI learning POC demonstrating a ReAct agent loop with "
        "tool calling, memory, planning, RAG-as-a-tool, guardrails, and "
        "observability."
    ),
    version=settings.app_version,
)

app.include_router(router, prefix="/api/v1")


@app.get("/")
def root() -> dict:
    """Root endpoint — lists available entry points."""
    return {
        "message": "Agentic AI POC",
        "app": settings.app_name,
        "version": settings.app_version,
        "simulated_mode": settings.use_mock_llm,
        "docs": "/docs",
        "api": "/api/v1",
        "endpoints": {
            "chat": "POST /api/v1/chat",
            "chat_stream": "POST /api/v1/chat/stream",
            "run": "POST /api/v1/run",
            "tools": "GET /api/v1/tools",
            "rag_ingest": "POST /api/v1/rag/ingest",
            "health": "GET /api/v1/health",
        },
    }


@app.get("/api/v1/health")
def health() -> dict:
    """Health check."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "simulated_mode": settings.use_mock_llm,
        "model": settings.llm_model,
    }
