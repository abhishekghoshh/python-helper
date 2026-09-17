"""
Web Search tool — simulates web search results.

This is a **mock** tool that returns canned search results based on the
query. It does not make real API calls. This lets the agent loop be
demonstrated end-to-end without requiring a search API key or network
access.

In a real deployment you would replace this with a call to:
- SerpApi / Google Search API
- Bing Search API
- Tavoli / Exa
- Or a custom web scraper

The mock returns plausible results for common queries and a generic
"no results" for others.
"""

from __future__ import annotations

from typing import Any

from app.tools.base import Tool, ToolResult


# Canned knowledge base for the mock search
_KNOWLEDGE: dict[str, list[str]] = {
    "capital of france": [
        "Paris is the capital of France.",
        "Paris has been France's capital since the 10th century.",
    ],
    "who is elon musk": [
        "Elon Musk is the CEO of Tesla, SpaceX, and X (formerly Twitter).",
        "He is known for electric vehicles, space exploration, and social media.",
    ],
    "python programming language": [
        "Python is a high-level, general-purpose programming language.",
        "Created by Guido van Rossum and first released in 1991.",
        "Python emphasizes code readability with its notable use of whitespace.",
    ],
    "agentic ai": [
        "Agentic AI refers to AI systems that can autonomously plan, reason, "
        "and act using tools to achieve goals.",
        "An AI agent differs from a simple LLM application by having an agent loop, "
        "tool calling, and memory.",
    ],
    "vector database": [
        "A vector database stores and queries high-dimensional vector embeddings.",
        "Examples include Qdrant, Pinecone, Milvus, and Chroma.",
    ],
    "rag": [
        "RAG (Retrieval-Augmented Generation) combines a retriever with a generator.",
        "It retrieves relevant documents and uses them as context for LLM generation.",
    ],
    "machine learning": [
        "Machine learning is a subset of AI that builds systems that learn from data.",
        "Common types include supervised, unsupervised, and reinforcement learning.",
    ],
}


class WebSearchTool(Tool):
    """Simulated web search that returns canned results."""

    name = "web_search"
    description = (
        "Searches the web for current information. Returns a list of results "
        "with titles and snippets. Use this when the user asks about recent "
        "events, current facts, or information you are uncertain about."
    )
    category = "search"
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query string.",
            }
        },
        "required": ["query"],
    }

    async def execute(self, query: str, **kwargs: Any) -> ToolResult:
        query_lower = query.lower().strip()

        # Try exact match first, then substring match
        results: list[str] = []
        if query_lower in _KNOWLEDGE:
            results = _KNOWLEDGE[query_lower]
        else:
            for key, snippets in _KNOWLEDGE.items():
                if key in query_lower or query_lower in key:
                    results.extend(snippets)

        if not results:
            results = [
                f"No specific information found for '{query}'.",
                f"This is a simulated search result. In production, this would "
                f"call a real search API (SerpApi, Bing, Exa, etc.).",
            ]

        # Format as search results
        formatted = "\n".join(
            f"[{i + 1}] {snippet}" for i, snippet in enumerate(results)
        )
        return ToolResult(self.name, formatted)
