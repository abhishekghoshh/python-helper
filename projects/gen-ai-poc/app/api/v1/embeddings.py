"""
Embeddings API endpoints — demonstrate text-to-vector conversion and
semantic similarity.

Endpoints:
- POST /embeddings/generate  — Convert text to a vector embedding
- POST /embeddings/similarity — Compare two texts for semantic similarity

These endpoints explain key concepts:
- What an embedding is (a dense vector representation of text)
- Why embeddings are useful (machine-readable semantic representation)
- How similarity is computed (cosine, euclidean, dot product)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.embeddings.service import embedding_service
from app.models.schemas import (
    EmbeddingRequest,
    EmbeddingResponse,
    SimilarityRequest,
    SimilarityResponse,
)

router = APIRouter(prefix="/embeddings", tags=["Embeddings"])
logger = logging.getLogger(__name__)


@router.post("/generate", response_model=EmbeddingResponse)
async def generate_embedding(request: EmbeddingRequest) -> EmbeddingResponse:
    """Generate an embedding vector for the given text.

    Returns the dense vector, model name, and dimensions.
    The vector is a list of floats that captures the semantic meaning
    of the input text — semantically similar texts produce similar vectors.
    """
    logger.info(
        "Embedding generate — text_len=%d, provider=%s",
        len(request.text),
        embedding_service.model_name,
    )
    return await embedding_service.embed_query(request.text)


@router.post("/similarity", response_model=SimilarityResponse)
async def compute_similarity(request: SimilarityRequest) -> SimilarityResponse:
    """Compute similarity between two texts.

    Returns three metrics:
    - **cosine**: Angle between vectors (ignores magnitude) — range [-1, 1]
    - **euclidean**: Straight-line distance — lower = more similar
    - **dot_product**: Raw inner product — higher = more similar

    Cosine is the default for most vector databases because it is
    insensitive to vector length and focuses on directional similarity.
    """
    logger.info("Similarity compute — len_a=%d, len_b=%d", len(request.text_a), len(request.text_b))
    return await embedding_service.similarity(request.text_a, request.text_b)
