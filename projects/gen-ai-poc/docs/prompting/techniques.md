# Prompting Techniques

Different prompt structures can dramatically change model behavior and output quality.

## Zero-Shot Prompting

**Zero-shot** means giving the model a task without any examples — it must
reason from the instruction alone.

```python
# Zero-shot
prompt = "Classify the sentiment of this text as positive, negative, or neutral:\n"The food was amazing!""
# Expected output: "positive"
```

### When to use
- Simple, well-defined tasks
- When the model's training data already covers the task format
- Quick prototyping

### Limitations
- The model may not understand the expected output format
- Quality can be inconsistent

## Few-Shot Prompting

**Few-shot** provides a few examples before asking the model to perform the task:

```python
prompt = """
Classify the sentiment of the following texts:

Text: "I love this product!"
Sentiment: positive

Text: "This is the worst experience ever."
Sentiment: negative

Text: "The package arrived on time."
Sentiment: neutral

Text: "The food was amazing!"
Sentiment:
"""
# Expected output: "positive"
```

### Why it works
The examples serve as a template — the model learns the pattern and applies
it to the new input.

### When to use
- Task-specific formats
- When zero-shot quality is insufficient
- When you need consistent output structure

## Chain-of-Thought (CoT)

Chain-of-thought prompting asks the model to **think step by step** before
answering:

```python
prompt = """
A store had 100 apples. They sold 30 in the morning and 25 in the afternoon.
How many apples are left? Think step by step.
"""
```

### Example with CoT

```python
prompt = """
Question: A train leaves station A at 60 mph. Another leaves station B at 40 mph, 
2 hours later, toward station A. The distance between stations is 500 miles. 
When do they meet?

Let's think step by step:
1. In 2 hours, the first train travels 60 × 2 = 120 miles.
2. Remaining distance: 500 - 120 = 380 miles.
3. Combined speed: 60 + 40 = 100 mph.
4. Time to meet: 380 / 100 = 3.8 hours.
5. Total time for train A: 2 + 3.8 = 5.8 hours.

Answer: They meet after 5.8 hours.
"""
```

### Variants

| Variant | Description | Example |
|---------|-------------|---------|
| **CoT** | "Think step by step" | "Explain your reasoning" |
| **CoT-SC** | Chain of Thought with Self-Consistency | Generate multiple answers, vote |
| **ToT** | Tree of Thoughts | Explore multiple reasoning paths |
| **Auto-CoT** | Automatically generate reasoning examples | Few-shot CoT |

## Structured Output

Asking the model to return data in a specific format:

```python
prompt = """
Extract the following information as JSON:
- Customer name
- Order total
- Order date

Text: "John Smith placed an order for $127.50 on March 15th."

JSON:
"""
```

### Approaches

1. **Explicit schema in prompt**: Describe the JSON structure
2. **Few-shot examples**: Show what valid output looks like
3. **Constrained decoding**: Use grammar-based decoding (e.g., Guided JSON, Outlines)
4. **Post-processing**: Parse and validate the model's output

## Prompt Templates

Templates make prompts reusable with variable substitution:

```python
from langchain_core.prompts import PromptTemplate

template = PromptTemplate(
    input_variables=["topic", "style"],
    template="Write a {style} summary about {topic}."
)

prompt = template.format(topic="machine learning", style="concise")
# "Write a concise summary about machine learning."
```

### In Our POC

Our RAG pipeline uses a prompt template:

```python
# app/rag/retrieval.py
def build_rag_prompt(question: str, context: str) -> str:
    return f"""Context:
{context}

Question: {question}

Answer:"""
```

## Delimiter Techniques

Using delimiters helps the model parse input structure:

```python
prompt = """
{context}
===
{instructions}
===
Question: {question}
"""
```

Delimiters like `===`, `---`, or XML tags (`<context>...</context>`) help
the model distinguish between different parts of the prompt.

## Role-Playing Prompts

Setting a specific persona:

```python
system = "You are a sarcastic chemistry professor who explains concepts with movie references."
```

## Attention Steering

Explicitly telling the model what to focus on:

```python
prompt = """
Important: Focus only on the economic impacts, not the environmental effects.

Analyze the economic impacts of climate change policies.
"""
```

## Common Mistakes

| Mistake | Better Approach |
|---------|----------------|
| Too vague | Be specific about format, style, length |
| Contradictory instructions | Keep system and user messages consistent |
| Too long | Trim unnecessary context; use retrieval |
| Hidden in noise | Put key instructions first |
| No output guardrails | Specify format constraints explicitly |

## Best Practices

1. **Be specific** — "Write a 200-word summary" not "Write a summary"
2. **Use delimiters** — Separate context, instructions, and questions clearly
3. **Show examples** — Few-shot for unusual formats
4. **Start simple** — Increase complexity iteratively
5. **Test edge cases** — Try adversarial inputs

## Next Steps

- [Prompt Templates](templates.md) — Building reusable prompts
- [Prompt Injection](injection.md) — Security considerations
- [Best Practices](best-practices.md) — Production guidance
