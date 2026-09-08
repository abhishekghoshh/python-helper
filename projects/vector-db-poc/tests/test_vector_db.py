"""Unit tests for the VectorDBService and ID mapping utility.

These tests do not require a running Qdrant instance — they verify the
pure-Python logic of distance-metric mapping and UUID generation.
"""

import uuid

import pytest

from app.services.vector_db import VectorDBService, _DISTANCE_MAP, to_uuid
from qdrant_client.http import models as qmodels


# ---------------------------------------------------------------------------
# to_uuid — deterministic string → UUID5 mapping
# ---------------------------------------------------------------------------

def test_to_uuid_deterministic():
    """The same input string always maps to the same UUID."""
    a = to_uuid("doc-1")
    b = to_uuid("doc-1")
    assert a == b


def test_to_uuid_different_inputs():
    """Different input strings produce different UUIDs."""
    assert to_uuid("doc-1") != to_uuid("doc-2")


def test_to_uuid_is_uuid5():
    """The generated UUID is a valid UUID5 under the DNS namespace."""
    result = to_uuid("my-doc")
    assert isinstance(result, uuid.UUID)
    assert result.version == 5


def test_to_uuid_string_roundtrip():
    """Chunk IDs with suffixes are also handled deterministically."""
    assert to_uuid("doc-1__0") != to_uuid("doc-1__1")
    assert to_uuid("doc-1__0") == to_uuid("doc-1__0")


# ---------------------------------------------------------------------------
# Distance metric mapping
# ---------------------------------------------------------------------------

def test_distance_map_contains_all_metrics():
    """All three supported distance metrics are in the map."""
    assert _DISTANCE_MAP["cosine"] == qmodels.Distance.COSINE
    assert _DISTANCE_MAP["euclidean"] == qmodels.Distance.EUCLID
    assert _DISTANCE_MAP["dot"] == qmodels.Distance.DOT


def test_default_distance_is_cosine():
    """When no distance is specified, cosine is used."""
    service = VectorDBService(
        client=None,  # we never actually use the client in this test
        collection_name="test",
        embedding_dim=384,
    )
    assert service.distance == qmodels.Distance.COSINE


@pytest.mark.parametrize(
    "metric_name,expected",
    [
        ("cosine", qmodels.Distance.COSINE),
        ("euclidean", qmodels.Distance.EUCLID),
        ("dot", qmodels.Distance.DOT),
        ("COSINE", qmodels.Distance.COSINE),  # case-insensitive
        ("EUCLIDEAN", qmodels.Distance.EUCLID),
    ],
)
def test_distance_metric_mapping(metric_name, expected):
    """VectorDBService maps string distance names to Qdrant Distance enums."""
    service = VectorDBService(
        client=None,
        collection_name="test",
        embedding_dim=384,
        distance=metric_name,
    )
    assert service.distance == expected


def test_unknown_distance_falls_back_to_cosine():
    """An unrecognized distance string falls back to COSINE."""
    service = VectorDBService(
        client=None,
        collection_name="test",
        embedding_dim=384,
        distance="manhattan",
    )
    assert service.distance == qmodels.Distance.COSINE
