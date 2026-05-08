from pathlib import Path

import pytest
from dishka import AsyncContainer
from news_service.application.ports import NewsIndexTaskQueue
from news_service.application.use_cases import (
    EnqueueIndexNewsDataset,
    IndexNewsDataset,
    PreviewNews,
)
from news_service.main.container import create_container
from news_service.main.settings import NewsServiceSettings


def test_news_settings_defaults_and_env_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NEWS_SERVICE_NEWS_DATASET_PATH", raising=False)
    settings = NewsServiceSettings()

    assert settings.service_name == "news-service"
    assert settings.news_dataset_path == Path("data/raw/economic_news.csv")
    assert str(settings.retrieval_service_url) == "http://retrieval-service:8000/"
    assert settings.default_index_limit == 100
    assert str(settings.redis_url) == "redis://redis:6379/0"
    assert settings.task_queue_name == "news-indexing"
    assert settings.index_events_channel == "news.index.events"


def test_news_settings_reads_prefixed_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEWS_SERVICE_NEWS_DATASET_PATH", "data/raw/demo.csv")
    monkeypatch.setenv("NEWS_SERVICE_RETRIEVAL_SERVICE_URL", "http://localhost:8002")
    monkeypatch.setenv("NEWS_SERVICE_DEFAULT_INDEX_LIMIT", "25")
    monkeypatch.setenv("NEWS_SERVICE_REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("NEWS_SERVICE_TASK_QUEUE_NAME", "custom-news-indexing")
    monkeypatch.setenv("NEWS_SERVICE_INDEX_EVENTS_CHANNEL", "custom.news.index.events")

    settings = NewsServiceSettings()

    assert settings.news_dataset_path == Path("data/raw/demo.csv")
    assert str(settings.retrieval_service_url) == "http://localhost:8002/"
    assert settings.default_index_limit == 25
    assert str(settings.redis_url) == "redis://localhost:6379/1"
    assert settings.task_queue_name == "custom-news-indexing"
    assert settings.index_events_channel == "custom.news.index.events"


@pytest.mark.asyncio
async def test_container_resolves_use_cases_with_fake_components() -> None:
    container: AsyncContainer = create_container(use_fake_components=True)
    try:
        async with container() as request_container:
            preview = await request_container.get(PreviewNews)
            index = await request_container.get(IndexNewsDataset)
            enqueue = await request_container.get(EnqueueIndexNewsDataset)
            queue = await request_container.get(NewsIndexTaskQueue)
    finally:
        await container.close()

    assert isinstance(preview, PreviewNews)
    assert isinstance(index, IndexNewsDataset)
    assert isinstance(enqueue, EnqueueIndexNewsDataset)
    assert callable(queue.enqueue)
