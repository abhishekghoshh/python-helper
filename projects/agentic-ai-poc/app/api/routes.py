"""
API routes for the Agentic AI POC.

Endpoints:
- POST /chat       — Run the agent on a message (returns final answer)
- POST /chat/stream — Run the agent with streaming (SSE)
- POST /run        — Run the agent with full trace and result
- GET  /tools      — List available tools and their schemas
- POST /rag/ingest — Ingest documents for the RAG tool
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_agent
from app.agents.react_agent import ReActAgent
from app.core.config import settings
from app.models.schemas import (
    AgentRunResponse,
    ChatRequest,
    ChatResponse,
    RagIngestRequest,
    ToolInfo,
)
from app.observability.trace import EventType

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=AgentRunResponse)
async def chat(request: ChatRequest, agent: ReActAgent = Depends(get_agent)):
    """Run the agent on a user message and return the final answer.

    This is the simplest entry point — send a message, get the agent's
    complete response including the trace of what it did.
    """
    result = await agent.run(request.message)
    return AgentRunResponse(
        success=result.success,
        answer=result.answer,
        final_state=result.final_state.value,
        total_steps=result.total_steps,
        total_tool_calls=result.total_tool_calls,
        total_llm_calls=result.total_llm_calls,
        trace=[e.to_dict() for e in agent.trace.events] if settings.agent_trace_enabled else [],
        error=result.error,
    )


@router.post("/run")
async def run_agent(
    request: ChatRequest,
    agent: ReActAgent = Depends(get_agent),
    max_iterations: int = Query(default=10, ge=1, le=50),
):
    """Run the agent with custom parameters and full observability.

    Unlike ``/chat``, this endpoint:
    - Accepts a custom ``max_iterations`` override
    - Returns the full execution trace
    - Lets you restrict to specific tools
    """
    # Override config from request
    if max_iterations != agent.config.max_iterations:
        agent.config.max_iterations = max_iterations
    if request.max_iterations is not None:
        agent.config.max_iterations = request.max_iterations
    if request.tools:
        # Filter the tool registry to only the requested tools
        agent.tools._allow_list = set(request.tools)

    result = await agent.run(request.message, conversation_id=request.conversation_id)
    return AgentRunResponse(
        success=result.success,
        answer=result.answer,
        final_state=result.final_state.value,
        total_steps=result.total_steps,
        total_tool_calls=result.total_tool_calls,
        total_llm_calls=result.total_llm_calls,
        trace=[e.to_dict() for e in agent.trace.events] if settings.agent_trace_enabled else [],
        error=result.error,
    )


@router.get("/tools")
def list_tools(agent: ReActAgent = Depends(get_agent)):
    """List all available tools with their descriptions and parameters."""
    tools_info = agent.tools.infos()
    return {
        "tools": tools_info,
        "allow_list": list(agent.config.tool_allow_list) if agent.config.tool_allow_list else "all",
        "total": len(tools_info),
    }


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, agent: ReActAgent = Depends(get_agent)):
    """Run the agent with streaming output (Server-Sent Events).

    Yields ``ChatResponse`` events of these types:
    - ``start`` — agent begins
    - ``tool_call`` — the LLM chose a tool (name + arguments)
    - ``tool_result`` — a tool finished (name + success + execution time)
    - ``end`` — final answer (or error)

    Tool-call and tool-result events are derived from the agent's execution
    trace. (Per-token streaming requires a streaming LLM backend, which the
    mock mode does not provide.)
    """

    async def event_stream():
        yield f"data: {ChatResponse(type='start', content='Agent starting...').model_dump_json()}\n\n"

        result = await agent.run(request.message)

        # Replay the trace as SSE events so a client can follow each tool decision.
        for event in agent.trace.events:
            if event.event_type == EventType.TOOL_CALL:
                yield f"data: {ChatResponse(
                    type='tool_call',
                    tool_call={
                        'name': event.data.get('tool_name'),
                        'arguments': event.data.get('arguments'),
                    },
                ).model_dump_json()}\n\n"
            elif event.event_type == EventType.TOOL_RESULT:
                yield f"data: {ChatResponse(
                    type='tool_result',
                    tool_result={
                        'tool_name': event.data.get('tool_name'),
                        'success': event.data.get('success'),
                        'execution_time': event.data.get('execution_time'),
                    },
                ).model_dump_json()}\n\n"

        if result.error:
            yield f"data: {ChatResponse(type='end', error=result.error).model_dump_json()}\n\n"
        else:
            yield f"data: {ChatResponse(type='end', answer=result.answer, content=result.answer).model_dump_json()}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/rag/ingest")
async def ingest_documents(
    request: RagIngestRequest,
    agent: ReActAgent = Depends(get_agent),
):
    """Ingest documents into the vector database for the RAG tool.

    This is a setup endpoint — the agent calls the RAG tool at runtime,
    but someone needs to populate the vector DB first.
    """
    from app.rag.retriever import RAGRetrieverTool

    documents = request.documents
    rag_tool = None
    for tool in agent.tools.list():
        if isinstance(tool, RAGRetrieverTool):
            rag_tool = tool
            break

    if rag_tool is None:
        raise HTTPException(status_code=500, detail="RAG tool not available")

    summary = await rag_tool.ingest([d.content for d in documents], [d.id for d in documents])
    return {"message": summary}
