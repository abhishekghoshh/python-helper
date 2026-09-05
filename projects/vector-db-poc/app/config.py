from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    collection_name: str = "demo"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    qdrant_distance: str = "cosine"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
