"""Tests for RAG pipeline components."""

from app.models.schemas import Document, SearchHit
from app.rag.generation import generate_simple_answer
from app.rag.ingestion import chunk_document
from app.rag.retrieval import build_context, build_rag_prompt


class TestBuildContext:
    def test_empty_hits_returns_empty(self):
        assert build_context([]) == ""

    def test_single_hit(self):
        hits = [SearchHit(id="1", score=0.9, text="Hello world")]
        result = build_context(hits)
        assert "Hello world" in result
        assert "[Source 1]" in result
        assert "0.9000" in result

    def test_multiple_hits_with_separator(self):
        hits = [
            SearchHit(id="1", score=0.9, text="Text A"),
            SearchHit(id="2", score=0.8, text="Text B"),
        ]
        result = build_context(hits)
        assert "[Source 1]" in result
        assert "[Source 2]" in result
        assert "---" in result
        assert "Text A" in result
        assert "Text B" in result

    def test_truncation(self):
        hits = [
            SearchHit(id="1", score=0.9, text="A" * 2000),
            SearchHit(id="2", score=0.8, text="B" * 2000),
        ]
        result = build_context(hits, max_chars=500)
        assert len(result) <= 500 + 100  # Allow some overhead


class TestBuildRagPrompt:
    def test_with_context(self):
        context = "[Source 1] Some context here."
        prompt = build_rag_prompt("What is AI?", context)
        assert "What is AI?" in prompt
        assert "Some context here" in prompt
        assert "Answer based on" in prompt.lower() or "based" in prompt.lower()

    def test_without_context(self):
        prompt = build_rag_prompt("Hello there", "")
        assert "Hello there" in prompt

    def test_system_prompt_present(self):
        prompt = build_rag_prompt("Question", "Context")
        assert "context" in prompt.lower()


class TestGenerateSimpleAnswer:
    def test_returns_prompt(self):
        result = generate_simple_answer("What is ML?", "ML stands for machine learning.")
        assert "What is ML?" in result
        assert "ML stands for machine learning" in result

    def test_empty_context(self):
        result = generate_simple_answer("What is ML?", "")
        assert "What is ML?" in result


class TestChunkDocument:
    def test_short_document_single_chunk(self):
        doc = Document(id="d1", content="Short text about AI.", metadata={})
        chunks = chunk_document(doc)
        assert len(chunks) == 1
        assert chunks[0].document_id == "d1"
        assert chunks[0].chunk_index == 0

    def test_metadata_preserved(self):
        doc = Document(
            id="d1",
            content="A" * 2000,
            metadata={"category": "tech", "source": "manual"},
        )
        chunks = chunk_document(doc)
        for chunk in chunks:
            assert chunk.metadata["category"] == "tech"
            assert chunk.metadata["source"] == "manual"

    def test_chunk_ids_contain_document_id(self):
        doc = Document(id="my-doc", content="A" * 2000, metadata={})
        chunks = chunk_document(doc)
        for chunk in chunks:
            assert "my-doc" in chunk.id
