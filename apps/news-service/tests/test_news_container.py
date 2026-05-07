import sys
from pathlib import Path

import pytest
from dishka import AsyncContainer

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from news_service.application.use_cases import IndexNewsDataset, PreviewNews
from news_service.main.container import create_container
from news_service.main.settings import NewsServiceSettings


def test_news_settings_defaults_and_env_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NEWS_SERVICE_NEWS_DATASET_PATH", raising=False)
    settings = NewsServiceSettings()

    assert settings.service_name == "news-service"
    assert settings.news_dataset_path == Path("data/raw/economic_news.csv")
    assert str(settings.retrieval_service_url) == "http://retrieval-service:8000/"
    assert settings.default_index_limit == 100


def test_news_settings_reads_prefixed_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEWS_SERVICE_NEWS_DATASET_PATH", "data/raw/demo.csv")
    monkeypatch.setenv("NEWS_SERVICE_RETRIEVAL_SERVICE_URL", "http://localhost:8002")
    monkeypatch.setenv("NEWS_SERVICE_DEFAULT_INDEX_LIMIT", "25")

    settings = NewsServiceSettings()

    assert settings.news_dataset_path == Path("data/raw/demo.csv")
    assert str(settings.retrieval_service_url) == "http://localhost:8002/"
    assert settings.default_index_limit == 25


@pytest.mark.asyncio
async def test_container_resolves_use_cases_with_fake_components() -> None:
    container: AsyncContainer = create_container(use_fake_components=True)
    try:
        async with container() as request_container:
            preview = await request_container.get(PreviewNews)
            index = await request_container.get(IndexNewsDataset)
    finally:
        await container.close()

    assert isinstance(preview, PreviewNews)
    assert isinstance(index, IndexNewsDataset)
