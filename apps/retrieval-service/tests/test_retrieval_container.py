import pytest
from dishka import AsyncContainer
from retrieval_service.application.use_cases import IndexNewsDocuments, SearchNews
from retrieval_service.main.container import create_container
from retrieval_service.main.settings import RetrievalServiceSettings


def test_retrieval_settings_defaults_and_env_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RETRIEVAL_QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("RETRIEVAL_COLLECTION_NAME", "test_news")
    monkeypatch.setenv("RETRIEVAL_USE_STATIC_EMBEDDINGS", "true")

    settings = RetrievalServiceSettings()

    assert str(settings.qdrant_url) == "http://localhost:6333/"
    assert settings.collection_name == "test_news"
    assert settings.use_static_embeddings is True


@pytest.mark.asyncio
async def test_container_resolves_use_cases_with_fake_components() -> None:
    container: AsyncContainer = create_container(use_fake_components=True)

    try:
        index_use_case = await container.get(IndexNewsDocuments)
        search_use_case = await container.get(SearchNews)
    finally:
        await container.close()

    assert isinstance(index_use_case, IndexNewsDocuments)
    assert isinstance(search_use_case, SearchNews)
