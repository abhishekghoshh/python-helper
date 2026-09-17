# Agentic AI POC — Learning Laboratory

An hands-on **Agentic AI learning laboratory** — a Python project that lets you
**understand, implement, experiment with, and interview about AI agents**.

> **Transitioned from:** A GenAI/RAG pipeline (fixed retrieve→generate workflow)
> **To:** A full agentic system with an explicit agent loop, tool calling,
> planning, memory, RAG-as-a-tool, multi-agent patterns, guardrails,
> evaluation, observability, experiments, and interview preparation.

---

## What is this?

This project demonstrates the difference between:

- **LLM Application** — prompt → LLM → response (one shot)
- **LLM Workflow** — a fixed sequence of steps (e.g. retrieve → generate)
- **AI Agent** — observe → reason → plan → act → observe → … → answer (a loop)

The core implementation is an explicit **ReAct agent loop** — no framework
hides the mechanics. You can read every line of the loop, every tool, and
every memory component.

## Quick Start

### Option 1: Run with the Mock LLM (no API key needed)

```bash
# Clone and enter the project
cd agentic-ai-poc

# Create a virtual environment and install
python3 -m venv .venv && source .venv/bin/activate
pip install fastapi "uvicorn[standard]" pydantic pydantic-settings openai numpy pytest pytest-asyncio httpx

# Run the demo CLI (uses a mock LLM — no API key required)
python -m app.cli

# Or run the API server
.venv/bin/python -m uvicorn app.main:app --reload
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Option 2: Run with a real LLM (OpenAI)

```bash
cp .env.example .env
# Edit .env: set AGENT_SIMULATED_MODE=false and LLM_API_KEY=your-key
.venv/bin/python -m uvicorn app.main:app --reload
```

### Option 3: Run with Docker

```bash
docker-compose up --build
# API: http://localhost:8000  |  Docs: http://localhost:8001
```

### Run Tests

```bash
.venv/bin/python -m pytest tests/ -v
```

## Run the Tests

```bash
.venv/bin/python -m pytest tests/ -v
```

## Documentation

Full documentation is available via MkDocs:

```bash
pip install mkdocs mkdocs-material mkdocstrings[python]
.venv/bin/python -m mkdocs serve
# Docs: http://localhost:8000
```

Key documentation sections:

- **[Project Analysis](docs/project/project-analysis.md)** — understanding the existing code
- **[Agentic AI Fundamentals](docs/agentic-ai/fundamentals.md)** — what agents are and aren't
- **[Agent Loop](docs/architecture/agent-loop.md)** — the ReAct pattern, step by step
- **[Tool Calling](docs/architecture/tool-calling.md)** — how the LLM chooses tools
- **[Interview Preparation](docs/interview-preparation/beginner.md)** — Q&As for technical interviews

## Project Structure

```
agentic-ai-poc/
├── app/
│   ├── main.py                    # FastAPI application
│   ├── core/
│   │   └── config.py              # Environment-based settings
│   ├── llm/
│   │   ├── service.py             # OpenAI-compatible LLM service
│   │   └── mock.py                # Mock LLM (offline, for testing/demos)
│   ├── tools/
│   │   ├── base.py                # Tool abstract base + ToolRegistry
│   │   ├── calculator.py          # Math calculator tool
│   │   ├── datetime_tool.py       # Current date/time tool
│   │   ├── file_reader.py         # File reader tool (sandboxed)
│   │   ├── web_search.py          # Web search tool (mock)
│   │   └── factory.py             # Tool registry builder
│   ├── rag/
│   │   ├── chunking.py            # Document chunking
│   │   └── retriever.py           # RAG as a tool
│   ├── agents/
│   │   ├── base.py                # BaseAgent (guardrails, state, tracing)
│   │   ├── react_agent.py         # ReAct agent loop
│   │   └── types.py               # AgentState, HitlApprover
│   ├── memory/
│   │   ├── base.py                # Memory interfaces
│   │   ├── short_term.py          # Conversation buffer
│   │   ├── working.py             # Working memory (scratchpad)
│   │   └── long_term.py           # Persistent SQLite memory
│   ├── models/
│   │   └── schemas.py             # Pydantic models
│   ├── observability/
│   │   └── trace.py               # Execution tracing
│   ├── services/
│   │   ├── embedding.py           # Embedding service
│   │   └── vector_db.py           # Qdrant vector DB service
│   ├── api/
│   │   ├── routes.py              # API endpoints
│   │   └── dependencies.py        # DI factory
│   └── cli.py                     # Interactive CLI demo
├── data/                          # Sample files for file_reader
├── tests/                         # Unit + integration tests
├── docs/                          # MkDocs documentation
├── Dockerfile
├── Dockerfile.docs
├── docker-compose.yml
├── mkdocs.yml
├── pyproject.toml
└── .env.example
```

## Key Concepts Demonstrated

| Concept | Where |
|---------|-------|
| Agent loop (ReAct) | `app/agents/react_agent.py` |
| Tool calling | `app/tools/base.py`, `app/llm/service.py` |
| Guardrails (allow-list, timeout, approval) | `app/agents/base.py` |
| Short-term memory | `app/memory/short_term.py` |
| Working memory | `app/memory/working.py` |
| Long-term memory | `app/memory/long_term.py` |
| RAG as a tool | `app/rag/retriever.py` |
| State machine | `app/agents/types.py` |
| Observability | `app/observability/trace.py` |
| Human-in-the-loop | `app/agents/types.py` (HitlApprover) |

## License

Learning reference — use freely to study and teach Agentic AI concepts.
