"""Pytest fixtures shared across test modules."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_client():
    """Provide a TestClient for API tests."""
    from app.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_documents():
    """Sample documents for ingestion tests."""
    return [
        {
            "content": (
                "Machine learning is a subset of artificial intelligence "
                "that enables computers to learn from data without being "
                "explicitly programmed. It includes supervised, unsupervised, "
                "and reinforcement learning."
            ),
            "metadata": {"topic": "AI", "difficulty": "beginner"},
        },
        {
            "content": (
                "Deep learning is a subset of machine learning that uses "
                "neural networks with many layers. It excels at processing "
                "unstructured data like images, text, and audio."
            ),
            "metadata": {"topic": "AI", "difficulty": "intermediate"},
        },
        {
            "content": (
                "RAG (Retrieval-Augmented Generation) combines a retriever "
                "and a generator. The retriever finds relevant documents, "
                "and the generator produces answers grounded in that context."
            ),
            "metadata": {"topic": "GenAI", "difficulty": "intermediate"},
        },
    ]
