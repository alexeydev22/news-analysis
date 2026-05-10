from pathlib import Path

import pytest
from dishka import AsyncContainer
from news_service.application.ports import DatasetStorage, NewsIndexTaskQueue, NewsSource
from news_service.application.use_cases import (
    ActivateNewsDataset,
    EnqueueIndexNewsDataset,
    GetActiveNewsDataset,
    IndexNewsDataset,
    ListNewsDatasets,
    PreviewNews,
    UploadNewsDataset,
)
from news_service.main.container import ActiveDatasetCsvNewsSource, create_container
from news_service.main.settings import NewsServiceSettings


def test_news_settings_defaults_and_env_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NEWS_SERVICE_NEWS_DATASET_PATH", raising=False)
    monkeypatch.delenv("NEWS_SERVICE_DATASET_UPLOAD_DIR", raising=False)
    monkeypatch.delenv("NEWS_SERVICE_ACTIVE_DATASET_FILE", raising=False)
    monkeypatch.delenv("NEWS_SERVICE_UPLOAD_MAX_BYTES", raising=False)
    settings = NewsServiceSettings()

    assert settings.service_name == "news-service"
    assert settings.news_dataset_path == Path("data/raw/economic_news.csv")
    assert settings.dataset_upload_dir == Path("data/uploads")
    assert settings.active_dataset_file == Path("data/uploads/active_dataset.json")
    assert settings.upload_max_bytes == 50 * 1024 * 1024
    assert str(settings.retrieval_service_url) == "http://retrieval-service:8000/"
    assert settings.default_index_limit == 100
    assert str(settings.redis_url) == "redis://redis:6379/0"
    assert settings.task_queue_name == "news-indexing"
    assert settings.index_events_channel == "news.index.events"


def test_news_settings_reads_prefixed_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEWS_SERVICE_NEWS_DATASET_PATH", "data/raw/demo.csv")
    monkeypatch.setenv("NEWS_SERVICE_DATASET_UPLOAD_DIR", "tmp/uploads")
    monkeypatch.setenv("NEWS_SERVICE_ACTIVE_DATASET_FILE", "tmp/uploads/active.json")
    monkeypatch.setenv("NEWS_SERVICE_UPLOAD_MAX_BYTES", "128")
    monkeypatch.setenv("NEWS_SERVICE_RETRIEVAL_SERVICE_URL", "http://localhost:8002")
    monkeypatch.setenv("NEWS_SERVICE_DEFAULT_INDEX_LIMIT", "25")
    monkeypatch.setenv("NEWS_SERVICE_REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("NEWS_SERVICE_TASK_QUEUE_NAME", "custom-news-indexing")
    monkeypatch.setenv("NEWS_SERVICE_INDEX_EVENTS_CHANNEL", "custom.news.index.events")

    settings = NewsServiceSettings()

    assert settings.news_dataset_path == Path("data/raw/demo.csv")
    assert settings.dataset_upload_dir == Path("tmp/uploads")
    assert settings.active_dataset_file == Path("tmp/uploads/active.json")
    assert settings.upload_max_bytes == 128
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
            upload = await request_container.get(UploadNewsDataset)
            list_datasets = await request_container.get(ListNewsDatasets)
            activate = await request_container.get(ActivateNewsDataset)
            get_active = await request_container.get(GetActiveNewsDataset)
            storage = await request_container.get(DatasetStorage)
            queue = await request_container.get(NewsIndexTaskQueue)
    finally:
        await container.close()

    assert isinstance(preview, PreviewNews)
    assert isinstance(index, IndexNewsDataset)
    assert isinstance(enqueue, EnqueueIndexNewsDataset)
    assert isinstance(upload, UploadNewsDataset)
    assert isinstance(list_datasets, ListNewsDatasets)
    assert isinstance(activate, ActivateNewsDataset)
    assert isinstance(get_active, GetActiveNewsDataset)
    assert callable(storage.save_upload)
    assert callable(queue.enqueue)


@pytest.mark.asyncio
async def test_container_resolves_active_dataset_source_for_real_components(
    tmp_path: Path,
) -> None:
    settings = NewsServiceSettings(
        news_dataset_path=tmp_path / "fallback.csv",
        dataset_upload_dir=tmp_path / "uploads",
        active_dataset_file=tmp_path / "uploads" / "active_dataset.json",
    )
    container: AsyncContainer = create_container(settings=settings)
    try:
        async with container() as request_container:
            source = await request_container.get(NewsSource)
    finally:
        await container.close()

    assert isinstance(source, ActiveDatasetCsvNewsSource)
