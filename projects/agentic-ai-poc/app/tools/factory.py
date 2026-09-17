"""
Tool factory — builds the default tool registry with all available tools.

This is where individual tools are instantiated and registered. The
agent receives a ``ToolRegistry`` from this factory.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.agents.types import HitlApprover
from app.tools.base import ToolRegistry
from app.tools.calculator import CalculatorTool
from app.tools.datetime_tool import DateTimeTool
from app.tools.file_reader import FileReaderTool
from app.tools.web_search import WebSearchTool
from app.rag.retriever import RAGRetrieverTool

logger = logging.getLogger(__name__)


def create_tool_registry(
    llm_service,
    allow_list: Optional[set[str]] = None,
    hitl_required_tools: Optional[set[str]] = None,
    data_dir: Optional[str] = None,
    approver: Optional[HitlApprover] = None,
) -> ToolRegistry:
    """Build a ToolRegistry with all default tools registered.

    Args:
        llm_service: The LLM service (needed by the RAG tool).
        allow_list: Set of allowed tool names (guardrail). None = all allowed.
        hitl_required_tools: Tool names that require human approval.
        data_dir: Base directory for the file_reader tool.
        approver: The human-in-the-loop approver (passed to tools that need it).

    Returns:
        A configured ``ToolRegistry``.
    """
    registry = ToolRegistry(allow_list=allow_list)

    registry.register(CalculatorTool())
    registry.register(DateTimeTool())
    registry.register(FileReaderTool(data_dir=data_dir))
    registry.register(WebSearchTool())

    # RAG tool depends on the LLM service for answer generation
    registry.register(RAGRetrieverTool(llm_service=llm_service))

    return registry
