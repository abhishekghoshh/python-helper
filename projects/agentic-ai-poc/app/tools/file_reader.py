"""
File Reader tool — reads files from a restricted data directory.

Security boundary: only files within ``data/`` (the project's data directory)
can be read. Path traversal (``../``) is blocked.

This demonstrates the principle:
    LLM decides WHAT to read.
    Application decides WHAT IS ALLOWED.
"""

from __future__ import annotations

import os
from typing import Any

from app.tools.base import Tool, ToolResult


class FileReaderTool(Tool):
    """Reads the contents of a file from the allowed data directory."""

    name = "file_reader"
    description = (
        "Reads the contents of a file and returns its text. "
        "Only files within the project's data directory can be read. "
        "Provide a path relative to the data directory, e.g. 'notes/example.txt'."
    )
    category = "utility"
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file, relative to the data directory.",
            }
        },
        "required": ["path"],
    }

    def __init__(self, data_dir: str | None = None) -> None:
        if data_dir is None:
            # Default to <project_root>/data
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.dirname(__file__)))), "data")
        self._data_dir = os.path.realpath(data_dir)

    async def execute(self, path: str, **kwargs: Any) -> ToolResult:
        # Block path traversal
        safe_path = os.path.realpath(os.path.join(self._data_dir, path))
        if not safe_path.startswith(self._data_dir + os.sep) and safe_path != self._data_dir:
            return ToolResult(
                self.name, "",
                success=False,
                error=f"Access denied: path must be within the data directory. "
                      f"Resolved path '{safe_path}' is outside '{self._data_dir}'.",
            )
        if not os.path.isfile(safe_path):
            return ToolResult(
                self.name, "",
                success=False,
                error=f"File not found: {path}",
            )
        try:
            with open(safe_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Truncate very large files
            max_read = 100_000
            if len(content) > max_read:
                content = content[:max_read] + "\n... [truncated]"
            return ToolResult(self.name, content)
        except Exception as e:
            return ToolResult(
                self.name, "",
                success=False,
                error=f"{type(e).__name__}: {e}",
            )
