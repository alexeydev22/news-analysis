from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import pytest
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider, setup_dishka
from economic_news_contracts.news import EnqueueIndexNewsDatasetResponse, IndexNewsDatasetResponse
from economic_news_framework.apps import create_service_app
from fastapi.testclient import TestClient
from news_service.application.use_cases import (
    ActivateNewsDataset,
    EnqueueIndexNewsDataset,
    GetActiveNewsDataset,
    IndexNewsDataset,
    ListNewsDatasets,
    PreviewNews,
    UploadNewsDataset,
)
from news_service.domain.dataset import ActiveDataset, UploadedDataset
from news_service.domain.errors import NewsSourceUnavailableError, NewsSourceValidationError
from news_service.domain.model import NewsDocument
from news_service.main.settings import NewsServiceSettings
from news_service.presentation.errors import register_error_handlers
from news_service.presentation.router import router


class StubPreviewNews(PreviewNews):
    def __init__(self, error: Exception | None = None) -> None:
        self.limit: int | None = None
        self._error = error

    async def execute(self, limit: int) -> tuple[list[NewsDocument], int]:
        self.limit = limit
        if self._error is not None:
            raise self._error
        return (
            [
                NewsDocument(
                    id="news-1",
                    title="GDP grows",
                    text="GDP grew by 2 percent.",
                    source="demo",
                    metadata={"impact": "positive"},
                ),
            ],
            3,
        )


class StubIndexNewsDataset(IndexNewsDataset):
    def __init__(self, error: Exception | None = None) -> None:
        self.limit: int | None = None
        self._error = error

    async def execute(self, limit: int) -> IndexNewsDatasetResponse:
        self.limit = limit
        if self._error is not None:
            raise self._error
        return IndexNewsDatasetResponse(
            loaded_count=1,
            indexed_count=1,
            collection_name="economic_news",
        )


class StubEnqueueIndexNewsDataset(EnqueueIndexNewsDataset):
    def __init__(self) -> None:
        self.limit: int | None = None

    async def execute(self, limit: int) -> EnqueueIndexNewsDatasetResponse:
        self.limit = limit
        return EnqueueIndexNewsDatasetResponse(
            job_id="job-1",
            events_channel="news.index.events",
        )


class StubUploadNewsDataset(UploadNewsDataset):
    def __init__(self) -> None:
        self.filename: str | None = None
        self.content: bytes | None = None

    async def execute(self, *, filename: str, content: bytes) -> UploadedDataset:
        self.filename = filename
        self.content = content
        return UploadedDataset(
            dataset_id="news",
            filename=filename,
            path=Path("data/uploads/news.csv"),
            size_bytes=len(content),
            uploaded_at=datetime(2026, 5, 8, tzinfo=UTC),
        )


class StubListNewsDatasets(ListNewsDatasets):
    def __init__(self) -> None:
        pass

    async def execute(self) -> list[UploadedDataset]:
        return [
            UploadedDataset(
                dataset_id="news",
                filename="news.csv",
                path=Path("data/uploads/news.csv"),
                size_bytes=42,
                uploaded_at=datetime(2026, 5, 8, tzinfo=UTC),
            ),
        ]


class StubActivateNewsDataset(ActivateNewsDataset):
    def __init__(self) -> None:
        self.dataset_id: str | None = None

    async def execute(self, dataset_id: str) -> ActiveDataset:
        self.dataset_id = dataset_id
        return ActiveDataset(
            dataset_id=dataset_id,
            filename="news.csv",
            path=Path("data/uploads/news.csv"),
            activated_at=datetime(2026, 5, 8, tzinfo=UTC),
        )


class StubGetActiveNewsDataset(GetActiveNewsDataset):
    def __init__(self) -> None:
        pass

    async def execute(self) -> ActiveDataset | None:
        return ActiveDataset(
            dataset_id="news",
            filename="news.csv",
            path=Path("data/uploads/news.csv"),
            activated_at=datetime(2026, 5, 8, tzinfo=UTC),
        )


class NewsProvider(Provider):
    def __init__(
        self,
        preview: PreviewNews,
        index: IndexNewsDataset,
        enqueue: EnqueueIndexNewsDataset,
        upload: UploadNewsDataset,
        list_datasets: ListNewsDatasets,
        activate: ActivateNewsDataset,
        get_active: GetActiveNewsDataset,
        settings: NewsServiceSettings,
    ) -> None:
        super().__init__()
        self._preview = preview
        self._index = index
        self._enqueue = enqueue
        self._upload = upload
        self._list_datasets = list_datasets
        self._activate = activate
        self._get_active = get_active
        self._settings = settings

    @provide(scope=Scope.APP)
    def preview_news(self) -> PreviewNews:
        return self._preview

    @provide(scope=Scope.APP)
    def index_news_dataset(self) -> IndexNewsDataset:
        return self._index

    @provide(scope=Scope.APP)
    def enqueue_index_news_dataset(self) -> EnqueueIndexNewsDataset:
        return self._enqueue

    @provide(scope=Scope.APP)
    def upload_news_dataset(self) -> UploadNewsDataset:
        return self._upload

    @provide(scope=Scope.APP)
    def list_news_datasets(self) -> ListNewsDatasets:
        return self._list_datasets

    @provide(scope=Scope.APP)
    def activate_news_dataset(self) -> ActivateNewsDataset:
        return self._activate

    @provide(scope=Scope.APP)
    def get_active_news_dataset(self) -> GetActiveNewsDataset:
        return self._get_active

    @provide(scope=Scope.APP)
    def settings(self) -> NewsServiceSettings:
        return self._settings


def make_client(
    preview: PreviewNews,
    index: IndexNewsDataset,
    enqueue: EnqueueIndexNewsDataset | None = None,
    upload: UploadNewsDataset | None = None,
    list_datasets: ListNewsDatasets | None = None,
    activate: ActivateNewsDataset | None = None,
    get_active: GetActiveNewsDataset | None = None,
    settings: NewsServiceSettings | None = None,
) -> TestClient:
    app = create_service_app(service_name="news-service", routers=(router,), log_level="INFO")
    register_error_handlers(app)
    container = make_async_container(
        NewsProvider(
            preview,
            index,
            enqueue or StubEnqueueIndexNewsDataset(),
            upload or StubUploadNewsDataset(),
            list_datasets or StubListNewsDatasets(),
            activate or StubActivateNewsDataset(),
            get_active or StubGetActiveNewsDataset(),
            settings or NewsServiceSettings(),
        ),
        FastapiProvider(),
    )
    setup_dishka(container=container, app=app)

    @asynccontextmanager
    async def close_container(_: object) -> AsyncIterator[None]:
        yield
        await container.close()

    app.router.lifespan_context = close_container
    return TestClient(app)


def test_preview_endpoint_returns_documents() -> None:
    preview = StubPreviewNews()

    with make_client(preview, StubIndexNewsDataset()) as client:
        response = client.get("/api/v1/news/preview?limit=1")

    assert response.status_code == 200
    assert preview.limit == 1
    assert response.json() == {
        "documents": [
            {
                "id": "news-1",
                "title": "GDP grows",
                "text": "GDP grew by 2 percent.",
                "source": "demo",
                "published_at": None,
                "metadata": {"impact": "positive"},
            },
        ],
        "total_count": 3,
    }


def test_index_endpoint_indexes_dataset() -> None:
    index = StubIndexNewsDataset()

    with make_client(StubPreviewNews(), index) as client:
        response = client.post("/api/v1/news/index", json={"limit": 5})

    assert response.status_code == 200
    assert index.limit == 5
    assert response.json() == {
        "loaded_count": 1,
        "indexed_count": 1,
        "collection_name": "economic_news",
    }


def test_index_endpoint_uses_configured_default_limit_when_omitted() -> None:
    index = StubIndexNewsDataset()

    with make_client(
        StubPreviewNews(),
        index,
        settings=NewsServiceSettings(default_index_limit=25),
    ) as client:
        response = client.post("/api/v1/news/index", json={})

    assert response.status_code == 200
    assert index.limit == 25


def test_enqueue_index_endpoint_schedules_dataset_indexing() -> None:
    enqueue = StubEnqueueIndexNewsDataset()

    with make_client(StubPreviewNews(), StubIndexNewsDataset(), enqueue) as client:
        response = client.post("/api/v1/news/index/jobs", json={"limit": 7})

    assert response.status_code == 202
    assert enqueue.limit == 7
    assert response.json() == {
        "job_id": "job-1",
        "status": "queued",
        "events_channel": "news.index.events",
    }


def test_upload_dataset_endpoint_accepts_csv() -> None:
    upload = StubUploadNewsDataset()

    with make_client(StubPreviewNews(), StubIndexNewsDataset(), upload=upload) as client:
        response = client.post(
            "/api/v1/news/datasets/upload",
            files={"file": ("news.csv", b"title,text,source\nA,B,C\n", "text/csv")},
        )

    assert response.status_code == 201
    assert upload.filename == "news.csv"
    assert upload.content == b"title,text,source\nA,B,C\n"
    assert response.json() == {
        "dataset_id": "news",
        "filename": "news.csv",
        "size_bytes": 24,
        "uploaded_at": "2026-05-08T00:00:00Z",
    }


def test_list_datasets_endpoint_returns_uploads() -> None:
    with make_client(StubPreviewNews(), StubIndexNewsDataset()) as client:
        response = client.get("/api/v1/news/datasets")

    assert response.status_code == 200
    assert response.json() == {
        "datasets": [
            {
                "dataset_id": "news",
                "filename": "news.csv",
                "size_bytes": 42,
                "uploaded_at": "2026-05-08T00:00:00Z",
            },
        ],
    }


def test_activate_dataset_endpoint_returns_active_dataset() -> None:
    activate = StubActivateNewsDataset()

    with make_client(StubPreviewNews(), StubIndexNewsDataset(), activate=activate) as client:
        response = client.post("/api/v1/news/datasets/news/activate")

    assert response.status_code == 200
    assert activate.dataset_id == "news"
    assert response.json() == {
        "dataset_id": "news",
        "filename": "news.csv",
        "activated_at": "2026-05-08T00:00:00Z",
    }


def test_get_active_dataset_endpoint_returns_active_dataset() -> None:
    with make_client(StubPreviewNews(), StubIndexNewsDataset()) as client:
        response = client.get("/api/v1/news/datasets/active")

    assert response.status_code == 200
    assert response.json() == {
        "dataset_id": "news",
        "filename": "news.csv",
        "activated_at": "2026-05-08T00:00:00Z",
    }


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (
            NewsSourceValidationError("Missing required CSV column: text"),
            422,
            "Invalid news source data",
        ),
        (
            NewsSourceUnavailableError("secret path /tmp/news.csv"),
            503,
            "news source is unavailable",
        ),
    ],
)
def test_news_endpoint_maps_source_errors(
    error: Exception,
    status_code: int,
    detail: str,
) -> None:
    with make_client(StubPreviewNews(error), StubIndexNewsDataset()) as client:
        response = client.get("/api/v1/news/preview")

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
