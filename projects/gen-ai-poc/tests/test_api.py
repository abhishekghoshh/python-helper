"""Tests for API endpoints using TestClient (no external services needed)."""


class TestHealthEndpoint:
    def test_health_check(self, api_client):
        response = api_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestLLMEndpoint:
    def test_generate_rejects_empty_messages(self, api_client):
        response = api_client.post("/api/v1/llm/generate", json={"messages": []})
        # Pydantic validation should reject empty list (min_length=1)
        assert response.status_code == 422 or response.status_code == 400

    def test_generate_validates_temperature_range(self, api_client):
        response = api_client.post(
            "/api/v1/llm/generate",
            json={
                "messages": [{"role": "user", "content": "Hi"}],
                "temperature": 5.0,  # Out of range [0, 2]
            },
        )
        assert response.status_code == 422

    def test_generate_validates_top_p_range(self, api_client):
        response = api_client.post(
            "/api/v1/llm/generate",
            json={
                "messages": [{"role": "user", "content": "Hi"}],
                "top_p": 2.0,  # Out of range [0, 1]
            },
        )
        assert response.status_code == 422

    def test_list_models(self, api_client):
        response = api_client.get("/api/v1/llm/models")
        assert response.status_code == 200
        data = response.json()
        assert "llm_model" in data
        assert "embedding_model" in data
        assert "embedding_dimensions" in data


class TestEmbeddingsEndpoint:
    def test_similarity_endpoint(self, api_client):
        response = api_client.post(
            "/api/v1/embeddings/similarity",
            json={
                "text_a": "The cat sat on the mat.",
                "text_b": "A feline rested on a rug.",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "cosine" in data
        assert "euclidean" in data
        assert "dot_product" in data
        # Similar texts should have positive cosine similarity
        assert data["cosine"] > 0.0

    def test_similarity_dissimilar(self, api_client):
        response = api_client.post(
            "/api/v1/embeddings/similarity",
            json={
                "text_a": "Machine learning algorithms",
                "text_b": "Cooking recipes and ingredients",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["cosine"] < 0.5  # Should be relatively dissimilar

    def test_generate_requires_text(self, api_client):
        response = api_client.post("/api/v1/embeddings/generate", json={"text": ""})
        assert response.status_code == 422


class TestRAGDemoEndpoint:
    def test_demo_requires_question(self, api_client):
        response = api_client.get("/api/v1/rag/demo")
        assert response.status_code == 422

    def test_demo_without_documents(self, api_client):
        """Demo endpoint should handle empty vector DB gracefully."""
        response = api_client.get(
            "/api/v1/rag/demo",
            params={"question": "What is AI?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["question"] == "What is AI?"
        assert "retrieved_chunks" in data
        assert "context" in data
        assert "prompt" in data
        assert len(data["retrieved_chunks"]) == 0  # No docs ingested
        assert data["context"] == ""

    def test_demo_with_invalid_params(self, api_client):
        response = api_client.get(
            "/api/v1/rag/demo",
            params={"question": "test", "top_k": 0},  # top_k must be >= 1
        )
        assert response.status_code == 422
