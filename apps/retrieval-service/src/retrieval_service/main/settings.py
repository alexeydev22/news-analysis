from economic_news_framework.settings import BaseServiceSettings
from pydantic import AnyHttpUrl, Field
from pydantic_settings import SettingsConfigDict


class RetrievalServiceSettings(BaseServiceSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="RETRIEVAL_",
        extra="ignore",
    )

    service_name: str = "retrieval-service"
    version: str = "0.1.0"
    qdrant_url: AnyHttpUrl = AnyHttpUrl("http://qdrant:6333")
    collection_name: str = "economic_news"
    embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dimension: int = Field(default=384, ge=1)
    use_static_embeddings: bool = False
