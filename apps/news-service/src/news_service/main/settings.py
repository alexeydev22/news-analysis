from pathlib import Path

from economic_news_framework.settings import BaseServiceSettings
from pydantic import AnyHttpUrl, Field
from pydantic_settings import SettingsConfigDict


class NewsServiceSettings(BaseServiceSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="NEWS_SERVICE_",
        extra="ignore",
    )

    service_name: str = "news-service"
    news_dataset_path: Path = Path("data/raw/economic_news.csv")
    retrieval_service_url: AnyHttpUrl = AnyHttpUrl("http://retrieval-service:8000")
    retrieval_service_timeout_seconds: float = Field(default=10.0, gt=0)
    default_index_limit: int = Field(default=100, ge=1, le=1000)
