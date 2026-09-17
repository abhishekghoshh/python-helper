"""Streamlit frontend for the GenAI POC API.

A minimal UI that communicates with the FastAPI backend via REST calls.
Demonstrates the GenAI workflow: LLM chat, embeddings, RAG ingest/search/query,
and a no-key demo.

Run locally:
    poetry run streamlit run streamlit_app.py

Or via Docker:
    docker compose up streamlit
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import requests
import streamlit as st
from streamlit.logger import get_logger

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_URL = os.environ.get("API_URL", "http://localhost:8000")

logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _api(path: str, **kwargs: Any) -> dict | None:
    """Call the backend API and return parsed JSON (or None on error)."""
    url = f"{API_URL}{path}"
    try:
        resp = requests.post(url, timeout=30, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        st.error(f"Cannot connect to the API at `{API_URL}`. Is the backend running?")
        logger.error("Connection error: %s", url)
        return None
    except requests.HTTPError as exc:
        st.error(f"API error ({exc.response.status_code if exc.response else '?'}): {exc}")
        logger.error("API error on %s: %s", url, exc)
        return None
    except Exception as exc:
        st.error(f"Unexpected error: {exc}")
        logger.error("Unexpected error on %s: %s", url, exc)
        return None


def _api_get(path: str, params: dict | None = None) -> dict | None:
    """Call the backend API (GET) and return parsed JSON."""
    url = f"{API_URL}{path}"
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        st.error(f"Cannot connect to the API at `{API_URL}`. Is the backend running?")
        return None
    except requests.HTTPError as exc:
        st.error(f"API error ({exc.response.status_code if exc.response else '?'}): {exc}")
        return None
    except Exception as exc:
        st.error(f"Unexpected error: {exc}")
        return None


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title(" GenAI POC")
st.sidebar.caption(f"Backend: `{API_URL}`")

api_url = st.sidebar.text_input("API URL", value=API_URL, key="api_url")
if api_url != API_URL:
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("""
**Endpoints used:**
- `/api/v1/llm/generate` — Chat with the LLM
- `/api/v1/embeddings/generate` — Text → vector
- `/api/v1/embeddings/similarity` — Compare two texts
- `/api/v1/rag/ingest` — Add documents
- `/api/v1/rag/search` — Find relevant chunks
- `/api/v1/rag/query` — Full RAG answer
- `/api/v1/rag/demo` — See prompt without LLM (no key needed)
""")

# ---------------------------------------------------------------------------
# Chat tab
# ---------------------------------------------------------------------------


def tab_chat() -> None:
    st.header("Chat with the LLM")

    model = st.text_input("Model", value="gpt-3.5-turbo", key="chat_model")
    temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1, key="chat_temp")
    max_tokens = st.number_input("Max tokens", 1, 16384, 1024, key="chat_tokens")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history: list[dict] = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask the LLM a question..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            *st.session_state.chat_history,
        ]
        with st.chat_message("assistant"):
            with st.spinner("Generating..."):
                result = _api(
                    "/api/v1/llm/generate",
                    json={
                        "messages": messages,
                        "model": model,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                if result:
                    content = result.get("content", "")
                    st.markdown(content)
                    st.session_state.chat_history.append({"role": "assistant", "content": content})
                    if result.get("usage"):
                        u = result["usage"]
                        st.sidebar.caption(
                            f"Tokens: {u.get('total_tokens', '?')} total "
                            f"({u.get('prompt_tokens', '?')} prompt, "
                            f"{u.get('completion_tokens', '?')} completion)"
                        )


# ---------------------------------------------------------------------------
# Embed tab
# ---------------------------------------------------------------------------


def tab_embeddings() -> None:
    st.header("Embeddings")
    st.caption("Convert text to vectors and compute similarity")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Generate Embedding")
        embed_text = st.text_area("Text", "Machine learning is a subset of AI.", key="embed_text")
        if st.button("Embed Text", key="btn_embed"):
            result = _api("/api/v1/embeddings/generate", json={"text": embed_text})
            if result:
                embedding = result["embedding"]
                st.write(f"**Model:** {result['model']}")
                st.write(f"**Dimensions:** {result['dimensions']}")
                st.write(f"**Vector (first 10):** {embedding[:10]}")
                st.download_button(
                    "Download vector (JSON)",
                    json.dumps(embedding),
                    file_name="embedding.json",
                )

    with col2:
        st.subheader("Similarity")
        text_a = st.text_area("Text A", "The cat sat on the mat.", key="sim_a")
        text_b = st.text_area("Text B", "A feline rested on a rug.", key="sim_b")
        metric = st.radio("Metric", ["cosine", "euclidean", "dot"], key="sim_metric")
        if st.button("Compute Similarity", key="btn_sim"):
            result = _api(
                "/api/v1/embeddings/similarity",
                json={
                    "text_a": text_a,
                    "text_b": text_b,
                    "metric": metric,
                },
            )
            if result:
                st.metric("Cosine", f"{result['cosine']:.4f}")
                st.metric("Euclidean", f"{result['euclidean']:.4f}")
                st.metric("Dot Product", f"{result['dot_product']:.4f}")


# ---------------------------------------------------------------------------
# RAG tab
# ---------------------------------------------------------------------------


def tab_rag() -> None:
    st.header(" Retrieval-Augmented Generation")

    st.subheader("1. Ingest Documents")
    raw_docs = st.text_area(
        "Documents (separate by blank line)",
        "RAG combines retrieval and generation to produce grounded answers.\n\n"
        "Machine learning is a subset of AI that learns patterns from data.",
        key="ingest_docs",
    )
    if st.button("Ingest Documents", key="btn_ingest"):
        docs = [{"content": d.strip()} for d in raw_docs.split("\n\n") if d.strip()]
        result = _api("/api/v1/rag/ingest", json={"documents": docs})
        if result:
            st.success(
                f"Processed {result['documents_processed']} documents → "
                f"{result['chunks_created']} chunks in collection '{result['collection']}'"
            )

    st.markdown("---")
    st.subheader("2. Search Documents (no LLM)")
    search_query = st.text_input("Search query", key="search_query")
    top_k_search = st.slider("Top-K", 1, 20, 5, key="search_k")
    if st.button("Search", key="btn_search"):
        result = _api(
            "/api/v1/rag/search",
            json={
                "question": search_query,
                "top_k": top_k_search,
            },
        )
        if result:
            st.write(f"Found **{len(result['hits'])}** results:")
            for hit in result["hits"]:
                with st.expander(f"Score: {hit['score']:.4f}"):
                    st.markdown(hit["text"])
                    if hit.get("metadata"):
                        st.caption(f"Metadata: {hit['metadata']}")

    st.markdown("---")
    st.subheader("3. Ask a Question (Full RAG)")
    question = st.text_input("Question", key="rag_question")
    top_k_rag = st.slider("Top-K retrieval", 1, 20, 5, key="rag_k")
    use_llm = st.checkbox(
        "I have configured an LLM API key",
        value=False,
        help="Check this box to call the LLM. Uncheck to run retrieval only.",
    )
    if st.button("Query (RAG)", key="btn_query"):
        if use_llm:
            result = _api(
                "/api/v1/rag/query",
                json={
                    "question": question,
                    "top_k": top_k_rag,
                },
            )
            if result:
                st.markdown(result["answer"])
                if result.get("sources"):
                    st.caption(f"Based on {len(result['sources'])} sources")
                    with st.expander("View sources"):
                        for src in result["sources"]:
                            st.markdown(f"**Score {src['score']:.4f}**: {src['text'][:200]}")
        else:
            result = _api(
                "/api/v1/rag/search",
                json={
                    "question": question,
                    "top_k": top_k_rag,
                },
            )
            if result:
                st.info(
                    "Retrieval-only mode (LLM not called). "
                    "Configure an API key and check the box above for full RAG."
                )
                for hit in result["hits"]:
                    with st.expander(f"Score: {hit['score']:.4f}"):
                        st.markdown(hit["text"])


# ---------------------------------------------------------------------------
# Demo tab
# ---------------------------------------------------------------------------


def tab_demo() -> None:
    st.header("RAG Demo (No LLM, No API Key)")
    st.caption("Shows the prompt that would be sent to the LLM — great for learning.")

    question = st.text_input("Question", "What is RAG?", key="demo_question")
    top_k = st.slider("Top-K", 1, 20, 5, key="demo_k")

    if st.button("Run Demo", key="btn_demo"):
        result = _api_get(
            "/api/v1/rag/demo",
            params={
                "question": question,
                "top_k": top_k,
            },
        )
        if result:
            st.write("### Retrieved Chunks")
            chunks = result.get("retrieved_chunks", [])
            if not chunks:
                st.info("No chunks retrieved (vector DB may not be running).")
            for i, chunk in enumerate(chunks):
                with st.expander(f"Chunk {i + 1} (score: {chunk['score']:.4f})"):
                    st.markdown(chunk["text"])

            st.write("### Constructed Context")
            st.code(result.get("context", ""), language="text")

            st.write("### Full Prompt (what would go to the LLM)")
            st.code(result.get("prompt", ""), language="text")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="GenAI POC",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("GenAI Learning Lab")
st.caption("A hands-on POC for learning LLMs, embeddings, vector databases, and RAG.")

tab1, tab2, tab3, tab4 = st.tabs([" Chat", " Embeddings", " RAG", " Demo (no key)"])

with tab1:
    tab_chat()
with tab2:
    tab_embeddings()
with tab3:
    tab_rag()
with tab4:
    tab_demo()
