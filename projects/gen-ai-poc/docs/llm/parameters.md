# LLM Parameters: Temperature, Top-p, and Token Limits

## What Are Model Parameters?

When calling an LLM, you can control its behavior through several parameters.
These don't change the model — they change how the model **samples** from its
learned probability distribution.

## Temperature

Controls randomness by scaling the probability distribution before sampling.

```python
# Low temperature → focused, deterministic
temperature=0.2

# Medium temperature → balanced
temperature=0.7

# High temperature → creative, random
temperature=1.5
```

### How Temperature Works

The model produces a probability distribution over the next token:

```text
Tokens:    "the"  "a"  "an"  "this"  "that"
Probabilities:  0.5  0.2  0.1   0.1   0.1
```

At **temperature = 1.0** (default): sample according to these exact probabilities.

At **temperature = 0.5**: sharpen the distribution — high-probability tokens
become even more likely:
```text
Probabilities:  0.7  0.1  0.05  0.05  0.1
```

At **temperature = 2.0**: flatten the distribution — low-probability tokens
become more likely:
```text
Probabilities:  0.3  0.2  0.18  0.17  0.15
```

### When to Use Which Temperature

| Temperature | Best For | Risk |
|-------------|----------|------|
| 0.0 | Factual Q&A, code generation | Repetitive, boring |
| 0.2-0.5 | Summarization, extraction | Safe and reliable |
| 0.7 | General conversation | Good balance |
| 1.0+ | Creative writing, brainstorming | May produce nonsense |

## Top-p (Nucleus Sampling)

Instead of sampling from all possible tokens, top-p restricts sampling to
the smallest set of tokens whose cumulative probability exceeds `p`.

```python
top_p=1.0   # Consider all tokens (default)
top_p=0.9   # Consider top 90% of probability mass
top_p=0.1   # Consider only the top 10% — very focused
```

### Example

With `top_p=0.9`:

```text
Tokens:    "the"  "a"  "an"  "this"  "that"  "other"
Cumulative:  0.5  0.7  0.8   0.9   0.95  1.00

→ Only "the", "a", "an", "this" are considered (cumulative ≤ 0.9)
→ Probabilities are renormalized among these
```

### Temperature vs. Top-p

| Parameter | Approach | When to Use |
|-----------|----------|-------------|
| Temperature | Softens/sharpenens entire distribution | General control of randomness |
| Top-p | Hard cutoff on probability mass | When you want to exclude unlikely tokens |

**Best practice**: Adjust one at a time. If using top_p for filtering,
keep temperature around 0.7-0.9.

## Max Tokens

Limits how many tokens the model can generate in its response.

```python
max_tokens=100   # Short response
max_tokens=1000  # Long response
max_tokens=4096  # Very long (if model supports it)
```

### Context Window Consideration

The **context window** includes both the prompt and the response:

```text
Context window: 8192 tokens
Prompt: 5000 tokens
Max response: 3192 tokens
```

If `max_tokens` exceeds the remaining space, you'll get an error.

## Presence and Frequency Penalties

(OpenAI-specific, not all providers support these)

### Presence Penalty (`presence_penalty`)

Penalizes new tokens based on whether they've appeared in the text so far.

```python
presence_penalty=0.0   # Default — no penalty
presence_penalty=1.0   # Discourage repetition
```

### Frequency Penalty (`frequency_penalty`)

Penalizes tokens based on their frequency in the text so far.

```python
frequency_penalty=0.5  # Mild anti-repetition
frequency_penalty=2.0  # Strong anti-repetition
```

## In Our POC

All these parameters are configurable:

```python
# app/models/schemas.py
class LLMRequest(BaseModel):
    messages: list[ChatMessage]
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    stream: bool = False
```

```python
# app/core/config.py
class Settings(BaseSettings):
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1024
    llm_top_p: float = 1.0
```

### Example: Calling with Parameters

```bash
curl -X POST http://localhost:8000/api/v1/llm/generate \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Write a creative poem about AI"}],
    "temperature": 1.2,
    "top_p": 0.9,
    "max_tokens": 100
  }'
```

## Choosing Parameters by Task

| Task | Temperature | Top-p | Max Tokens | Notes |
|------|------------|-------|------------|-------|
| Factual Q&A | 0.2 | 0.9 | 256 | Deterministic |
| Summarization | 0.3 | 0.9 | 512 | Concise output |
| Code generation | 0.2 | 0.95 | 1024 | Correct syntax |
| Creative writing | 0.8 | 0.95 | 1024 | Varied output |
| Brainstorming | 1.0 | 1.0 | 512 | Maximum ideas |
| Classification | 0.0 | 0.9 | 10 | Structured output |
| Math reasoning | 0.2 | 0.95 | 512 | Reliable logic |

## Next Steps

- [Error Handling](error-handling.md) — What happens when parameters are out of range
- [Cost Considerations](cost.md) — How max_tokens affects pricing
