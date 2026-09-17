"""
Central configuration management.

All environment-based settings live here, loaded via pydantic-settings.
This keeps secrets and toggles out of code and makes the application
configurable without changes to source.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Application ---
    app_name: str = "GenAI POC"
    app_version: str = "0.1.0"
    debug: bool = False

    # --- LLM ---
    llm_provider: str = "openai"  # "openai" or "openai-compatible"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-3.5-turbo"
    # "auto" = use mock LLM when no API key; "always" = always use mock;
    # "never" = require a real API key
    mock_llm_mode: str = "auto"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1024
    llm_top_p: float = 1.0
    llm_timeout: int = 30

    # --- Embeddings ---
    embedding_provider: str = "sentence-transformers"  # "sentence-transformers" or "openai"
    embedding_model: str = "all-MiniLM-L6-v2"  # local sentence-transformers model
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 384  # dimensionality of all-MiniLM-L6-v2 output

    # --- Vector Database ---
    qdrant_host: str = "http://localhost:6333"
    qdrant_collection: str = "genai-documents"
    qdrant_distance: str = "cosine"  # "cosine", "euclid", or "dot"

    # --- Logging ---
    log_level: str = "INFO"
    log_format: str = "standard"  # "standard" or "json"
    log_file: str | None = None

    # --- RAG ---
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 100
    rag_top_k: int = 5

    # --- Derived ---
    @property
    def qdrant_distance_mode(self) -> str:
        """Map config string to Qdrant Distance enum value."""
        mapping: dict[str, str] = {"cosine": "Cosine", "euclid": "Euclid", "dot": "Dot"}
        return mapping.get(self.qdrant_distance, "Cosine")


settings = Settings()
