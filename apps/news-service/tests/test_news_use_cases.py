from pathlib import Path

import pytest
from economic_news_contracts.retrieval import IndexNewsResponse
from news_service.application.use_cases import (
    ActivateNewsDataset,
    EnqueueIndexNewsDataset,
    GetActiveNewsDataset,
    IndexNewsDataset,
    ListNewsDatasets,
    PreviewNews,
    UploadNewsDataset,
)
from news_service.domain.dataset import ActiveDataset, UploadedDataset, utc_now
from news_service.domain.model import NewsDocument


class FakeNewsSource:
    def __init__(self) -> None:
        self.limit: int | None = None

    async def load(self, limit: int | None = None) -> list[NewsDocument]:
        self.limit = limit
        documents = [
            NewsDocument(
                id="news-1",
                title="GDP grows",
                text="GDP grew by 2 percent.",
                source="demo",
            ),
            NewsDocument(
                id="news-2",
                title="Inflation slows",
                text="Inflation slowed in April.",
                source="demo",
            ),
        ]
        if limit is not None:
            return documents[:limit]
        return documents


class FakeRetrievalIndexer:
    def __init__(self) -> None:
        self.batches: list[list[NewsDocument]] = []

    async def index(self, documents: list[NewsDocument]) -> IndexNewsResponse:
        self.batches.append(documents)
        return IndexNewsResponse(
            indexed_count=len(documents),
            collection_name="economic_news",
        )


class FakeTaskQueue:
    def __init__(self) -> None:
        self.limit: int | None = None

    async def enqueue(self, limit: int) -> str:
        self.limit = limit
        return "job-1"


class FakeDatasetStorage:
    def __init__(self) -> None:
        uploaded = UploadedDataset(
            dataset_id="news",
            filename="news.csv",
            path=Path("data/uploads/news.csv"),
            size_bytes=42,
            uploaded_at=utc_now(),
        )
        self.saved_filename: str | None = None
        self.saved_content: bytes | None = None
        self.activated_dataset_id: str | None = None
        self.uploaded = uploaded
        self.active = ActiveDataset(
            dataset_id=uploaded.dataset_id,
            filename=uploaded.filename,
            path=uploaded.path,
            activated_at=utc_now(),
        )

    async def save_upload(self, *, filename: str, content: bytes) -> UploadedDataset:
        self.saved_filename = filename
        self.saved_content = content
        return self.uploaded

    async def list_datasets(self) -> list[UploadedDataset]:
        return [self.uploaded]

    async def activate(self, dataset_id: str) -> ActiveDataset:
        self.activated_dataset_id = dataset_id
        return self.active

    async def get_active(self) -> ActiveDataset | None:
        return self.active

    async def get_active_path(self) -> Path | None:
        return self.active.path


@pytest.mark.asyncio
async def test_preview_news_loads_documents_and_reports_total_count() -> None:
    source = FakeNewsSource()
    use_case = PreviewNews(source)

    documents, total_count = await use_case.execute(limit=1)

    assert source.limit is None
    assert [document.id for document in documents] == ["news-1"]
    assert total_count == 2


@pytest.mark.asyncio
async def test_index_news_dataset_loads_limited_documents_and_indexes_them() -> None:
    source = FakeNewsSource()
    indexer = FakeRetrievalIndexer()
    use_case = IndexNewsDataset(source, indexer)

    result = await use_case.execute(limit=1)

    assert source.limit == 1
    assert [[document.id for document in batch] for batch in indexer.batches] == [["news-1"]]
    assert result.loaded_count == 1
    assert result.indexed_count == 1
    assert result.collection_name == "economic_news"


@pytest.mark.asyncio
async def test_index_news_dataset_indexes_large_dataset_in_batches() -> None:
    documents = [
        NewsDocument(
            id=f"news-{number}",
            title=f"Title {number}",
            text=f"Text {number}",
            source="demo",
        )
        for number in range(1, 6)
    ]

    class ManyNewsSource(FakeNewsSource):
        async def load(self, limit: int | None = None) -> list[NewsDocument]:
            self.limit = limit
            return documents[:limit]

    source = ManyNewsSource()
    indexer = FakeRetrievalIndexer()
    use_case = IndexNewsDataset(source, indexer, batch_size=2)

    result = await use_case.execute(limit=5)

    assert source.limit == 5
    assert [[document.id for document in batch] for batch in indexer.batches] == [
        ["news-1", "news-2"],
        ["news-3", "news-4"],
        ["news-5"],
    ]
    assert result.loaded_count == 5
    assert result.indexed_count == 5
    assert result.collection_name == "economic_news"


@pytest.mark.asyncio
async def test_enqueue_index_news_dataset_schedules_background_job() -> None:
    queue = FakeTaskQueue()
    use_case = EnqueueIndexNewsDataset(queue, events_channel="news.index.events")

    result = await use_case.execute(limit=25)

    assert queue.limit == 25
    assert result.job_id == "job-1"
    assert result.status == "queued"
    assert result.events_channel == "news.index.events"


@pytest.mark.asyncio
async def test_upload_news_dataset_saves_upload() -> None:
    storage = FakeDatasetStorage()
    use_case = UploadNewsDataset(storage)

    result = await use_case.execute(filename="news.csv", content=b"csv")

    assert storage.saved_filename == "news.csv"
    assert storage.saved_content == b"csv"
    assert result == storage.uploaded


@pytest.mark.asyncio
async def test_list_news_datasets_returns_uploads() -> None:
    storage = FakeDatasetStorage()
    use_case = ListNewsDatasets(storage)

    result = await use_case.execute()

    assert result == [storage.uploaded]


@pytest.mark.asyncio
async def test_activate_news_dataset_activates_upload() -> None:
    storage = FakeDatasetStorage()
    use_case = ActivateNewsDataset(storage)

    result = await use_case.execute("news")

    assert storage.activated_dataset_id == "news"
    assert result == storage.active


@pytest.mark.asyncio
async def test_get_active_news_dataset_returns_active_upload() -> None:
    storage = FakeDatasetStorage()
    use_case = GetActiveNewsDataset(storage)

    result = await use_case.execute()

    assert result == storage.active
