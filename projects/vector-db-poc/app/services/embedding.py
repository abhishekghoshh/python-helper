"""Sentence-transformers embedding service."""

import logging

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Wraps a sentence-transformers model to produce dense embeddings."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model: SentenceTransformer | None = None
        logger.debug("EmbeddingService initialized for model: %s", model_name)

    def load(self) -> None:
        if self.model is None:
            logger.info("Loading embedding model: %s", self.model_name)
            self.model = SentenceTransformer(self.model_name)
            logger.info(
                "Model '%s' loaded successfully (dimension: %s)",
                self.model_name,
                self.model.get_sentence_embedding_dimension(),
            )

    def embed(self, text: str) -> list[float]:
        self.load()
        logger.debug("Generating embedding for text (%d chars)", len(text))
        assert self.model is not None
        vector = self.model.encode(text, convert_to_numpy=True)
        return vector.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self.load()
        logger.debug("Generating embeddings for %d texts", len(texts))
        assert self.model is not None
        vectors = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return vectors.tolist()

    @property
    def dimension(self) -> int:
        self.load()
        assert self.model is not None
        return self.model.get_sentence_embedding_dimension()
