# Structured Outputs

## What are Structured Outputs?

**Structured outputs** force an LLM to return data in a specific, predictable
format (JSON, tables, etc.) rather than free-form text.

## Why Structured Outputs Matter

When integrating LLMs into applications, you need data you can parse and use:

```mermaid
graph TD
    subgraph "Free-form Output"
        FF["❌ LLM generates free text:<br/>\"The temperature in SF is 68°F,<br/>it's sunny and the humidity is 70%.\""]
        PARSE["✅ Requires parsing:<br/>Extract temperature, unit, condition,<br/>humidity from natural language<br/>Fragile — format varies by response"]
    end

    subgraph "Structured Output"
        SO["✅ LLM generates JSON:<br/>{\"temperature\": 68, \"unit\": \"F\",<br/>\"condition\": \"sunny\", \"humidity\": 70}"]
        VALIDATE["✅ Directly parseable:<br/>json.loads() → dict<br/>Validated against schema<br/>No text parsing needed"]
    end

    FF --> PARSE
    SO --> VALIDATE

    style FF fill:#e74c3c,color:#fff
    style PARSE fill:#f39c12,color:#fff
    style SO fill:#27ae60,color:#fff
    style VALIDATE fill:#27ae60,color:#fff
```

## Methods for Structured Output

### 1. Prompt Engineering

The simplest approach — just ask in the prompt:

```python
prompt = """
Extract the date, amount, and merchant from this text.
Return as JSON.

Text: "On March 15th, I paid $42.50 to Amazon for books."
JSON:
"""
```

**Pros**: Works with any model
**Cons**: Not guaranteed — model may still produce free text

### 2. Constrained Decoding (JSON Mode)

Some providers support JSON mode:

```python
response = await client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    response_format={"type": "json_object"},
)
```

**Pros**: Stronger guarantee of valid JSON
**Cons**: Provider-specific, still needs validation

### 3. Schema-Guided Generation

Provide a JSON schema — the model generates data conforming to it:

```python
response = await client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "weather_info",
            "schema": {
                "type": "object",
                "properties": {
                    "temperature": {"type": "number"},
                    "unit": {"type": "string"},
                    "condition": {"type": "string"},
                },
                "required": ["temperature", "unit", "condition"],
            }
        }
    },
)
```

### 4. Function Calling

Use function calling to force structured output:

```python
tools = [{
    "type": "function",
    "function": {
        "name": "extract_info",
        "parameters": {
            "type": "json_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "amount": {"type": "number"},
                    "merchant": {"type": "string"},
                },
                "required": ["date", "amount", "merchant"],
            }
        }
    }
}]

response = await client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=tools,
)
```

## Validation

Always validate LLM output, even with constrained formats:

```python
import json
from pydantic import BaseModel, ValidationError

class WeatherInfo(BaseModel):
    temperature: float
    unit: str
    condition: str

# Parse and validate
try:
    data = json.loads(llm_output)
    info = WeatherInfo(**data)
    print(f"Temperature: {info.temperature}°{info.unit}")
except (json.JSONDecodeError, ValidationError) as e:
    print(f"Invalid output: {e}")
    # Fallback
```

## In Our POC

Our RAG response schema is defined with Pydantic:

```python
# app/models/schemas.py
class RAGResponse(BaseModel):
    answer: str
    sources: list[SearchHit] = Field(default_factory=list)
    context: str = ""
```

The API returns structured JSON — the LLM's text answer is wrapped in a
predictable response format.

## JSON Extraction from Free Text

When the LLM returns free text but you need JSON, use extraction:

```python
import re
import json

def extract_json(text: str) -> dict | None:
    """Extract the first JSON object from free text."""
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return None
    return None
```

## Best Practices

1. **Always validate** — never trust LLM output directly
2. **Use JSON mode** when available
3. **Provide examples** in the prompt
4. **Specify required fields** clearly
5. **Handle failures gracefully** — have a fallback
6. **Log raw output** — useful for debugging failed extractions

## Next Steps

- [Function Calling](function-calling.md) — Tools as the ultimate structured output
- [Agents](agents.md) — Combining tools and structured outputs
