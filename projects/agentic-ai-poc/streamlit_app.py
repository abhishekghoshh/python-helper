"""Minimal Streamlit UI for the Agentic AI POC HTTP API.

Run locally (with the API already up on port 8000):

    streamlit run streamlit_app.py

Or with Docker via `docker-compose up` (the `ui` service sets API_URL to the
internal `api` host).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import requests
import streamlit as st

DEFAULT_API_BASE = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")


def api_base() -> str:
    return st.session_state.api_base.rstrip("/")


def _request(method: str, path: str, **kwargs: Any) -> requests.Response:
    return requests.request(method, f"{api_base()}{path}", timeout=120, **kwargs)


def _sse_chat(message: str):
    """Stream a chat message from /api/v1/chat/stream, yielding SSE events."""
    with requests.post(
        f"{api_base()}/api/v1/chat/stream",
        json={"message": message, "stream": True},
        headers={"Accept": "text/event-stream"},
        stream=True,
        timeout=120,
    ) as r:
        r.raise_for_status()
        event: dict[str, Any] | None = None
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            try:
                event = json.loads(line[len("data:"):].strip())
            except json.JSONDecodeError:
                continue
            yield event


# --------------------------------------------------------------------------- #
# Sidebar: connection + tools + knowledge base
# --------------------------------------------------------------------------- #
st.sidebar.header("Agentic AI POC")
if "api_base" not in st.session_state:
    st.session_state.api_base = DEFAULT_API_BASE
st.session_state.api_base = st.sidebar.text_input(
    "API base URL", value=st.session_state.api_base, key="api_base_in"
)
st.sidebar.caption("_relative paths are served from the base above_")

if st.sidebar.button("Check health"):
    try:
        ok = _request("GET", "/api/v1/health")
        ok.raise_for_status()
        data = ok.json()
        st.sidebar.success(
            f"OK — {data.get('service','api')} · "
            f"{'mock' if data.get('simulated_mode') else 'real'} LLM"
        )
    except Exception as exc:
        st.sidebar.error(f"Could not reach the API: {exc}")

st.sidebar.subheader("Tools")
if st.sidebar.button("List tools"):
    try:
        r = _request("GET", "/api/v1/tools")
        r.raise_for_status()
        for tool in r.json().get("tools", []):
            st.sidebar.markdown(f"- **{tool['name']}** — {tool.get('description', '')}")
    except Exception as exc:
        st.sidebar.error(str(exc))

st.sidebar.subheader("Knowledge base (RAG)")
doc_text = st.sidebar.text_area(
    "Document text",
    placeholder="Paste text to ingest into the vector store, then click Ingest.",
    height=120,
    key="doc_text",
)
doc_id = st.sidebar.text_input("Document ID (optional)", key="doc_id")
if st.sidebar.button("Ingest"):
    docs = [
        {"id": doc_id or f"doc-{int(time.time())}", "content": doc_text.strip()}
        for _ in [0]
        if doc_text.strip()
    ]
    if not docs:
        st.sidebar.warning("Nothing to ingest.")
    else:
        try:
            r = _request("POST", "/api/v1/rag/ingest", json={"documents": docs})
            r.raise_for_status()
            st.sidebar.success(r.json().get("message", "Ingested."))
        except Exception as exc:
            st.sidebar.error(str(exc))


# --------------------------------------------------------------------------- #
# Main: chat
# --------------------------------------------------------------------------- #
st.title("Agentic AI — Chat")

if "messages" not in st.session_state:
    st.session_state.messages: list[dict[str, str]] = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask the agent..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        answer = ""
        tool_lines: list[str] = []
        thinking = st.empty()
        thinking.info("Thinking…")

        try:
            for event in _sse_chat(prompt):
                etype = event.get("type", "")
                if etype == "start":
                    thinking.info(event.get("content") or "Starting…")
                elif etype == "tool_call":
                    tc = event.get("tool_call") or {}
                    name = tc.get("name", "?")
                    args = tc.get("arguments", "")
                    tool_lines.append(f"• **{name}** called with `{args}`")
                    thinking.info(f"Using `{name}`…")
                elif etype == "tool_result":
                    tr = event.get("tool_result") or {}
                    status = "✅ OK" if tr.get("success") else "❌ failed"
                    tool_lines.append(f"  → {status} `{tr.get('tool_name', '')}`")
                    thinking.info(f"Waiting for `{tr.get('tool_name', '')}`…")
                elif etype == "end":
                    if event.get("error"):
                        answer += f"\n\n⚠️ {event['error']}"
                    else:
                        answer = event.get("answer") or event.get("content") or answer
                    thinking.empty()
        except Exception as exc:
            thinking.empty()
            answer = f"⚠️ Could not reach the agent: {exc}"

        if tool_lines:
            for line in tool_lines:
                st.markdown(line)
        st.markdown(answer or "…")

    st.session_state.messages.append({"role": "assistant", "content": answer})
