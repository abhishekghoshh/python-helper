# Experiment: Agent Memory

**Category:** Memory  
**Difficulty:** Intermediate  
**Estimated time:** 10 minutes

---

## Objective

Understand how the three types of memory (short-term, working, long-term)
work together and how they affect agent behavior.

---

## Hypothesis

- **Short-term memory** (conversation buffer) is essential for multi-turn
  conversations — removing it makes the agent "forget" earlier turns.
- **Working memory** allows the agent to track task progress across tool
  calls.
- **Long-term memory** allows the agent to remember user preferences and
  facts across sessions.

---

## Architecture

```mermaid
flowchart TB
    UI["User Input"] --> STM["Short-term Memory<br/>(ConversationBuffer)"]
    STM -->|Messages| STM_D["Stores: user, assistant, tool results<br/>Purpose: provide context to the LLM each turn"]
    STM --> WTM["Working Memory<br/>(InMemoryWorkingMemory)"]
    WTM -->|Key-value data| WTM_D["Stores: intermediate results, sub-tasks<br/>Purpose: track task progress<br/>Example: {\"budget_total\": 1096, \"last_step\": \"calculated\"}"]
    WTM --> LTM["Long-term Memory<br/>(PersistentMemory / SQLite)"]
    LTM -->|Facts & preferences| LTM_D["Stores: user preferences, facts, session summaries<br/>Purpose: persist across agent runs<br/>Example: {\"preferred_unit\": \"metric\", \"last_topic\": \"budget\"}"]
```

Source: `app/memory/` (app/memory/)

---

## Implementation

### Short-term memory

```python
# app/memory/short_term.py
memory = ConversationBuffer(max_chars=4000)

# Add messages
memory.add_user("What is 23 * 47 + 15?")
memory.add(assistant_message)
memory.add(tool_result_message)

# Get context for LLM
messages = memory.get_messages()  # all messages in order
```

### Working memory

```python
# app/memory/working.py
working = InMemoryWorkingMemory()
working.set("calculation_result", "1096")
working.set("step", 2)

value = working.get("calculation_result")  # "1096"
```

### Long-term memory

```python
# app/memory/long_term.py
lt_memory = PersistentMemory(db_path="data/agent_memory.db")
await lt_memory.store("user_prefs", "units", "metric")
await lt_memory.store("facts", "capital_of_france", "Paris")

# Retrieve by key
fact = await lt_memory.retrieve("user_prefs", "units")  # "metric"

# Search by similarity
results = await lt_memory.search("user_facts", "What did we discuss?")
```

---

## Input

Multi-turn conversation:

```
Turn 1: What is 23 * 47 + 15?
Turn 2: What did I just ask you to calculate?
Turn 3: My name is Alex. Remember that.
Turn 4: What is my name?
```

---

## Execution

### Test 1: Short-term memory (same session)

```bash
python -m app.cli
> What is 23 * 47 + 15?
# Agent calls calculator → answers 1096
> What did I just ask you to calculate?
# Agent remembers the conversation → references the earlier calculation
```

Without short-term memory, the agent would not remember the earlier question.

### Test 2: Long-term memory (across sessions)

```python
# Session 1
await lt_memory.store("user_prefs", "name", "Alex")

# Session 2 (new agent instance)
name = await lt_memory.retrieve("user_prefs", "name")
# → "Alex"
```

### Test 3: Working memory

```python
agent.working_memory.set("task_progress", "step 1 complete")
agent.working_memory.set("intermediate_result", "1096")
# Available throughout the agent's run
```

---

## Result

| Memory type | Persists across turns? | Persists across sessions? | Key API |
|-------------|-----------------------|--------------------------|---------|  |
| Short-term | ✅ Yes | ❌ No (in-memory) | `memory.add`, `memory.get_messages()` |
| Working | ✅ Yes (same run) | ❌ No (in-memory) | `working.set`, `working.get` |
| Long-term | ✅ Yes | ✅ Yes (SQLite) | `store`, `retrieve`, `search` |

---

## Observations

1. **Short-term memory is conversation context** — without it, the agent
   can't reference earlier turns.
2. **Working memory is a scratchpad** — useful for the agent to track
   task-specific state during a run.
3. **Long-term memory enables personalization** — the agent can remember
   user preferences and facts across sessions.
4. **Memory truncation matters** — if short-term memory grows too large,
   it must be truncated to fit the LLM's context window.
5. **Vector search for memory** — long-term memory can use embeddings for
   semantic search (finding related facts even without exact key match).

---

## Trade-offs

| Memory type | Storage | Retrieval | Use case |
|-------------|---------|-----------|----------|
| Short-term | In-memory list | Pass to LLM | Current conversation |
| Working | In-memory dict | Key lookup | Task scratchpad |
| Long-term | SQLite / vector DB | Key or semantic search | User preferences, facts |
| **Trade-off** | In-memory is fast but lost on crash | Semantic search is powerful but costly | Choose based on persistence needs |

---

## Variations to try

1. **Truncate short-term memory** — set `max_chars` to a small value and
   observe the agent forgetting early conversation.
2. **Persist working memory** — save it to disk between runs.
3. **Semantic memory search** — store facts with embeddings and retrieve
   by similarity instead of exact key.

---

## Key takeaway

Memory is what makes an agent **stateful** across turns and sessions.
Short-term memory enables multi-turn dialogue, working memory tracks
task progress, and long-term memory enables personalization. Each serves a
distinct purpose, and choosing the right storage and retrieval strategy
matters.
