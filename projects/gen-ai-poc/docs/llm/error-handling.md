# Error Handling, Rate Limits, and Retries

## Common LLM API Errors

### 401 Unauthorized

```python
# Missing or invalid API key
HTTPError: 401 Unauthorized
```

**Fix**: Check your API key in `.env` and ensure the model provider accepts it.

### 429 Too Many Requests (Rate Limited)

```python
# You're sending requests too fast
openai.RateLimitError: 429 Too Many Requests
```

**Fix**: Implement exponential backoff with retries.

### 400 Bad Request

```python
# Prompt too long or invalid parameters
openai.BadRequestError: 400 Bad Request - Error code: 400
```

**Fix**: Check token count (use the tokenizer), validate parameters.

### 408/504 Request Timeout

```python
openai.APITimeoutError: 504 Gateway Timeout
```

**Fix**: Increase timeout, implement retries.

### 503 Service Unavailable

```python
openai.APIError: 503 The server is temporarily unavailable
```

**Fix**: Retry with exponential backoff.

## Retry Logic

### Exponential Backoff

```python
import asyncio
import random
from openai import RateLimitError, APIError

async def call_with_backoff(func, max_retries=5, base_delay=1.0):
    """Call an LLM function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return await func()
        except RateLimitError as e:
            # 429 — rate limited
            if attempt < max_retries - 1:
                # Exponential backoff: 1s, 2s, 4s, 8s...
                delay = base_delay * (2 ** attempt)
                # Add jitter to avoid thundering herd
                delay += random.uniform(0, 1)
                await asyncio.sleep(delay)
            else:
                raise
        except APIError as e:
            # 5xx — temporary server errors
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                await asyncio.sleep(delay)
            else:
                raise
```

### When to Retry

| Error Type | Retry? | Strategy |
|-----------|--------|----------|
| 429 Rate Limit | Yes | Exponential backoff |
| 503 Unavailable | Yes | Exponential backoff |
| 504 Timeout | Yes | Longer timeout + backoff |
| 400 Bad Request | No | Fix the request |
| 401 Unauthorized | No | Fix the API key |
| 403 Forbidden | No | Check permissions/plan |

## Rate Limiting

### Token-based Rate Limits

Most LLM APIs rate-limit by **tokens per minute (TPM)** and **requests per minute (RPM)**:

```text
OpenAI rate limits (gpt-3.5-turbo):
- 3 requests per second
- 150,000 tokens per minute
- 200 concurrent requests
```

### Strategies for Managing Rate Limits

1. **Batch requests** — combine multiple operations into one API call
2. **Queue requests** — use a task queue (Celery, Redis Queue)
3. **Caching** — cache responses for repeated queries
4. **Throttling** — limit request rate on the client side

### Simple Rate Limiter

```python
import time
from collections import deque

class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = deque()

    async def acquire(self):
        now = time.time()
        # Remove old requests outside the window
        while self.requests and self.requests[0] < now - self.window:
            self.requests.popleft()
        
        if len(self.requests) >= self.max_requests:
            # Wait until the oldest request exits the window
            sleep_time = self.requests[0] + self.window - now
            await asyncio.sleep(sleep_time)
            return await self.acquire()

        self.requests.append(now)
```

## In Our POC

The LLM service wraps API calls with error handling:

```python
# app/llm/service.py
try:
    response = await self.client.chat.completions.create(...)
    return response
except Exception as e:
    logger.error("LLM generation failed: %s", e)
    raise HTTPException(status_code=502, detail=str(e))
```

### Token Counting

You can estimate token count to avoid exceeding limits:

```python
import tiktoken

def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))
```

## Timeout Configuration

Set appropriate timeouts based on your use case:

```python
# app/core/config.py
llm_timeout: int = 30  # seconds

# app/llm/service.py
self._client = AsyncOpenAI(
    timeout=settings.llm_timeout,
)
```

## Next Steps

- [Cost Considerations](cost.md) — How errors and retries affect costs
- [Streaming Responses](../llm/apis.md#streaming-response) — Handling partial errors
