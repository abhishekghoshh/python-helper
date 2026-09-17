# LLM App vs Workflow vs Agent vs Multi-Agent

> **Quick reference** — which category does your system fall into?

---

## The Spectrum

```mermaid
flowchart TD
    LLMApp["🟢 LLM Application\n(prompt → response)\nNo tools, no loop"]
    LLMWorkflow["🟡 LLM Workflow\n(fixed multi-step pipeline)\nApp decides the steps"]
    ToolApp["🟡 Tool-Calling App\n(LLM calls tools, single pass)\nNo feedback loop"]
    SingleAgent["🟠 Single AI Agent\n(observe→reason→act→loop)\nLLM directs the flow"]
    MultiAgent["🔴 Multi-Agent System\n(supervisor + workers)\nMultiple autonomous loops"]
    
    LLMApp -->|"more autonomy"| LLMWorkflow
    LLMWorkflow -->|"adds tool calling"| ToolApp
    ToolApp -->|"adds feedback loop"| SingleAgent
    SingleAgent -->|"adds collaboration"| MultiAgent
```

---

## 1. LLM Application

**One-shot prompt → response. No loop, no tools, no memory.**

```mermaid
flowchart LR
    U["👤 User"] -->|"prompt"| P["📝 Prompt"]
    P -->|"context"| L["🧠 LLM"]
    L -->|"completion"| R["💬 Response"]
```

- **Single LLM call** — one round-trip, no feedback
- **No tools** — the LLM cannot interact with the outside world
- **No memory** — each request is independent, no history retained
- **Deterministic** within LLM stochasticity — no branching logic

**Examples:** Chatbot, text summarizer, code generator.

---

## 2. LLM Workflow

**Fixed, pre-defined sequence of steps. The application code decides the flow.**

```mermaid
flowchart LR
    U["👤 User"] -->|"query"| S1["📥 Step 1: Retrieve\n(fixed logic)"]
    S1 -->|"documents"| S2["🔄 Step 2: Process\n(fixed logic)"]
    S2 -->|"context"| S3["🧠 Step 3: Generate\n(LLM call)"]
    S3 -->|"answer"| R["💬 Response"]
```

- Steps are **hard-coded** — the application decides the flow, not the LLM
- **No adaptivity** — same sequence runs every time for the same task type
- May or may not use tools — the workflow is predetermined

**Example:** RAG pipeline — `query → vector_search → LLM(prompt+context) → answer`.

---

## 3. Tool-Calling Application

**The LLM can call tools, but in a single pass (no loop).**

```mermaid
flowchart LR
    U["👤 User"] -->|"question"| L["🧠 LLM\n(with tool schemas)"]
    L -->|"tool_calls"| TC["🔧 [Tool calls]\n(name + args)"]
    TC -->|"results"| R["💬 Response\n(no feedback)"]
```

- **LLM chooses tools** — but in a single pass, not iteratively
- **No feedback** — the LLM never sees tool results before responding
- **No loop** — one LLM call, one set of tool executions, one response

**Example:** An LLM that can call a calculator once, but doesn't act on the result.

**Why this is NOT an agent:** There's no loop. The LLM calls tools and
immediately responds. It never sees the tool results before producing its
final answer.

---

## 4. Single AI Agent

**LLM makes decisions in a loop, calling tools and observing results.**

```mermaid
flowchart LR
    G["🎯 Goal"] --> O["👁️ Observe\n(user input, memory, environment)"]
    O --> R["🔍 Reason\n(LLM decides next action)"]
    R --> A["⚡ Act\n(tool call or respond)"]
    A -->|"tool_call"| TO["👁️ Observe Result\n(tool output)"]
    TO -->|"feedback"| R
    A -->|"text response"| D{"Done?"}
    D -->|"No"| O
    D -->|"Yes"| F["✅ Final Answer"]
```

- Iterative loop
- LLM chooses tools dynamically
- LLM observes tool results and adapts
- Memory across steps
- LLM decides when to stop

**Example:** A research agent that searches the web, evaluates results,
calculates totals, and writes a report.

**This POC's `ReActAgent`** is a single AI agent.

---

## 5. Multi-Agent System

**Multiple agents collaborate, each with its own loop.**

```mermaid
flowchart LR
    U["👤 User"] --> S["🧠 Supervisor Agent"]
    S -->|"delegate: research"| W1["🔍 Research Agent\n(web_search)"]
    S -->|"delegate: compute"| W2["🧮 Math Agent\n(calculator)"]
    S -->|"delegate: review"| W3["👁️ Reviewer Agent\n(critique)"]
    W1 -->|"results"| S
    W2 -->|"results"| S
    W3 -->|"critique"| S
    S -->|"synthesize"| Ans["✅ Final Answer"]
    Ans -->|"response"| U
```

- Each agent has its own goal, tools, and loop
- Agents communicate via messages, shared memory, or tool calls
- Higher cost and complexity, but specialized capabilities

**Example:** A research team where a supervisor delegates to a web-search
agent, a document-analysis agent, and a writing agent.

---

## Decision Tree

```mermaid
graph TD
    A["Does it loop (multiple steps)?"] -->|No| B["LLM Application"]
    A -->|Yes| C["Does the LLM choose tools?"]
    C -->|No| D["LLM Workflow"]
    C -->|Yes| E["Does the LLM observe results and adapt?"]
    E -->|No| F["Tool-Calling App"]
    E -->|Yes| G["Is it one agent?"]
    G -->|Yes| H["Single AI Agent"]
    G -->|No| I["Multi-Agent System"]
```

---

## Quick Test: Is it an agent?

Ask these questions:

1. **Does the LLM decide the next action?** (Not just the next word.)
2. **Can it call tools?** (Not just retrieve/generate in a fixed order.)
3. **Does it observe tool results?** (Not just use them in the same pass.)
4. **Does it loop?** (Does it keep going based on results?)
5. **Can it change its mind?** (Based on observations, take a different path.)

If you answered **yes** to all five → it's an agent.
If you answered **yes** to 1–3 only → tool-calling application.
If you answered **no** to all → LLM application.
If 1–4 yes but only one agent → single agent.

---

## In this POC

```mermaid
flowchart LR
    subgraph History["Evolution of this POC"]
        OldRAG["📄 Existing RAG pipeline\n(fixed: retrieve → generate)\n= LLM Workflow"]
        New["🎯 New ReActAgent\n(dynamic loop + tool selection)\n= Single AI Agent"]
        Future["👥 Future multi-agent\n(supervisor + worker agents)\n= Multi-Agent System"]
    end
    OldRAG -->|"Transitioned to"| New
    New -->|"Planned for"| Future
```
