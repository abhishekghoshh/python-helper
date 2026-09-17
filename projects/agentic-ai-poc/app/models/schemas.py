"""
Pydantic data models (DTOs) for the Agentic AI POC.

These schemas define every request/response shape, internal message object,
tool definition, agent state, and trace that flows through the system.

The message model here mirrors the OpenAI chat format so that switching
between a real OpenAI LLM service and a mock LLM service is transparent:
both produce the same ``ConversationMessage`` list.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Message roles
# ---------------------------------------------------------------------------


class Role(str, Enum):
    """Roles in a conversation / agent context window."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ConversationMessage(BaseModel):
    """A single message in the conversation history.

    This is the canonical message type used internally by the agent loop.
    It maps cleanly to OpenAI's chat message format:

    - ``system``     → system instructions
    - ``user``       → user input (can be a string or structured content)
    - ``assistant``  → the LLM's response; may include ``tool_calls``
    - ``tool``       → the result of a tool call, linked by ``tool_call_id``
    """

    role: Role
    content: Optional[str] = None
    # Only populated for assistant messages when the LLM makes tool calls.
    tool_calls: Optional[list["ToolCall"]] = None
    # Only populated for tool messages — the ID of the call this result answers.
    tool_call_id: Optional[str] = None
    # The name of the tool that produced this result (for traceability).
    tool_name: Optional[str] = None

    model_config = {"use_enum_values": False, "populate_by_name": True}


# ---------------------------------------------------------------------------
# Tool calling types
# ---------------------------------------------------------------------------


class FunctionDef(BaseModel):
    """Describes a callable function the LLM can invoke."""

    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)  # JSON Schema


class ToolDefinition(BaseModel):
    """A tool definition in the OpenAI tools format: {"type": "function", "function": ...}."""

    type: Literal["function"] = "function"
    function: FunctionDef

    def to_openai(self) -> dict[str, Any]:
        """Convert to the dict format expected by the OpenAI SDK."""
        return {"type": self.type, "function": self.function.model_dump()}


class ToolCall(BaseModel):
    """A single tool invocation requested by the LLM.

    Mirrors OpenAI's ``ChatCompletionMessageToolCall``: an opaque ``id``
    plus a ``function`` with name and arguments (as a JSON string).
    """

    id: str
    type: str = "function"
    function: "ToolCallFunction" = Field(..., alias="function")

    model_config = {"populate_by_name": True}


class ToolCallFunction(BaseModel):
    """The function payload inside a ``ToolCall``."""

    name: str
    arguments: str  # JSON-encoded string (matches the OpenAI wire format)


class ToolExecutionResult(BaseModel):
    """Result of executing a tool — fed back to the LLM as a ``tool`` message."""

    tool_call_id: str
    tool_name: str
    success: bool
    content: str  # serialised result (string) or error message
    error: Optional[str] = None

    def to_message(self) -> ConversationMessage:
        """Convert to a conversation message for the next LLM call.

        When a tool fails with an empty result body, the error text is
        surfaced into the message content so the LLM (and the mock LLM's
        synthesis phase) can react to it. Without this, a failed tool
        produces an empty ``tool`` message that the agent mistakes for an
        unprocessed call and re-invokes the same failing tool forever.
        """
        content = self.content
        if not content and self.error:
            content = self.error
        return ConversationMessage(
            role=Role.TOOL,
            content=content,
            tool_call_id=self.tool_call_id,
            tool_name=self.tool_name,
        )


# ---------------------------------------------------------------------------
# LLM response
# ---------------------------------------------------------------------------


class LLMResponse(BaseModel):
    """Unified response from any LLM service.

    Either ``content`` is set (text response) or ``tool_calls`` is set
    (the LLM wants to invoke tools). Both can be set if the LLM wants to
    respond with text AND call a tool in the same turn.
    """

    id: str = Field(default_factory=lambda: "")
    model: str = ""
    content: Optional[str] = None
    tool_calls: Optional[list[ToolCall]] = None
    finish_reason: Optional[str] = None
    usage: Optional[dict[str, Any]] = None  # {prompt_tokens, completion_tokens, total_tokens}

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


# ---------------------------------------------------------------------------
# Agent state & result types
# ---------------------------------------------------------------------------


class AgentState(str, Enum):
    """Lifecycle states of an agent run.

    Models the agent as an explicit state machine. Each transition
    is observable and traceable for debugging and learning.
    """

    IDLE = "IDLE"  # Agent created, not yet running
    RUNNING = "RUNNING"  # Active in the loop
    THINKING = "THINKING"  # LLM is reasoning / deciding
    TOOL_CALLING = "TOOL_CALLING"  # About to execute tools
    OBSERVING = "OBSERVING"  # Processing tool results
    PLANNING = "PLANNING"  # Decomposing task into sub-steps
    REFLECTING = "REFLECTING"  # Self-critique / reviewing output
    COMPLETED = "COMPLETED"  # Finished successfully
    FAILED = "FAILED"  # Terminated due to error
    MAX_ITERATIONS = "MAX_ITERATIONS"  # Hit the iteration cap
    STOPPED = "STOPPED"  # Manually stopped


class AgentStep(BaseModel):
    """One iteration of the agent loop — a single observe→reason→act cycle."""

    step_number: int
    state: AgentState
    observation: Optional[str] = None  # what the agent saw
    reasoning: Optional[str] = None  # the LLM's reasoning/trace
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_results: list[ToolExecutionResult] = Field(default_factory=list)
    llm_response: Optional[LLMResponse] = None
    timestamp: str


class AgentConfig(BaseModel):
    """Configuration for a specific agent run."""

    max_iterations: int = 10
    max_tool_calls_per_step: int = 5
    max_output_tokens: Optional[int] = None
    iteration_delay: float = 0.0
    tool_timeout: float = 30.0
    model: Optional[str] = None
    temperature: Optional[float] = None
    trace_enabled: bool = True
    tool_allow_list: Optional[set[str]] = None
    human_in_the_loop: bool = False
    required_approval_tools: Optional[set[str]] = None


class AgentResult(BaseModel):
    """Final output of an agent run."""

    success: bool
    answer: Optional[str] = None
    final_state: AgentState
    total_steps: int
    total_tool_calls: int
    total_llm_calls: int
    trace: list[AgentStep] = Field(default_factory=list)
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# API request / response models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Request to run the agent on a user message."""

    message: str
    conversation_id: Optional[str] = None
    max_iterations: Optional[int] = None
    tools: Optional[list[str]] = None  # restrict to specific tool names
    stream: bool = False


class ChatResponse(BaseModel):
    """A response chunk sent back to the client (SSE-friendly)."""

    type: Literal["start", "token", "tool_call", "tool_result", "step", "end"]
    content: Optional[str] = None
    tool_call: Optional[dict[str, Any]] = None
    tool_result: Optional[dict[str, Any]] = None
    step: Optional[AgentStep] = None
    answer: Optional[str] = None
    error: Optional[str] = None


class AgentRunResponse(BaseModel):
    """Full agent run result (non-streaming)."""

    success: bool
    answer: Optional[str]
    final_state: str
    total_steps: int
    total_tool_calls: int
    total_llm_calls: int
    trace: list[dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


class ToolInfo(BaseModel):
    """Public info about a registered tool."""

    name: str
    description: str
    parameters_schema: dict[str, Any] = Field(default_factory=dict)
    category: str = "general"


class MemoryEntry(BaseModel):
    """A single entry in short-term / working memory."""

    role: Role
    content: str
    timestamp: Optional[str] = None


# ---------------------------------------------------------------------------
# Tool definitions for the agent
# ---------------------------------------------------------------------------


def get_default_tool_definitions() -> list[ToolDefinition]:
    """Return the OpenAI-format tool definitions for all default tools.

    Kept as a function (not a constant) so the list is fresh each call
    and cannot be accidentally mutated by callers.
    """
    return [
        ToolDefinition(
            type="function",
            function=FunctionDef(
                name="calculator",
                description=(
                    "A simple calculator that evaluates a math expression and "
                    "returns the numeric result. Use this for arithmetic, "
                    "unit conversions, or any numerical computation."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "A mathematical expression to evaluate, e.g. '2 + 2 * 10'.",
                        }
                    },
                    "required": ["expression"],
                },
            ),
        ),
        ToolDefinition(
            type="function",
            function=FunctionDef(
                name="datetime_now",
                description=(
                    "Returns the current date and time, optionally in a "
                    "specific timezone or format. Useful when the user asks "
                    "about the current time, date, or day of week."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "timezone": {
                            "type": "string",
                            "description": "Timezone name, e.g. 'UTC', 'America/New_York'. Defaults to UTC.",
                        },
                        "format": {
                            "type": "string",
                            "description": "strftime format string, e.g. '%Y-%m-%d %H:%M:%S'. Defaults to ISO 8601.",
                        },
                    },
                    "required": [],
                },
            ),
        ),
        ToolDefinition(
            type="function",
            function=FunctionDef(
                name="file_reader",
                description=(
                    "Reads the contents of a file at the given path and returns "
                    "its text. Only files within the allowed data directory can "
                    "be read."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The file path to read (relative to the project data directory).",
                        }
                    },
                    "required": ["path"],
                },
            ),
        ),
        ToolDefinition(
            type="function",
            function=FunctionDef(
                name="web_search",
                description=(
                    "Searches the web for current information on a topic. "
                    "Returns a list of results with titles, snippets, and URLs. "
                    "Use this when the user asks about recent events, news, "
                    "or factual information you are not certain about."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query string.",
                        }
                    },
                    "required": ["query"],
                },
            ),
        ),
        ToolDefinition(
            type="function",
            function=FunctionDef(
                name="rag_query",
                description=(
                    "Retrieves relevant documents from a vector database (RAG) "
                    " and generates a grounded answer. Use this when the user "
                    "asks about information that might be in the knowledge base, "
                    "documentation, or any ingested documents."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The question or query to search the knowledge base with.",
                        }
                    },
                    "required": ["question"],
                },
            ),
        ),
    ]


# ---------------------------------------------------------------------------
# RAG schemas
# ---------------------------------------------------------------------------


class Document(BaseModel):
    """A document to be indexed for RAG."""

    id: Optional[str] = None
    content: str = Field(..., min_length=1, description="Full text content")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata")


class Chunk(BaseModel):
    """A piece of a document after chunking."""

    id: str
    text: str
    document_id: str
    chunk_index: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    """Result of ingesting documents."""

    documents_processed: int
    chunks_created: int
    collection: str


class RagIngestRequest(BaseModel):
    """Request body for ingesting documents into the RAG knowledge base."""

    documents: list[Document] = Field(..., min_length=1, description="Documents to chunk and store")


class SearchHit(BaseModel):
    """A single search result."""

    id: str
    score: float
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Response for document search."""

    query: str
    hits: list[SearchHit]
    collection: str


class RAGResponse(BaseModel):
    """Response containing the RAG-generated answer."""

    answer: str
    sources: list[SearchHit] = Field(default_factory=list)
    context: str = ""


class RAGQueryRequest(BaseModel):
    """Request body for a RAG tool query."""

    question: str
    top_k: Optional[int] = None
