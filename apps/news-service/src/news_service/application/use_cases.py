from economic_news_contracts.news import (
    EnqueueIndexNewsDatasetResponse,
    IndexNewsDatasetResponse,
)

from news_service.application.ports import (
    DatasetStorage,
    NewsIndexTaskQueue,
    NewsSource,
    RetrievalIndexer,
)
from news_service.domain.dataset import ActiveDataset, UploadedDataset
from news_service.domain.model import NewsDocument


class PreviewNews:
    def __init__(self, source: NewsSource) -> None:
        self._source = source

    async def execute(self, limit: int) -> tuple[list[NewsDocument], int]:
        documents = await self._source.load()
        return documents[:limit], len(documents)


class IndexNewsDataset:
    def __init__(self, source: NewsSource, indexer: RetrievalIndexer) -> None:
        self._source = source
        self._indexer = indexer

    async def execute(self, limit: int) -> IndexNewsDatasetResponse:
        documents = await self._source.load(limit=limit)
        index_response = await self._indexer.index(documents)
        return IndexNewsDatasetResponse(
            loaded_count=len(documents),
            indexed_count=index_response.indexed_count,
            collection_name=index_response.collection_name,
        )


class EnqueueIndexNewsDataset:
    def __init__(self, task_queue: NewsIndexTaskQueue, events_channel: str) -> None:
        self._task_queue = task_queue
        self._events_channel = events_channel

    async def execute(self, limit: int) -> EnqueueIndexNewsDatasetResponse:
        job_id = await self._task_queue.enqueue(limit=limit)
        return EnqueueIndexNewsDatasetResponse(
            job_id=job_id,
            events_channel=self._events_channel,
        )


class UploadNewsDataset:
    def __init__(self, storage: DatasetStorage) -> None:
        self._storage = storage

    async def execute(self, *, filename: str, content: bytes) -> UploadedDataset:
        return await self._storage.save_upload(filename=filename, content=content)


class ListNewsDatasets:
    def __init__(self, storage: DatasetStorage) -> None:
        self._storage = storage

    async def execute(self) -> list[UploadedDataset]:
        return await self._storage.list_datasets()


class ActivateNewsDataset:
    def __init__(self, storage: DatasetStorage) -> None:
        self._storage = storage

    async def execute(self, dataset_id: str) -> ActiveDataset:
        return await self._storage.activate(dataset_id)


class GetActiveNewsDataset:
    def __init__(self, storage: DatasetStorage) -> None:
        self._storage = storage

    async def execute(self) -> ActiveDataset | None:
        return await self._storage.get_active()
