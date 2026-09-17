# Evaluation

## Why Evaluate LLM Applications?

Traditional software has deterministic behavior — the same input always
produces the same output. LLM applications are **probabilistic** — outputs
vary, so evaluating quality is challenging but critical.

## What to Evaluate

### For RAG Systems

| Metric | What it Measures |
|--------|-----------------|
| **Context Precision** | Of retrieved documents, how many are relevant |
| **Context Recall** | Of all relevant documents, how many were retrieved |
| **Answer Faithfulness** | Does the answer match the retrieved context? |
| **Answer Relevancy** | Does the answer address the user's question? |
| **Answer Correctness** | Is the answer factually accurate? |

### For LLM Chatbots

| Metric | What it Measures |
|--------|-----------------|
| **Coherence** | Is the response well-formed and logical? |
| **Relevance** | Does it address the user's question? |
| **Factuality** | Are the claims accurate? |
| **Safety** | Does it avoid harmful content? |
| **Helpfulness** | Does it actually help the user? |

## Evaluation Approaches

### 1. Human Evaluation

Humans rate responses on various dimensions. Expensive but the gold standard.

```python
# Rate this response:
# 1-5: How accurate is the answer?
# 1-5: How helpful is the response?
# 1-5: How fluent is the language?
```

### 2. Automated Metrics

#### BLEU, ROUGE, METEOR

Compare generated text to reference (human-written) answers:

```python
from rouge_score import rouge_scorer

scorer = rouge_scorer.RougeScorer()
score = scorer.score(
    target="The capital of France is Paris.",    # Reference
    prediction="Paris is the capital of France.", # LLM output
)
# ROUGE-L: 0.92 (high overlap)
```

**Limitations**: These measure surface similarity, not factual correctness.

#### BERTScore

Uses embeddings to compare meaning, not just exact word matches:

```python
from bert_score import score

p, r, f = score(
    cands=["The capital is Paris."],
    refs=["The capital of France is Paris."],
    lang="en",
)
# Higher score = more semantically similar
```

### 3. LLM-as-a-Judge

Use an LLM (like GPT-4) to evaluate another LLM's output:

```python
eval_prompt = f"""
Rate this QA pair on a scale of 1-5:
- Accuracy: Does the answer correctly address the question?
- Completeness: Does the answer cover all key points?
- Faithfulness: Does the answer only contain supported facts?

Question: {question}
Answer: {answer}
Context: {context}

Rating: """
```

**Pros**: Captures nuanced quality
**Cons**: LLM evaluator may have its own biases

## RAG-Specific Evaluation

### Retrieval Evaluation

```python
def evaluate_retrieval(
    query: str,
    ground_truth_docs: list[str],  # Which docs SHOULD be retrieved
    retrieved_docs: list[str],     # Which docs WERE retrieved
) -> float:
    """Compute recall@K."""
    relevant_retrieved = len(set(ground_truth_docs) & set(retrieved_docs))
    return relevant_retrieved / len(ground_truth_docs)
```

### End-to-End Evaluation

Create a test set of questions with known answers:

```python
test_cases = [
    {
        "question": "What is RAG?",
        "expected_answer_contains": ["retrieval-augmented", "generation"],
        "expected_cited_source": True,
    },
    {
        "question": "Who created Python?",
        "expected_answer_contains": ["Guido van Rossum"],
        "expected_cited_source": True,
    },
]

for case in test_cases:
    response = await rag_pipeline.query(RAGRequest(question=case["question"]))
    # Check if response meets expectations
```

## In Our POC

The test suite includes basic functional tests:

```python
# tests/test_rag.py
async def test_rag_query():
    """Test the complete RAG flow."""
    # Ingest a document
    await ingest_documents([...])
    
    # Query
    response = await rag_pipeline.query(RAGRequest(question="..."))
    
    # Assert response exists
    assert response.answer is not None
    assert len(response.sources) > 0
```

## Metrics Dashboard

Track evaluation results over time:

| Metric | Baseline | Current | Target |
|--------|----------|---------|--------|
| Answer Relevance | 3.2/5 | 3.8/5 | 4.5/5 |
| Context Recall@5 | 0.65 | 0.78 | 0.90 |
| Hallucination Rate | 0.15 | 0.08 | <0.05 |

## Next Steps

- [Guardrails](guardrails.md) — Ensuring safe outputs
- [Hallucination](hallucination.md) — Measuring factual accuracy
- [Observability](observability.md) — Monitoring in production
