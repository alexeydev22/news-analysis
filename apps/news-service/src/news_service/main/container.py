from pathlib import Path
from typing import Any

from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider
from economic_news_contracts.retrieval import IndexNewsResponse

from news_service.application.ports import (
    DatasetStorage,
    NewsIndexTaskQueue,
    NewsSource,
    RetrievalIndexer,
)
from news_service.application.use_cases import (
    ActivateNewsDataset,
    EnqueueIndexNewsDataset,
    GetActiveNewsDataset,
    IndexNewsDataset,
    ListNewsDatasets,
    PreviewNews,
    UploadNewsDataset,
)
from news_service.domain.model import NewsDocument
from news_service.infrastructure.csv_news_source import CsvNewsSource
from news_service.infrastructure.local_dataset_storage import LocalDatasetStorage
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


class FakeNewsIndexTaskQueue:
    async def enqueue(self, limit: int) -> str:
        return f"fake-news-index-{limit}"


class ActiveDatasetCsvNewsSource:
    def __init__(self, storage: DatasetStorage, fallback_path: Path) -> None:
        self._storage = storage
        self._fallback_path = fallback_path

    async def load(self, limit: int | None = None) -> list[NewsDocument]:
        active_path = await self._storage.get_active_path()
        return await CsvNewsSource(active_path or self._fallback_path).load(limit=limit)


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

    @provide(scope=Scope.APP, provides=DatasetStorage)
    def dataset_storage(self, settings: NewsServiceSettings) -> DatasetStorage:
        return LocalDatasetStorage(
            upload_dir=settings.dataset_upload_dir,
            active_dataset_file=settings.active_dataset_file,
            max_upload_bytes=settings.upload_max_bytes,
        )

    @provide(scope=Scope.APP, provides=NewsSource)
    def news_source(self, settings: NewsServiceSettings, storage: DatasetStorage) -> NewsSource:
        if self._use_fake_components:
            return FakeNewsSource()
        return ActiveDatasetCsvNewsSource(storage, Path(settings.news_dataset_path))

    @provide(scope=Scope.APP, provides=RetrievalIndexer)
    def retrieval_indexer(self, settings: NewsServiceSettings) -> RetrievalIndexer:
        if self._use_fake_components:
            return FakeRetrievalIndexer()
        return ZaprosRetrievalIndexer(
            base_url=str(settings.retrieval_service_url),
            timeout_seconds=settings.retrieval_service_timeout_seconds,
        )

    @provide(scope=Scope.APP, provides=NewsIndexTaskQueue)
    def news_index_task_queue(self) -> NewsIndexTaskQueue:
        if self._use_fake_components:
            return FakeNewsIndexTaskQueue()
        from news_service.infrastructure.taskiq_queue import TaskiqNewsIndexTaskQueue

        return TaskiqNewsIndexTaskQueue()

    @provide(scope=Scope.APP)
    def preview_news(self, source: NewsSource) -> PreviewNews:
        return PreviewNews(source)

    @provide(scope=Scope.APP)
    def index_news_dataset(
        self,
        source: NewsSource,
        indexer: RetrievalIndexer,
        settings: NewsServiceSettings,
    ) -> IndexNewsDataset:
        return IndexNewsDataset(source, indexer, batch_size=settings.index_batch_size)

    @provide(scope=Scope.APP)
    def enqueue_index_news_dataset(
        self,
        task_queue: NewsIndexTaskQueue,
        settings: NewsServiceSettings,
    ) -> EnqueueIndexNewsDataset:
        return EnqueueIndexNewsDataset(
            task_queue,
            events_channel=settings.index_events_channel,
        )

    @provide(scope=Scope.APP)
    def upload_news_dataset(self, storage: DatasetStorage) -> UploadNewsDataset:
        return UploadNewsDataset(storage)

    @provide(scope=Scope.APP)
    def list_news_datasets(self, storage: DatasetStorage) -> ListNewsDatasets:
        return ListNewsDatasets(storage)

    @provide(scope=Scope.APP)
    def activate_news_dataset(self, storage: DatasetStorage) -> ActivateNewsDataset:
        return ActivateNewsDataset(storage)

    @provide(scope=Scope.APP)
    def get_active_news_dataset(self, storage: DatasetStorage) -> GetActiveNewsDataset:
        return GetActiveNewsDataset(storage)


def create_container(
    settings: NewsServiceSettings | None = None,
    *,
    use_fake_components: bool = False,
) -> Any:
    return make_async_container(
        NewsServiceProvider(settings, use_fake_components=use_fake_components),
        FastapiProvider(),
    )
