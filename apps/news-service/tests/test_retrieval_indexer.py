import pytest
from news_service.domain.errors import RetrievalIndexUnavailableError
from news_service.domain.model import NewsDocument
from news_service.infrastructure.retrieval_client import ZaprosRetrievalIndexer


class FakeResponse:
    def __init__(self, status: int, json: object) -> None:
        self.status = status
        self.json = json


class FakeZaprosClient:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def post(self, url: str, json: dict[str, object]) -> FakeResponse:
        self.calls.append((url, json))
        return self.response


class RaisingZaprosClient:
    async def post(self, url: str, json: dict[str, object]) -> FakeResponse:
        raise OSError("connection refused")


@pytest.mark.asyncio
async def test_zapros_retrieval_indexer_sends_index_payload() -> None:
    transport = FakeZaprosClient(
        FakeResponse(200, {"indexed_count": 1, "collection_name": "economic_news"}),
    )
    indexer = ZaprosRetrievalIndexer(
        base_url="http://retrieval-service:8000/",
        timeout_seconds=5.0,
        client=transport,
    )

    response = await indexer.index(
        [
            NewsDocument(
                id="news-1",
                title="GDP grows",
                text="GDP grew by 2 percent.",
                source="demo",
                metadata={"impact": "positive"},
            ),
        ],
    )

    assert response.indexed_count == 1
    assert response.collection_name == "economic_news"
    assert transport.calls == [
        (
            "http://retrieval-service:8000/api/v1/index",
            {
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
            },
        ),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        FakeResponse(503, {"detail": "down"}),
        FakeResponse(200, {"indexed_count": -1, "collection_name": "economic_news"}),
    ],
)
async def test_zapros_retrieval_indexer_maps_bad_responses(
    response: FakeResponse,
) -> None:
    indexer = ZaprosRetrievalIndexer(
        base_url="http://retrieval-service:8000",
        timeout_seconds=5.0,
        client=FakeZaprosClient(response),
    )

    with pytest.raises(
        RetrievalIndexUnavailableError,
        match="retrieval-service is unavailable",
    ):
        await indexer.index(
            [NewsDocument(id="news-1", title="GDP", text="Text", source="demo")],
        )


@pytest.mark.asyncio
async def test_zapros_retrieval_indexer_maps_transport_error() -> None:
    indexer = ZaprosRetrievalIndexer(
        base_url="http://retrieval-service:8000",
        timeout_seconds=5.0,
        client=RaisingZaprosClient(),
    )

    with pytest.raises(
        RetrievalIndexUnavailableError,
        match="retrieval-service is unavailable",
    ):
        await indexer.index(
            [NewsDocument(id="news-1", title="GDP", text="Text", source="demo")],
        )
