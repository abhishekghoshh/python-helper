# Architecture Diagrams

> **Visual reference** — the key diagrams for agentic AI architecture.

---

## 1. Basic Agent

```mermaid
flowchart TD
    U[User] --> A[Agent]
    A --> L[LLM]
    A --> T[Tools]
    L --> T
    T --> E[External Systems]
    L --> R[Response]
    R --> A
    A --> U
```

---

## 2. Tool-Using Agent

```mermaid
flowchart TD
    U[User Input] --> A[Agent Loop]
    A -->|"1. Build messages"| M[Memory]
    M -->|"2. system + history"| LLM
    A -->|"3. Tool definitions"| TD[Tool Definitions]
    LLM -->|"4. Reason + decide"| D{Action?}
    D -->|"Tool call"| TC[Tool Call]
    D -->|"Final answer"| FA[Final Answer]
    TC --> TExec[Tool Executor]
    TExec -->|"5. Allow-list check"| AL[Allow-list]
    AL -->|"6. Validate args"| VA[Validator]
    VA -->|"7. Execute"| Tool
    Tool --> Ext[External System]
    Ext -->|"8. Result"| Obs[Observation]
    Obs -->|"9. Add to memory"| M
    M -->|"10. Loop back"| LLM
    FA --> A
    A --> U
```

---

## 3. Agent Loop

```mermaid
flowchart TD
    O[Observe] --> R[Reason]
    R --> P[Plan]
    P --> A[Act]
    A --> O2[Observe Result]
    O2 --> R2[Reason Again]
    R2 --> D{Continue?}
    D -->|Yes| O
    D -->|No| F[Final Answer]
```

---

## 4. Agent with Memory

```mermaid
flowchart TD
    U[User Input] --> A[Agent]
    A --> ST[Short-Term Memory]
    A --> WM[Working Memory]
    A --> LT[Long-Term Memory]
    ST -->|"Context"| LLM
    WM -->|"Task state"| A
    LT -->|"Retrieve facts"| A
    A --> LLM
    LLM --> T[Tools]
    T -->|"Results"| ST
    LLM -->|"Answer"| U
```

---

## 5. Agent with RAG

```mermaid
flowchart TD
    U[User] --> A[Agent]
    A -->|"Needs knowledge?"| D{Decision}
    D -->|Yes| R[RAG Tool]
    R --> E[Embed Question]
    E --> VS[Vector Search]
    VS --> CR[Context Retrieval]
    CR -->|"Context"| A
    D -->|No| G[Generate from LLM knowledge]
    A -->|"Answer"| U
```

---

## 6. Multi-Agent Architecture

```mermaid
flowchart TD
    U[User] --> Sup[Supervisor Agent]
    Sup -->|"Delegate research"| RA[Research Agent]
    Sup -->|"Delegate math"| MA[Math Agent]
    Sup -->|"Delegate review"| Rev[Reviewer Agent]
    RA -->|"Search results"| Sup
    MA -->|"Calculation result"| Sup
    Rev -->|"Critique"| Sup
    Sup -->|"Synthesize"| Ans[Final Answer]
    Sup --> U
```

---

## 7. Agent State Machine

```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> RUNNING: start
    RUNNING --> THINKING: iteration begins
    THINKING --> TOOL_CALLING: tools decided
    THINKING --> COMPLETED: final answer
    TOOL_CALLING --> OBSERVING: tools executed
    OBSERVING --> THINKING: next iteration
    OBSERVING --> THINKING: retry
    THINKING --> FAILED: error
    RUNNING --> MAX_ITERATIONS: cap reached
    MAX_ITERATIONS --> TERMINATING
    COMPLETED --> TERMINATING
    FAILED --> TERMINATING
    TERMINATING --> DONE
```

---

## 8. Security Boundaries

```mermaid
flowchart LR
    LLM[LLM: decides WHAT] --> Decision
    App[Application: decides WHAT IS ALLOWED] --> Guardrails
    Decision --> Act[Action]
    Guardrails --> Check{Allowed?}
    Check -->|Yes| Execute[Execute Tool]
    Check -->|No| Block[Blocked]
    Execute --> Result[Result]
    Block --> Result2[Blocked Result]
```
