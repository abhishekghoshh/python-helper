"""Application configuration with environment-based settings and logging setup."""

import logging
import sys
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    collection_name: str = "demo"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    qdrant_distance: str = "cosine"
    log_level: str = "INFO"
    log_format: str = "standard"  # "standard" or "json"
    log_file: Optional[str] = None  # optional file path for file logging

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON strings."""

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime, timezone

        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def setup_logging() -> None:
    """Configure root logging based on settings.

    Supports two formats:
    - ``standard``: ``%(asctime)s [%(levelname)s] %(name)s: %(message)s``
    - ``json``:     single-line JSON via :class:`JsonFormatter`

    When ``log_file`` is set, a file handler is added in addition to stdout.
    """
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    if settings.log_format == "json":
        formatter: logging.Formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if settings.log_file:
        handlers.append(logging.FileHandler(settings.log_file))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    for handler in handlers:
        handler.setFormatter(formatter)
        handler.setLevel(level)
        root.addHandler(handler)

    # Reduce verbosity of noisy third-party loggers
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("qdrant.client").setLevel(level)
