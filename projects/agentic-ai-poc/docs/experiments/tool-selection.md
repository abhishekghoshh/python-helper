# Experiment: Tool Selection

**Category:** Tool Calling  
**Difficulty:** Beginner  
**Estimated time:** 5 minutes

---

## Objective

Observe how the LLM (mocked) selects the appropriate tool based on the
query, and how the tool's arguments are generated.

---

## Hypothesis

The agent will correctly map:

| Query pattern | Expected tool |
|---------------|--------------|
| Contains numbers + operators ("2 + 2") | `calculator` |
| Contains "time", "date", "now" | `datetime_now` |
| Contains "file", "read" | `file_reader` |
| Contains "what is", "capital" | `web_search` / `rag_query` |
| No matching tool needed | Direct answer (no tool) |

---

## Architecture

```mermaid
flowchart TB
    UQ["User Query"] --> LLM["LLM.generate(messages, tools)"]
    LLM --> INS["LLM inspects:<br/>— tool descriptions (name, params, purpose)<br/>— current user query<br/>— conversation context"]
    INS --> OUT["LLM outputs:<br/>tool_call[name=\"calculator\", args={\"expression\": \"...\"}]<br/>(or a text response if no tool fits)"]
    OUT --> EXEC["Agent executes the tool<br/>(or returns text as final answer)"]
```

The tool **description** and **parameter schema** are what the LLM uses to
decide. Good descriptions = better selection.

Source: `app/tools/base.py` (app/tools/base.py),
`app/llm/mock.py` (app/llm/mock.py)

---

## Implementation

The mock LLM's decision logic (simplified):

```python
def _decide_tool_call(self, query: str, tools: list[ToolDefinition]) -> LLMResponse:
    available = {t.function.name for t in tools}

    # Math → calculator
    if self._detect_math(query) and "calculator" in available:
        expr = self._extract_math_expression(query)
        return self._make_tool_call("calculator", {"expression": expr})

    # Time/date → datetime_now
    if any(kw in query for kw in ["time", "date", "today"]) and "datetime_now" in available:
        return self._make_tool_call("datetime_now", {})

    # File → file_reader
    if any(kw in query for kw in ["file", "read"]) and "file_reader" in available:
        return self._make_tool_call("file_reader", {"path": "data/sample_knowledge.md"})

    # Factual → web_search or rag_query
    if self._is_factual_query(query):
        if "rag_query" in available:
            return self._make_tool_call("rag_query", {"question": query})
        if "web_search" in available:
            return self._make_tool_call("web_search", {"query": query})

    return self._make_text_response("I can't help with that.")
```

---

## Input

```bash
python -m app.cli
```

Try:

```
What is 15 * 24?
What time is it now in New York?
Read the file sample_knowledge.md
Who won the latest election?
Say hello
```

---

## Execution

```bash
python -m app.cli
> What time is it now in New York?
```

### Expected trace

```
[0.002s] llm_call | step=1 | tools=4
[0.003s] tool_call | tool=datetime_now | args={"timezone": "America/New_York"}
[0.004s] tool_result | tool=datetime_now | success=True | result=2026-09-05 14:30:00
[0.005s] llm_call | step=2 | tools=4
```

---

## Result

| Query | Tool selected | Arguments | Correct? |
|-------|---------------|-----------|----------|
| What is 15 * 24? | calculator | `{"expression": "15 * 24"}` | ✅ |
| What time is it now? | datetime_now | `{}` | ✅ |
| Read sample_knowledge.md | file_reader | `{"path": "data/sample_knowledge.md"}` | ✅ |
| Who won the latest election? | web_search | `{"query": "..."}` | ✅ |
| Say hello | (none) | — | ✅ |

---

## Observations

1. **Tool descriptions matter** — clear, specific descriptions help the LLM
   pick the right tool.
2. **The mock uses keyword matching** — a real LLM uses semantic understanding.
3. **Some ambiguity is inevitable** — "What is X?" could need web_search,
   rag_query, or a calculator depending on X.
4. **The schema constrains arguments** — the LLM must provide the right
   argument names as defined in the tool's JSON Schema.

---

## Trade-offs

| Approach | Pros | Cons |
|----------|------|------|
| **Keyword matching** (mock) | No API key, deterministic, fast | Not general-purpose, brittle |
| **Real LLM** | General-purpose, understands intent | Requires API key, costs money, non-deterministic |
| **Rule-based selection** | Deterministic, fast, controllable | Hard to maintain as tools grow |
| **LLM-based selection** | Adapts to new queries, handles ambiguity | Cost, latency, potential for wrong selection |

---

## Variations to try

1. **Remove a tool** — If `calculator` is removed from the registry, math
   queries should fall back to a direct answer (the mock can't compute).
2. **Add a confusingly-named tool** — e.g., `query` (ambiguous). See if it
   affects selection.
3. **Change tool descriptions** — Make them vague or misleading. Observe
   how selection changes.

---

## Key takeaway

Tool selection is one of the hardest parts of agent design. The LLM must
choose from available tools based on descriptions and schemas. Good tool
design (clear names, descriptions, and schemas) is essential for reliable
selection.
