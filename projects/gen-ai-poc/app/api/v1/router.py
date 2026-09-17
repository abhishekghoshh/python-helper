"""
API router — aggregates all v1 route modules under a single prefix.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.api.v1 import embeddings, llm, rag

logger = logging.getLogger(__name__)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(llm.router)
api_router.include_router(embeddings.router)
api_router.include_router(rag.router)

logger.info("API v1 router registered — prefix=/api/v1")
