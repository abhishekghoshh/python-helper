# Prompt Templates

## What Are Prompt Templates?

A **prompt template** is a reusable pattern with placeholders that get filled
in at runtime. Templates standardize prompting workflows and make prompts
maintainable.

## Why Use Templates?

- **Consistency**: Same structure every time
- **Reusability**: Fill in variables instead of rewriting
- **Testability**: Easy to test with different inputs
- **Version control**: Track prompt changes in code

## Basic Template Pattern

```python
# Simple f-string approach
def make_summary_prompt(text: str, max_words: int = 3) -> str:
    return f"""
Summarize the following text in {max_words} words:

{text}

Summary:
"""
```

## Template with Delimiters

```python
def make_rag_prompt(context: str, question: str) -> str:
    return f"""
{context}
===
Question: {question}

Answer concisely using only the context above:
"""
```

Delimiters (`===`) help the model distinguish sections.

## Using Python's `string.Template`

```python
from string import Template

template = Template("""
You are a $role.
Task: $task
Tone: $tone

Content:
$content
""")

prompt = template.substitute(
    role="technical writer",
    task="explain a complex concept simply",
    tone="friendly",
    content="How quantum computers work"
)
```

## XML-Style Delimiters

```python
def structured_prompt(text: str, format: str) -> str:
    return f"""
<instruction>
Analyze the following text and extract information in the specified format.
</instruction>

<text>
{text}
</text>

<output_format>
{format}
</output_format>

<result>
"""
```

## In Our POC

The RAG pipeline uses templates extensively:

```python
# app/rag/retrieval.py
def build_rag_prompt(question: str, context: str) -> str:
    system_prompt = """You are a helpful assistant that answers questions based 
    on the provided context."""
    
    user_prompt = f"""Context:
{context}

Question: {question}

Answer:"""
    
    return f"{system_prompt}\n\n{user_prompt}"
```

```python
# app/rag/generation.py
# Messages with explicit roles
messages = [
    ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
    ChatMessage(role=MessageRole.USER, content=user_prompt),
]
```

## Template Best Practices

1. **Keep it readable**: Use whitespace and delimiters
2. **Make variables explicit**: Use clear placeholder names
3. **Handle empty inputs**: What happens if context is empty?
4. **Version your prompts**: Track template changes
5. **Test with real data**: Validate outputs with edge cases

## Prompt Chaining

Templates can chain — one prompt's output feeds into the next:

```python
# Step 1: Extract key topics
extract_prompt = "Extract key topics from: {text}"

# Step 2: Generate summary based on topics
summary_prompt = "Write a summary focusing on these topics: {topics}"
```

## Next Steps

- [Prompt Injection](injection.md) — Security risks of templated prompts
- [Best Practices](best-practices.md) — Production considerations
