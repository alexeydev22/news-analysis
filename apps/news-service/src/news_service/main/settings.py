from pathlib import Path

from economic_news_framework.settings import BaseServiceSettings
from pydantic import AnyHttpUrl, Field, RedisDsn
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
    dataset_upload_dir: Path = Path("data/uploads")
    active_dataset_file: Path = Path("data/uploads/active_dataset.json")
    upload_max_bytes: int = Field(default=50 * 1024 * 1024, ge=1)
    retrieval_service_url: AnyHttpUrl = AnyHttpUrl("http://retrieval-service:8000")
    retrieval_service_timeout_seconds: float = Field(default=10.0, gt=0)
    default_index_limit: int = Field(default=100, ge=1, le=1000)
    redis_url: RedisDsn = RedisDsn("redis://redis:6379/0")
    task_queue_name: str = Field(default="news-indexing", min_length=1)
    task_result_ttl_seconds: int = Field(default=3600, ge=60)
    index_events_channel: str = Field(default="news.index.events", min_length=1)
