from pathlib import Path
from typing import Any

from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider
from economic_news_contracts.retrieval import IndexNewsResponse

from news_service.application.ports import NewsSource, RetrievalIndexer
from news_service.application.use_cases import IndexNewsDataset, PreviewNews
from news_service.domain.model import NewsDocument
from news_service.infrastructure.csv_news_source import CsvNewsSource
from news_service.infrastructure.retrieval_client import ZaprosRetrievalIndexer
from news_service.main.settings import NewsServiceSettings


class FakeNewsSource:
    async def load(self, limit: int | None = None) -> list[NewsDocument]:
        documents = [
            NewsDocument(
                id="news-1",
                title="GDP grows",
                text="GDP grew by 2 percent.",
                source="demo",
            ),
        ]
        if limit is None:
            return documents
        return documents[:limit]


class FakeRetrievalIndexer:
    async def index(self, documents: list[NewsDocument]) -> IndexNewsResponse:
        return IndexNewsResponse(indexed_count=len(documents), collection_name="economic_news")


class NewsServiceProvider(Provider):
    def __init__(
        self,
        settings: NewsServiceSettings | None = None,
        *,
        use_fake_components: bool = False,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._use_fake_components = use_fake_components

    @provide(scope=Scope.APP)
    def settings(self) -> NewsServiceSettings:
        return self._settings or NewsServiceSettings()

    @provide(scope=Scope.APP, provides=NewsSource)
    def news_source(self, settings: NewsServiceSettings) -> NewsSource:
        if self._use_fake_components:
            return FakeNewsSource()
        return CsvNewsSource(Path(settings.news_dataset_path))

    @provide(scope=Scope.APP, provides=RetrievalIndexer)
    def retrieval_indexer(self, settings: NewsServiceSettings) -> RetrievalIndexer:
        if self._use_fake_components:
            return FakeRetrievalIndexer()
        return ZaprosRetrievalIndexer(
            base_url=str(settings.retrieval_service_url),
            timeout_seconds=settings.retrieval_service_timeout_seconds,
        )

    @provide(scope=Scope.APP)
    def preview_news(self, source: NewsSource) -> PreviewNews:
        return PreviewNews(source)

    @provide(scope=Scope.APP)
    def index_news_dataset(
        self,
        source: NewsSource,
        indexer: RetrievalIndexer,
    ) -> IndexNewsDataset:
        return IndexNewsDataset(source, indexer)


def create_container(
    settings: NewsServiceSettings | None = None,
    *,
    use_fake_components: bool = False,
) -> Any:
    return make_async_container(
        NewsServiceProvider(settings, use_fake_components=use_fake_components),
        FastapiProvider(),
    )
