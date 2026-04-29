from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import pytest
from retrieval_service.domain.errors import RetrievalUnavailableError
from retrieval_service.domain.model import NewsDocument, SearchQuery
from retrieval_service.infrastructure import embeddings
from retrieval_service.infrastructure.embeddings import FastEmbedEmbeddingProvider
from retrieval_service.infrastructure.qdrant_repository import QdrantNewsRepository, _point_id


class FakeEmbeddingModel:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.texts = texts
        return [[0.1, 0.2] for _ in texts]


class FailingEmbeddingModel:
    def embed(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("model unavailable")


class FakeQdrantClient:
    def __init__(self) -> None:
        self.collection_exists_value = False
        self.created_collection: str | None = None
        self.vectors_config: object | None = None
        self.points: list[Any] = []
        self.query_filter: object | None = None

    async def collection_exists(self, collection_name: str) -> bool:
        return self.collection_exists_value

    async def create_collection(self, collection_name: str, vectors_config: object) -> None:
        self.collection_exists_value = True
        self.created_collection = collection_name
        self.vectors_config = vectors_config

    async def upsert(self, collection_name: str, points: list[object]) -> None:
        self.points = points

    async def query_points(
        self,
        collection_name: str,
        query: list[float],
        limit: int,
        query_filter: object | None = None,
    ) -> object:
        self.query_filter = query_filter
        point = type(
            "ScoredPoint",
            (),
            {
                "id": str(uuid5(NAMESPACE_URL, "news-1")),
                "score": 0.87,
                "payload": {
                    "document_id": "news-1",
                    "title": "GDP grows",
                    "text": "GDP grew by 2 percent.",
                    "source": "demo",
                    "published_at": "2026-04-29T10:30:00",
                    "metadata": {"sector": "macro"},
                },
            },
        )()
        return type("QueryResponse", (), {"points": [point]})()


class FailingQdrantClient(FakeQdrantClient):
    def __init__(self, failure_method: str) -> None:
        super().__init__()
        self.failure_method = failure_method

    async def collection_exists(self, collection_name: str) -> bool:
        if self.failure_method == "collection_exists":
            raise RuntimeError("qdrant unavailable")
        return await super().collection_exists(collection_name)

    async def upsert(self, collection_name: str, points: list[object]) -> None:
        if self.failure_method == "upsert":
            raise RuntimeError("qdrant unavailable")
        await super().upsert(collection_name, points)

    async def query_points(
        self,
        collection_name: str,
        query: list[float],
        limit: int,
        query_filter: object | None = None,
    ) -> object:
        if self.failure_method == "query_points":
            raise RuntimeError("qdrant unavailable")
        return await super().query_points(collection_name, query, limit, query_filter)


@pytest.mark.asyncio
async def test_fastembed_provider_returns_vectors_from_model() -> None:
    model = FakeEmbeddingModel()
    provider = FastEmbedEmbeddingProvider(model_name="unused", model=model)

    vectors = await provider.embed(["hello"])

    assert model.texts == ["hello"]
    assert vectors == [[0.1, 0.2]]


@pytest.mark.asyncio
async def test_fastembed_provider_runs_sync_model_in_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = FakeEmbeddingModel()
    provider = FastEmbedEmbeddingProvider(model_name="unused", model=model)
    calls: list[object] = []

    async def fake_to_thread(func: Callable[[], list[list[float]]]) -> list[list[float]]:
        calls.append(func)
        return func()

    monkeypatch.setattr(embeddings.asyncio, "to_thread", fake_to_thread)

    vectors = await provider.embed(["hello"])

    assert len(calls) == 1
    assert model.texts == ["hello"]
    assert vectors == [[0.1, 0.2]]


@pytest.mark.asyncio
async def test_fastembed_provider_maps_model_errors() -> None:
    provider = FastEmbedEmbeddingProvider(model_name="unused", model=FailingEmbeddingModel())

    with pytest.raises(RetrievalUnavailableError):
        await provider.embed(["hello"])


@pytest.mark.asyncio
async def test_qdrant_repository_upserts_documents_and_creates_collection_lazily() -> None:
    client = FakeQdrantClient()
    repository = QdrantNewsRepository(
        client=client,
        collection_name="economic_news",
        vector_size=2,
    )
    published_at = datetime(2026, 4, 29, 10, 30)
    document = NewsDocument(
        id="news-1",
        title="GDP grows",
        text="GDP grew by 2 percent.",
        source="demo",
        published_at=published_at,
        metadata={"sector": "macro"},
    )

    indexed_count = await repository.upsert([document], [[0.1, 0.2]])

    assert indexed_count == 1
    assert client.created_collection == "economic_news"
    assert len(client.points) == 1
    point = client.points[0]
    expected_point_id = uuid5(NAMESPACE_URL, "news-1")
    assert UUID(str(point.id)) == expected_point_id
    assert point.vector == [0.1, 0.2]
    assert point.payload == {
        "document_id": "news-1",
        "title": "GDP grows",
        "text": "GDP grew by 2 percent.",
        "source": "demo",
        "published_at": "2026-04-29T10:30:00",
        "metadata": {"sector": "macro"},
    }


@pytest.mark.asyncio
async def test_qdrant_repository_search_returns_domain_results_and_source_filter() -> None:
    client = FakeQdrantClient()
    repository = QdrantNewsRepository(
        client=client,
        collection_name="economic_news",
        vector_size=2,
    )

    results = await repository.search(SearchQuery(query="GDP", source="demo"), [0.1, 0.2])

    assert len(results) == 1
    assert results[0].document.id == "news-1"
    assert results[0].document.metadata == {"sector": "macro"}
    assert results[0].document.published_at == datetime(2026, 4, 29, 10, 30)
    assert results[0].score == 0.87
    assert client.query_filter is not None


def test_qdrant_point_id_is_deterministic_uuid_from_document_id() -> None:
    point_id = _point_id("arbitrary-news-id")

    assert UUID(point_id) == uuid5(NAMESPACE_URL, "arbitrary-news-id")
    assert point_id != "arbitrary-news-id"


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_method", ["collection_exists", "upsert", "query_points"])
async def test_qdrant_repository_maps_client_errors(failure_method: str) -> None:
    client = FailingQdrantClient(failure_method=failure_method)
    repository = QdrantNewsRepository(
        client=client,
        collection_name="economic_news",
        vector_size=2,
    )

    with pytest.raises(RetrievalUnavailableError):
        if failure_method == "query_points":
            await repository.search(SearchQuery(query="GDP"), [0.1, 0.2])
        else:
            document = NewsDocument(id="news-1", title="GDP grows", text="Body", source="demo")
            await repository.upsert([document], [[0.1, 0.2]])
