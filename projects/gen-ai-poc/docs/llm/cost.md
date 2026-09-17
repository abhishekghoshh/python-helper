# Cost Considerations

## How LLM APIs Are Priced

LLM APIs are priced by **tokens**. A token is roughly 4 characters or ¾ of a word.

```text
"Generative AI is transforming software."
→ ~7 tokens (approximately)
```

### Pricing Structure

| Component | Description |
|-----------|-------------|
| **Input tokens** | Tokens in your prompt (what you send) |
| **Output tokens** | Tokens in the response (what the model generates) |
| **Token ratio** | Input is typically ¼ to ⅓ the price of output |

### Example: OpenAI Pricing

| Model | Input | Output |
|-------|-------|--------|
| gpt-3.5-turbo | $0.001 / 1K tokens | $0.002 / 1K tokens |
| gpt-4-turbo | $0.0015 / 1K tokens | $0.003 / 1K tokens |
| gpt-4 | $0.03 / 1K tokens | $0.06 / 1K tokens |

### Cost Calculation Example

If you send a 500-token prompt that gets a 200-token response using gpt-3.5-turbo:

```text
Input:  500 tokens × ($0.001 / 1000) = $0.0005
Output: 200 tokens × ($0.002 / 1000) = $0.0004
Total: $0.0009 per call
```

At 10,000 calls per day: ~$9/day, ~$270/month.

## Cost Optimization Strategies

### 1. Cache Responses

```python
import hashlib
import functools

@functools.lru_cache(maxsize=1024)
def cached_completion(prompt_hash: str, params: tuple) -> str:
    # Skip re-calling the API for identical requests
    return generate_response(prompt_hash)
```

### 2. Use Smaller Models

| Model | Use Case | When to Use |
|-------|----------|-------------|
| gpt-3.5-turbo | General tasks | Cost-sensitive, simple tasks |
| gpt-4 | Complex reasoning | Quality matters, budget allows |
| text-embedding-3-small | Embeddings | Most embedding tasks |
| text-embedding-3-large | High-precision embeddings | When quality is critical |

### 3. Limit Output Tokens

```python
# Only request what you need
request = LLMRequest(
    messages=messages,
    max_tokens=256,  # Not 4096 if you need a short answer
)
```

### 4. Use Local Models

For some tasks, local models are cheaper and more private:

```python
# app/core/config.py
embedding_provider: str = "sentence-transformers"  # Local, no API cost
```

Local embedding models (sentence-transformers) run on CPU and have zero
per-call cost, making them ideal for ingestion and search.

### 5. Batch Requests

```python
# Instead of N individual calls, make fewer batched calls
response = await client.embeddings.create(
    model="text-embedding-3-small",
    input=texts,  # List of texts
)
```

## Cost vs. Local Models Trade-off

| Aspect | API (Cloud) | Local |
|--------|------------|-------|
| **Upfront cost** | None | GPU (~$1,000-5,000) |
| **Per-call cost** | Yes ($0.0001-0.001) | No (just electricity) |
| **Quality** | State-of-the-art | Varies by model size |
| **Latency** | Network-dependent | Fast (on same machine) |
| **Privacy** | Data leaves your system | Data stays local |
| **Scalability** | Auto-scales | Manual scaling |
| **Maintenance** | Provider-managed | You manage updates |

## In Our POC

The POC supports both local and cloud embeddings:

```python
# Default: local sentence-transformers (free)
EMBEDDING_PROVIDER=sentence-transformers

# Alternative: OpenAI embeddings (paid)
EMBEDDING_PROVIDER=openai
```

For the LLM layer, the POC uses the OpenAI API (cloud). A local LLM (e.g.,
Ollama) can be substituted by changing `LLM_BASE_URL`.

## Monitoring Cost

Track token usage to stay within budget:

```python
response = await llm_service.generate(request)
usage = response.usage  # {prompt_tokens, completion_tokens, total_tokens}
cost = (usage["prompt_tokens"] * input_rate + 
        usage["completion_tokens"] * output_rate) / 1000
```

## Cost Optimization Checklist

- [ ] Cache identical requests
- [ ] Use appropriate model size for the task
- [ ] Set `max_tokens` to realistic limits
- [ ] Use local embeddings where possible
- [ ] Batch embedding requests
- [ ] Monitor token usage in logs
- [ ] Set spending alerts
- [ ] Consider local LLMs for development
