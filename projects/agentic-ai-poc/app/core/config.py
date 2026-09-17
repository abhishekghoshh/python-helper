"""
Central configuration management for the Agentic AI POC.

All environment-based settings live here, loaded via pydantic-settings.
This keeps secrets, toggles, and limits out of code and makes the
application configurable without changes to source.

Every agent-specific guardrail (max iterations, timeout, tool allow-list)
is a setting here so it can be tuned without code changes.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Application ---
    app_name: str = "Agentic AI POC"
    app_version: str = "0.1.0"
    debug: bool = False

    # --- LLM ---
    llm_provider: str = "openai"  # "openai" or "openai-compatible"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096
    llm_top_p: float = 1.0
    llm_timeout: int = 60

    # --- Agent Settings ---
    # Maximum agent loop iterations before forced termination
    agent_max_iterations: int = 10
    # Delay (seconds) between agent loop iterations (for rate limiting)
    agent_iteration_delay: float = 0.0
    # Enable reasoning trace logging
    agent_trace_enabled: bool = True
    # When True, use a Mock LLM (no API key needed) — useful for demos/tests
    agent_simulated_mode: bool = True

    # --- Memory Settings ---
    memory_max_history_chars: int = 8000
    memory_lt_db_path: str = "data/memory.db"

    # --- Embedding / RAG ---
    embedding_provider: str = "sentence-transformers"  # "sentence-transformers" (local) or "openai" (cloud)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 384
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "agentic-docs"
    rag_top_k: int = 5
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 100

    # --- Human-in-the-Loop ---
    hitl_enabled: bool = False
    hitl_required_tools: str = "execute_command,write_file"

    # --- Guardrails ---
    tool_timeout_seconds: float = 30.0
    tool_allow_list: str = "calculator,datetime,file_reader,search,rag_query"

    @property
    def tool_allowlist_set(self) -> set[str]:
        """Parse the comma-separated allow-list into a set of tool names."""
        allowed = self.tool_allow_list.strip()
        if allowed.lower() == "all":
            return set()  # empty set = no restriction
        return {name.strip() for name in allowed.split(",") if name.strip()}

    @property
    def hitl_required_tools_set(self) -> set[str]:
        return {name.strip() for name in self.hitl_required_tools.split(",") if name.strip()}

    @property
    def use_mock_llm(self) -> bool:
        """Whether to use the mock LLM (simulated mode) instead of a real LLM API."""
        return self.agent_simulated_mode


# Module-level singleton
settings = Settings()
