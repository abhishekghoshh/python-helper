"""Minimal Streamlit UI for the Vector DB POC API.

Provides a clean, chat-style interface to:
  - Check API health
  - Generate embeddings
  - Add / batch-add documents (with optional chunking)
  - Search for semantically similar documents
  - List and delete stored documents

Configuration via environment variables:
  API_BASE_URL  – the FastAPI server URL (default http://localhost:8000)
  LOG_LEVEL     – inherited from the API settings, no direct effect here

Run locally:
  poetry run streamlit run streamlit_app.py --server.port 8501

Or via Docker Compose (see docker-compose.yml ``streamlit`` service).
"""

from __future__ import annotations

import os

import httpx
import streamlit as st

# ── Page setup ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Vector DB POC",
    page_icon="🔍",
    layout="centered",
)

# ── Configuration ───────────────────────────────────────────────────────
DEFAULT_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
api_base = st.sidebar.text_input("API Base URL", DEFAULT_URL)

# ── Helper ─────────────────────────────────────────────────────────────


def api_request(
    method: str,
    path: str,
    *,
    json: dict | list | None = None,
    timeout: float = 30.0,
) -> dict | list | None:
    """Send a request to the FastAPI backend and return parsed JSON."""
    url = f"{api_base}{path}"
    try:
        resp = httpx.request(method, url, json=json, timeout=timeout)
    except httpx.ConnectError:
        st.error(f"Cannot reach API at `{api_base}`")
        return None
    if resp.status_code == 204:
        return None
    if resp.status_code >= 400:
        st.error(f"API error {resp.status_code}: {resp.text}")
        return None
    return resp.json()


def check_health() -> dict | None:
    return api_request("GET", "/api/v1/health", timeout=5)


# ── Sidebar ─────────────────────────────────────────────────────────────
st.sidebar.header("Vector DB POC")
page = st.sidebar.radio(
    "Navigation",
    ["🔍 Search", "📄 Add Document", "📋 List Documents", "🏠 About"],
)

# ── Health banner ───────────────────────────────────────────────────────
health = check_health()
if health:
    st.sidebar.success(
        f"● Connected\n"
        f"Model: {health['embedding_model']}\n"
        f"Dim: {health['embedding_dim']}"
    )
else:
    st.sidebar.error("● API unreachable")

# ── About ───────────────────────────────────────────────────────────────
if page == "🏠 About":
    st.title("Vector DB POC")
    st.markdown(
        """
        This is a minimal Streamlit interface for the Vector DB POC API.

        **Endpoints demonstrated:**
        - **Health** (`/health`) — checks service and Qdrant connectivity
        - **Embed** (`/embed`) — converts text into a dense embedding vector
        - **Documents** (`/documents/`) — stores, lists, searches, and deletes documents
        - **Search** (`/search`) — semantic similarity search over stored vectors

        The backend is a FastAPI service backed by Qdrant. The Streamlit app
        communicates with it via plain HTTP requests using `httpx`.
        """
    )
    st.code(
        """# Start the backend first:
docker-compose up -d api qdrant

# Then run this app:
poetry run streamlit run streamlit_app.py --server.port 8501
        """,
        language="bash",
    )

# ── Search ──────────────────────────────────────────────────────────────
elif page == "🔍 Search":
    st.title("Semantic Search")
    st.caption("Type a query — the API will embed it and find similar documents.")

    with st.form("search-form"):
        query = st.text_input("Query", placeholder="e.g. How do vector databases work?")
        col1, col2 = st.columns(2)
        with col1:
            top_k = st.slider("Top K", 1, 20, 5)
        with col2:
            score_threshold = st.slider(
                "Score threshold", 0.0, 1.0, 0.0, help="Minimum similarity score"
            )
        submitted = st.form_submit_button("Search", type="primary")

    if submitted and query:
        with st.spinner("🧠 Embedding query and searching..."):
            results = api_request(
                "POST",
                "/api/v1/search",
                json={"query": query, "top_k": top_k, "score_threshold": score_threshold},
            )
        if results:
            hits = results.get("hits", [])
            st.subheader(f"Results ({len(hits)} found)")
            for hit in hits:
                score = hit.get("score", 0)
                with st.container():
                    cols = st.columns([1, 8])
                    with cols[0]:
                        st.metric("Score", f"{score:.3f}")
                    with cols[1]:
                        st.markdown(f"**{hit['id']}**")
                        st.markdown(hit.get("text", "")[:300])
                        if hit.get("metadata"):
                            st.caption(f"Metadata: {hit['metadata']}")
                    st.divider()
            if not hits:
                st.info("No results above the score threshold.")

# ── Add Document ───────────────────────────────────────────────────────
elif page == "📄 Add Document":
    st.title("Add Document")
    st.caption("Store text for later semantic search. Optionally chunk long text.")

    with st.form("add-doc-form"):
        doc_id = st.text_input("Document ID", placeholder="e.g. doc-1")
        text = st.text_area("Text", height=150, placeholder="Enter document text...")
        metadata_str = st.text_input(
            "Metadata (JSON)",
            placeholder='{"category": "tutorial"}',
        )
        col1, col2 = st.columns(2)
        with col1:
            chunk_size = st.number_input(
                "Chunk size (0 = no chunking)", min_value=0, value=0
            )
        with col2:
            chunk_overlap = st.number_input(
                "Chunk overlap (chars)", min_value=0, value=0, disabled=chunk_size == 0
            )
        submitted = st.form_submit_button("Store", type="primary")

    if submitted:
        if not doc_id or not text:
            st.error("Document ID and Text are required.")
        else:
            import json as _json

            metadata = {}
            if metadata_str:
                try:
                    metadata = _json.loads(metadata_str)
                except _json.JSONDecodeError:
                    st.error("Invalid JSON in Metadata field.")
                    st.stop()

            payload: dict = {"id": doc_id, "text": text, "metadata": metadata}
            if chunk_size > 0:
                payload["chunk_size"] = chunk_size
                payload["chunk_overlap"] = chunk_overlap if chunk_overlap else 0

            with st.spinner("📦 Embedding and storing..."):
                result = api_request("POST", "/api/v1/documents/", json=payload)
            if result:
                st.success(
                    f"Stored **{result['id']}** — "
                    f"{result.get('inserted_chunks', 1)} chunk(s) embedded and indexed."
                )

# ── List Documents ───────────────────────────────────────────────────────
elif page == "📋 List Documents":
    st.title("Stored Documents")
    st.caption("All document chunks currently in the vector database.")

    limit = st.number_input("Limit", min_value=1, max_value=500, value=100)

    if st.button("Refresh"):
        with st.spinner("Fetching documents..."):
            result = api_request(
                "GET", f"/api/v1/documents/?limit={limit}"
            )
        if result is None:
            st.warning("Cannot reach the API. Check the API Base URL in the sidebar.")
        else:
            docs = result.get("documents", [])
            if not docs:
                st.info("No documents found. Add documents from the 'Add Document' page.")
            else:
                st.subheader(f"Documents ({len(docs)})")
                for doc in docs:
                    with st.container():
                        cols = st.columns([2, 8])
                        with cols[0]:
                            st.code(doc["id"], language="text")
                        with cols[1]:
                            st.markdown(f"**{doc['text'][:200]}**")
                            if doc.get("metadata"):
                                st.caption(f"Metadata: {doc['metadata']}")
                        st.divider()

            if st.button("Delete all (use with caution)"):
                with st.spinner("Deleting..."):
                    for doc in docs:
                        api_request("DELETE", f"/api/v1/documents/{doc['id']}")
                st.success(f"Deleted {len(docs)} documents.")
                st.rerun()

            if result.get("next_page"):
                st.info("More results available — increase the limit.")
