import pytest
from api_gateway.application.errors import RetrievalServiceUnavailableError
from api_gateway.infrastructure.retrieval_client import ZaprosRetrievalClient
from economic_news_contracts.retrieval import (
    IndexNewsRequest,
    NewsDocumentPayload,
    SearchNewsRequest,
)
from zapros import Response


class FakeZaprosClient:
    def __init__(self, response: Response) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def post(self, url: str, json: dict[str, object]) -> Response:
        self.calls.append((url, json))
        return self.response


class RaisingZaprosClient:
    async def post(self, url: str, json: dict[str, object]) -> Response:
        raise OSError("connection refused")


def index_request() -> IndexNewsRequest:
    return IndexNewsRequest(
        documents=[
            NewsDocumentPayload(
                id="news-1",
                title="GDP grows",
                text="GDP grew by 2 percent.",
                source="demo",
            ),
        ],
    )


@pytest.mark.asyncio
async def test_retrieval_client_indexes_documents() -> None:
    transport = FakeZaprosClient(
        Response(200, json={"indexed_count": 1, "collection_name": "economic_news"}),
    )
    client = ZaprosRetrievalClient(
        base_url="http://retrieval-service:8000/",
        timeout_seconds=3.0,
        client=transport,
    )

    response = await client.index(index_request())

    assert response.indexed_count == 1
    assert transport.calls[0] == (
        "http://retrieval-service:8000/api/v1/index",
        {
            "documents": [
                {
                    "id": "news-1",
                    "title": "GDP grows",
                    "text": "GDP grew by 2 percent.",
                    "source": "demo",
                    "published_at": None,
                    "metadata": {},
                },
            ],
        },
    )


@pytest.mark.asyncio
async def test_retrieval_client_search_accepts_negative_score() -> None:
    transport = FakeZaprosClient(
        Response(
            200,
            json={
                "results": [
                    {
                        "id": "news-1",
                        "score": -0.1,
                        "title": "GDP grows",
                        "text": "GDP grew by 2 percent.",
                        "source": "demo",
                        "published_at": None,
                        "metadata": {},
                    },
                ],
            },
        ),
    )
    client = ZaprosRetrievalClient(
        base_url="http://retrieval-service:8000",
        timeout_seconds=3.0,
        client=transport,
    )

    response = await client.search(SearchNewsRequest(query="GDP", limit=3))

    assert response.results[0].score == -0.1
    assert transport.calls[0] == (
        "http://retrieval-service:8000/api/v1/search",
        {"query": "GDP", "limit": 3, "source": None},
    )


@pytest.mark.asyncio
async def test_retrieval_client_maps_5xx_to_unavailable_error() -> None:
    client = ZaprosRetrievalClient(
        base_url="http://retrieval-service:8000",
        timeout_seconds=3.0,
        client=FakeZaprosClient(Response(503, json={"detail": "down"})),
    )

    with pytest.raises(
        RetrievalServiceUnavailableError,
        match="retrieval-service is unavailable",
    ):
        await client.search(SearchNewsRequest(query="GDP"))


@pytest.mark.asyncio
async def test_retrieval_client_maps_transport_error() -> None:
    client = ZaprosRetrievalClient(
        base_url="http://retrieval-service:8000",
        timeout_seconds=3.0,
        client=RaisingZaprosClient(),
    )

    with pytest.raises(
        RetrievalServiceUnavailableError,
        match="retrieval-service is unavailable",
    ):
        await client.index(index_request())
