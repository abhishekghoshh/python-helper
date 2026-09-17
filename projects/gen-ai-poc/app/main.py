"""
FastAPI application entry point.

Run with:
    uvicorn app.main:app --host 0.0.0.0 --port 8000

Or via Docker:
    docker compose up app
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging_config import configure_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle hooks."""
    configure_logging()
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    logger.info("LLM provider: %s, model: %s", settings.llm_provider, settings.llm_model)
    logger.info(
        "Embedding provider: %s, model: %s",
        settings.embedding_provider,
        settings.embedding_model,
    )
    logger.info("Vector DB: %s, collection: %s", settings.qdrant_host, settings.qdrant_collection)
    logger.info("Log level: %s, format: %s", settings.log_level, settings.log_format)
    yield


# Configure logging at import time for modules that log before lifespan runs
configure_logging()


app = FastAPI(
    title=settings.app_name,
    description=(
        "A hands-on Generative AI POC demonstrating LLMs, embeddings, "
        "RAG, and vector databases with Python and FastAPI."
    ),
    version=settings.app_version,
    docs_url="/",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — allow frontend dev servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
