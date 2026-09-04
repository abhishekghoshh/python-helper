from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """Wraps a sentence-transformers model to produce dense embeddings."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model: SentenceTransformer | None = None

    def load(self) -> None:
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)

    def embed(self, text: str) -> list[float]:
        self.load()
        assert self.model is not None
        vector = self.model.encode(text, convert_to_numpy=True)
        return vector.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self.load()
        assert self.model is not None
        vectors = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return vectors.tolist()

    @property
    def dimension(self) -> int:
        self.load()
        assert self.model is not None
        return self.model.get_sentence_embedding_dimension()
