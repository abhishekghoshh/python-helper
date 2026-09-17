# Agentic AI Knowledge Base

This is a sample document ingested into the RAG vector database.
It demonstrates how an agent can use RAG to answer questions about
internal documentation.

## Overview

Agentic AI systems use an iterative loop of observation, reasoning,
planning, and action. They differ from simple LLM applications by
their ability to:

1. Call tools to interact with the world
2. Observe results and adapt their approach
3. Maintain memory across turns
4. Make decisions about which tools to use

## Key Components

- **Agent Loop**: The observe-reason-act cycle
- **Tools**: Functions the agent can invoke
- **Memory**: Context and state management
- **Planning**: Task decomposition and reasoning
- **Guardrails**: Safety boundaries and limits

## ReAct Pattern

ReAct interleaves reasoning with tool actions:

```
Thought: I need to calculate something. I should use the calculator.
Action: calculator
Action Input: 23 * 47 + 15
Observation: 1096
Thought: I have the result. The answer is 1096.
```

## Benefits

- Agents can solve complex, multi-step problems
- They adapt to unexpected results
- They can use external tools for accuracy
- They learn from feedback (human or environmental)
