# Agent Memory

> **Goal:** Understand the three types of memory in agentic systems —
> short-term, working, and long-term — and how they are implemented.

---

## Why Memory Matters

An agent that forgets everything between steps is just a stateless LLM.
**Memory** lets the agent:

- Retain the conversation history (so it doesn't repeat itself)
- Track task progress (what's been done, what's left)
- Remember user preferences and facts across sessions
- Accumulate context for better decisions

---

## Short-Term Memory (Conversation History)

**Short-term memory** is the agent's immediate context — the conversation
history of the current task. It is the equivalent of a chat's message list.

### What it stores

- The user's original request
- All LLM responses (including tool-call decisions)
- All tool results (observations)
- Any system messages

### Implementation

In this POC: `ConversationBuffer` (app/memory/short_term.py)

```python
class ConversationBuffer(ShortTermMemory):
    def add(self, message: ConversationMessage) -> None:
        self._messages.append(message)

    def get_messages(self) -> list[ConversationMessage]:
        return self._messages

    def truncate(self, max_chars: int) -> list[ConversationMessage]:
        # Remove oldest messages until under token/char budget
        ...
```

### Context window limits

LLMs have finite context windows. If the conversation grows too long,
memory must be **truncated** or **summarized**:

| Strategy | Description | Trade-offs |
|----------|-------------|------------|
| **Truncate** | Remove oldest messages | Fast, but loses early context |
| **Summarize** | Replace old messages with a summary | Retains gist, costs an LLM call |
| **Sliding window** | Keep last N messages | Simple, predictable |

### In this POC

`ConversationBuffer` supports truncation by character count
(`max_chars`). When exceeded, oldest messages are removed.

---

## Working Memory

**Working memory** is the agent's temporary scratchpad — a place to store
intermediate results, notes, and task state during a single run.

### What it stores

- Current sub-task being worked on
- Intermediate results (e.g., a value computed by the calculator)
- Notes about what the user cares about
- Flags (e.g., "user_asked_about_price = True")

### Implementation

In this POC: `InMemoryWorkingMemory` (app/memory/working.py)

```python
class InMemoryWorkingMemory(WorkingMemory):
    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)
```

### Why separate from short-term memory?

Short-term memory is a **message list** for the LLM. Working memory is a
**key-value store** for the agent's logic. Mixing them would clutter the
conversation.

---

## Long-Term Memory

**Long-term memory** persists across sessions. It stores facts about the
user, previous interactions, and learned knowledge.

### What it stores

- User preferences ("the user prefers metric units")
- Key facts learned from past conversations
- Session summaries ("last time we discussed the travel budget")
- Cached knowledge (e.g., a retrieved document)

### Implementation

In this POC: `PersistentMemory` (app/memory/long_term.py)

Uses a **SQLite** database (via stdlib `sqlite3`) with two tables:

```sql
CREATE TABLE memory_facts (
    id INTEGER PRIMARY KEY,
    namespace TEXT NOT NULL,
    key TEXT NOT NULL,
    vector BLOB,  -- embedding for semantic search
    value TEXT NOT NULL,
    created_at TEXT,
    updated_at TEXT,
    UNIQUE(namespace, key)
);

CREATE VIRTUAL TABLE memory_facts_vec USING vec0(vector_id UNDEFINED);
-- (or a simple in-memory vector table)
```

### Semantic search

Long-term memory supports semantic search — finding facts similar to a
query, even if they don't match exactly. This uses embeddings:

```python
async def search(self, namespace: str, query: str, top_k: int = 5) -> list[MemoryFact]:
    query_vec = await self._embed(query)
    # compute cosine similarity with all stored vectors
    ...
```

### In this POC

See `app/memory/long_term.py` (app/memory/long_term.py). The
embedding service is injected, so you can use real embeddings or a mock.

---

## Memory Retrieval

### Short-term memory
All messages are passed to the LLM as context (with truncation).

### Working memory
The agent logic reads/write specific keys.

### Long-term memory
Retrieved by:
- **Exact key lookup** (`retrieve(namespace, key)`)
- **Semantic search** (`search(namespace, query)`)

The agent decides what to retrieve — typically via a dedicated tool.

---

## Memory Updates

| Memory type | Update strategy |
|-------------|----------------|
| Short-term | Append messages; truncate when exceeding limit |
| Working | Set/overwrite keys |
| Long-term | Store fact → upsert by (namespace, key); update vector |

### Expiration

Long-term memory can expire facts (TTL). This prevents stale information.

**In this POC:** Not yet implemented (simple upsert model).

### Consistency

When multiple facts change, the agent should update them atomically. In this
POC, SQLite transactions ensure consistency.

### Privacy

Sensitive information (credentials, personal data) should:
- Be encrypted at rest
- Be scoped to namespaces
- Be deletable on request

**In this POC:** The `namespace` field provides basic scoping.

---

## RAG vs. Agent Memory

| Aspect | RAG Pipeline | Agent Memory |
|--------|-------------|--------------|
| **Purpose** | Answer questions from documents | Remember across conversation/task |
| **Scope** | Document corpus | User session + user profile |
| **Lifecycle** | Ingest → Query → Ingest | Store → Retrieve → Update |
| **Access** | Usually fixed (query → context) | Dynamic (LLM decides when to read/write) |
| **Example** | "What does the manual say about X?" | "The user prefers Y. I noted this last time." |

**Key insight:** Vector databases are a *mechanism* for RAG and for
long-term memory, but they are not the same thing. RAG retrieves from a
document corpus; agent memory stores conversational and user-specific facts.

Vector storage **can be** used as one memory mechanism, but vector DBs
are not synonymous with agent memory.

---

## Interview Questions

**Q: What is short-term memory in an agent?**
A: The agent's immediate context — the conversation history of the current
task. All messages (user input, assistant responses, tool results) are kept
in a buffer and passed to the LLM.

**Q: What is long-term memory?**
A: Persistent memory that survives across sessions. It stores user
preferences, facts learned from past interactions, and session summaries.

**Q: What is working memory?**
A: A temporary, task-scoped scratchpad. The agent uses it to store
intermediate results, flags, and notes during a single task execution.

**Q: How would you implement persistent agent memory?**
A: Use a database (SQLite, PostgreSQL) or a key-value store. Store facts
with a namespace, key, and value. Optionally store embeddings for semantic
search. Upsert by key; retrieve by exact match or similarity search.

**Q: How does RAG differ from agent memory?**
A: RAG retrieves information from a document corpus (e.g., manuals, articles)
to ground responses. Agent memory stores conversational context, user
preferences, and learned facts. RAG is about external knowledge; memory is
about internal state.

**Q: How would you prevent memory from becoming too large?**
A: (1) Truncate short-term memory by character/token limit, (2) summarize
old conversations, (3) implement TTL for long-term facts, (4) archive or
delete stale entries.

**Q: How would you handle stale memory?**
A: Implement TTL (time-to-live) with expiration timestamps, or use a
confidence/scoring mechanism to weight recent facts more heavily.

### Follow-up questions
- "How would you summarize conversation history to fit within a context window?"
- "How do you ensure memory consistency across parallel agent runs?"
- "Should memory be encrypted? Why?"
- "How would you design a memory eviction policy?"

### Common mistakes
- Putting everything in long-term memory (slow, cluttered)
- Never truncating short-term memory (context overflow)
- Not scoping memory by namespace/user (cross-user leakage)
- Confusing RAG retrieval with agent memory
