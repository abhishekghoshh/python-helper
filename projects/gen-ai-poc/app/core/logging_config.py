"""
Logging configuration — structured, configurable logging for the GenAI POC.

Configuration is driven by environment variables (via Settings):

- ``LOG_LEVEL``    — one of DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
- ``LOG_FORMAT``   — ``standard`` (human-readable) or ``json`` (machine-readable)
- ``LOG_FILE``     — optional file path for log output (default: stdout only)

Usage:

    >>> from app.core.logging_config import configure_logging
    >>> configure_logging()

Called automatically in the FastAPI ``lifespan`` handler.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """Emit log records as JSON lines — ideal for production and log aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Include extra fields if present
        for key, value in record.__dict__.items():
            if key not in {
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
                "taskName",
            }:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def _build_handlers() -> list[logging.Handler]:
    """Create handlers based on settings (stdout + optional file)."""
    handlers: list[logging.Handler] = []

    stream_handler = logging.StreamHandler(sys.stdout)
    handlers.append(stream_handler)

    if settings.log_file:
        file_handler = logging.FileHandler(settings.log_file)
        handlers.append(file_handler)

    return handlers


def _build_formatter() -> logging.Formatter:
    """Select the formatter based on the configured format."""
    if settings.log_format == "json":
        return JSONFormatter()
    return logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def configure_logging() -> None:
    """Configure root logger with the application's logging settings.

    Call once at application startup (typically in the FastAPI lifespan handler).
    Safe to call multiple times — it resets handlers each call.
    """
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    formatter = _build_formatter()
    handlers = _build_handlers()

    for handler in handlers:
        handler.setLevel(level)
        handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = handlers
