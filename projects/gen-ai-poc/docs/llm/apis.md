# Communicating with LLMs

## How Applications Talk to LLMs

LLMs expose **HTTP APIs** that accept text input and return text (or tokens)
as output. Applications make HTTP requests to these APIs, just like any
other web service.

## The Chat API Pattern

Most modern LLM APIs use a **chat completion** pattern:

```mermaid
flowchart LR
    App[Your Application] --> API[LLM API Endpoint]
    API --> Model[LLM on Server]
    Model --> API
    API --> App

    style App fill:#3498db,color:#fff
    style API fill:#e74c3c,color:#fff
    style Model fill:#27ae60,color:#fff
```

## Request Structure

### OpenAI API Format

```python
response = await client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"}
    ],
    temperature=0.7,
    max_tokens=100,
)
```

### Request Components

| Field | Description | Required? |
|-------|-------------|-----------|
| `model` | Which model to use | Yes |
| `messages` | Conversation history | Yes |
| `temperature` | Randomness control (0.0-2.0) | No |
| `top_p` | Nucleus sampling (0.0-1.0) | No |
| `max_tokens` | Max output length | No |
| `stream` | Stream tokens as generated | No |
| `stop` | Stop sequences | No |

## Response Structure

### Non-Streaming Response

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "model": "gpt-3.5-turbo",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Paris is the capital of France."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 8,
    "total_tokens": 28
  }
}
```

### Streaming Response

When `stream=True`, the API returns Server-Sent Events (SSE):

```json
data: {"choices":[{"delta":{"content":"Pa"}}]}

data: {"choices":[{"delta":{"content":"ris"}}]}

data: {"choices":[{"delta":{"content":" is"}}]}

data: [DONE]
```

Each chunk contains a small piece of the response, enabling real-time
display in UIs.

## Completion API vs. Chat API

| Aspect | Completion API | Chat API |
|--------|---------------|----------|
| Input | Prompt string | Message array |
| Output | Text completion | Assistant message |
| Use case | Legacy, simple | Modern, conversational |
| State | Stateless | Stateful (multi-turn) |

The Chat API is the modern standard. Most new models (GPT-3.5, GPT-4, Claude, Llama)
are chat-trained and perform best with the Chat API format.

## In Our POC

Our LLM service wraps the OpenAI client:

```python
# app/llm/service.py
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
)

response = await client.chat.completions.create(
    model=settings.llm_model,
    messages=messages,
    temperature=temperature,
    max_tokens=max_tokens,
)
```

The FastAPI endpoint exposes this as a REST API:

```python
# app/api/v1/llm.py
@router.post("/generate", response_model=LLMResponse)
async def generate_llm_response(request: LLMRequest) -> LLMResponse:
    return await llm_service.generate(request)
```

### API Endpoint

`POST /api/v1/llm/generate`

```bash
curl -X POST http://localhost:8000/api/v1/llm/generate \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Explain quantum computing."}
    ],
    "temperature": 0.7,
    "max_tokens": 256
  }'
```

### Streaming Endpoint

`POST /api/v1/llm/generate-stream`

```bash
curl -N -X POST http://localhost:8000/api/v1/llm/generate-stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Tell me a joke"}],
    "stream": true
  }'
```

## Other LLM Providers

The OpenAI API format is widely adopted. Other providers:

| Provider | API Compatible? | Notes |
|----------|----------------|-------|
| OpenAI | Reference | The standard |
| Anthropic (Claude) | Partial | Similar but different structure |
| Google (Gemini) | No | Different API entirely |
| Ollama | Yes | Local models, OpenAI-compatible |
| LM Studio | Yes | Local models, OpenAI-compatible |
| Together.ai | Yes | OpenAI-compatible |
| Groq | Yes | OpenAI-compatible, fast inference |

Our POC uses the OpenAI client with a configurable `base_url`, so it works
with any OpenAI-compatible provider:

```python
# .env
LLM_BASE_URL=https://api.openai.com/v1    # OpenAI
# or
LLM_BASE_URL=http://ollama:11434/v1       # Local Ollama
# or
LLM_BASE_URL=http://openai-compatible:8080/v1  # Any compatible service
```

## Next Steps

- [Parameters](parameters.md) — Temperature, top-p, token limits
- [Error Handling](error-handling.md) — Rate limits and retries
