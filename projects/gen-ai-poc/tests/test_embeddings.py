"""Tests for the embedding service and similarity metrics."""

import numpy as np
import pytest

from app.embeddings.service import (
    compute_similarity,
    cosine_similarity,
    dot_product,
    euclidean_distance,
)
from app.models.schemas import SimilarityResponse


class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 2.0, 3.0]
        result = cosine_similarity(v, v)
        assert result == pytest.approx(1.0, abs=0.001)

    def test_orthogonal_vectors(self):
        # [1, 0] and [0, 1] are orthogonal → cosine = 0
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        result = cosine_similarity(a, b)
        assert result == pytest.approx(0.0, abs=0.001)

    def test_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        result = cosine_similarity(a, b)
        assert result == pytest.approx(-1.0, abs=0.001)

    def test_similar_vectors_high_score(self):
        a = [1.0, 2.0, 3.0]
        b = [2.0, 4.0, 6.0]  # Same direction, double magnitude
        result = cosine_similarity(a, b)
        assert result == pytest.approx(1.0, abs=0.001)

    def test_zero_vector(self):
        result = cosine_similarity([0.0, 0.0], [1.0, 2.0])
        assert result == 0.0


class TestEuclideanDistance:
    def test_identical_vectors(self):
        v = [1.0, 2.0, 3.0]
        result = euclidean_distance(v, v)
        assert result == pytest.approx(0.0)

    def test_orthogonal_vectors(self):
        a = [0.0, 0.0]
        b = [3.0, 4.0]
        result = euclidean_distance(a, b)
        assert result == pytest.approx(5.0)  # 3-4-5 triangle

    def test_known_distance(self):
        a = [0.0, 0.0, 0.0]
        b = [1.0, 1.0, 1.0]
        result = euclidean_distance(a, b)
        assert result == pytest.approx(np.sqrt(3))


class TestDotProduct:
    def test_known_dot_product(self):
        a = [1.0, 2.0, 3.0]
        b = [4.0, 5.0, 6.0]
        result = dot_product(a, b)
        assert result == pytest.approx(32.0)  # 1*4 + 2*5 + 3*6

    def test_orthogonal(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        result = dot_product(a, b)
        assert result == pytest.approx(0.0)


class TestComputeSimilarity:
    def test_returns_all_metrics(self):
        a = [1.0, 2.0, 3.0]
        b = [4.0, 5.0, 6.0]
        result = compute_similarity(a, b)
        assert isinstance(result, SimilarityResponse)
        assert result.cosine is not None
        assert result.euclidean is not None
        assert result.dot_product is not None

    def test_cosine_in_range(self):
        a = [1.0, 2.0, 3.0]
        b = [4.0, 5.0, 6.0]
        result = compute_similarity(a, b)
        assert -1.0 <= result.cosine <= 1.0

    def test_identical_vectors(self):
        v = [1.0, 2.0, 3.0]
        result = compute_similarity(v, v)
        assert result.cosine == pytest.approx(1.0, abs=0.001)
        assert result.euclidean == pytest.approx(0.0, abs=0.001)

    def test_similar_vs_dissimilar(self):
        """Similar vectors should have higher cosine than dissimilar ones."""
        base = [1.0, 0.0, 0.0]
        similar = [0.9, 0.1, 0.0]
        dissimilar = [0.0, 0.9, 0.1]

        sim_score = cosine_similarity(base, similar)
        dis_score = cosine_similarity(base, dissimilar)
        assert sim_score > dis_score
