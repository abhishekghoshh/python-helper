"""
RAG step 3 — Generation: calling the LLM with retrieved context.

The flow:
    Prompt + Context → LLM → Generated Answer

This module assembles the final prompt (system + context + question)
and calls the LLM service to generate a response.

It demonstrates how retrieved context is injected into the prompt to
"ground" the LLM's response — reducing hallucinations and providing
up-to-date, domain-specific information.
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.llm.service import LLMService
from app.models.schemas import ChatMessage, MessageRole, RAGResponse, SearchHit
from app.rag.retrieval import build_context, build_rag_prompt

logger = logging.getLogger(__name__)


async def generate_answer(
    question: str,
    hits: list[SearchHit],
    llm_service: LLMService,
    model: str | None = None,
    temperature: float | None = None,
) -> RAGResponse:
    """Generate an answer using the RAG pipeline.

    Args:
        question: The user's query.
        hits: Retrieved context chunks from the vector DB.
        llm_service: LLM service instance.
        model: Optional model override.
        temperature: Optional temperature override.

    Returns:
        RAGResponse with answer, sources, and context.
    """
    # Step 1: Build context string from retrieved hits
    context = build_context(hits)
    logger.info(
        "RAG generation — question=%s, hits=%d, context_chars=%d",
        question[:60],
        len(hits),
        len(context),
    )

    # Step 2: Construct chat messages with proper roles
    messages: list[ChatMessage] = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content=(
                "You are a helpful assistant that answers questions "
                "based on the provided context.\n"
                "If you cannot answer the question from the context, "
                "say so honestly.\n"
                "Do not make up facts that are not supported by the context."
                "Cite the source numbers from the context when you use them."
            ),
        ),
    ]

    if context:
        messages.append(
            ChatMessage(
                role=MessageRole.USER,
                content=f"""Context:
{context}

Question: {question}

Please answer the question using only the information provided in the context above.
Cite the source numbers when you use them.
""",
            )
        )
    else:
        messages.append(
            ChatMessage(
                role=MessageRole.USER,
                content=f"Question: {question}\n\nAnswer:",
            )
        )

    # Step 3: Call the LLM
    logger.info("Calling LLM — model=%s, temperature=%s", model or settings.llm_model, temperature)
    response = await llm_service.generate_response(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=settings.llm_max_tokens,
    )
    logger.info("LLM response received — length=%d", len(response.content))

    return RAGResponse(
        answer=response.content,
        sources=hits,
        context=context,
    )


def generate_simple_answer(question: str, context: str) -> str:
    """Generate an answer without calling an LLM — for demos and testing.

    This demonstrates the prompt construction without needing an API key.
    Returns the assembled prompt so learners can see what the LLM receives.
    """
    return build_rag_prompt(question, context)
