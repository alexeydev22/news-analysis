from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from api_gateway.application.errors import RetrievalServiceUnavailableError
from api_gateway.application.ports import RetrievalClient
from api_gateway.application.use_cases import IndexNewsUseCase, SearchNewsUseCase
from api_gateway.presentation.router import router
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider, setup_dishka
from economic_news_contracts.retrieval import (
    IndexNewsRequest,
    IndexNewsResponse,
    SearchNewsRequest,
    SearchNewsResponse,
    SearchNewsResult,
)
from economic_news_framework.apps import create_service_app
from fastapi.testclient import TestClient


class SuccessfulClient:
    async def index(self, request: IndexNewsRequest) -> IndexNewsResponse:
        return IndexNewsResponse(
            indexed_count=len(request.documents),
            collection_name="economic_news",
        )

    async def search(self, request: SearchNewsRequest) -> SearchNewsResponse:
        return SearchNewsResponse(
            results=[
                SearchNewsResult(
                    id="news-1",
                    score=0.75,
                    title=f"{request.query} grows",
                    text="GDP grew by 2 percent.",
                    source=request.source or "demo",
                    metadata={"limit": request.limit},
                ),
            ],
        )


class UnavailableClient:
    async def index(self, request: IndexNewsRequest) -> IndexNewsResponse:
        raise RetrievalServiceUnavailableError("retrieval-service is unavailable")

    async def search(self, request: SearchNewsRequest) -> SearchNewsResponse:
        raise RetrievalServiceUnavailableError("retrieval-service is unavailable")


class SensitiveUnavailableClient:
    async def index(self, request: IndexNewsRequest) -> IndexNewsResponse:
        raise RetrievalServiceUnavailableError("connection refused at 10.0.0.12")

    async def search(self, request: SearchNewsRequest) -> SearchNewsResponse:
        raise RetrievalServiceUnavailableError("connection refused at 10.0.0.12")


class RetrievalProvider(Provider):
    def __init__(self, retrieval_client: RetrievalClient) -> None:
        super().__init__()
        self._retrieval_client = retrieval_client

    @provide(scope=Scope.APP)
    def index_news_use_case(self) -> IndexNewsUseCase:
        return IndexNewsUseCase(self._retrieval_client)

    @provide(scope=Scope.APP)
    def search_news_use_case(self) -> SearchNewsUseCase:
        return SearchNewsUseCase(self._retrieval_client)


def make_client(retrieval_client: RetrievalClient) -> TestClient:
    app = create_service_app(
        service_name="api-gateway",
        routers=(router,),
        log_level="INFO",
    )
    container = make_async_container(RetrievalProvider(retrieval_client), FastapiProvider())
    setup_dishka(container=container, app=app)

    @asynccontextmanager
    async def close_container(_: object) -> AsyncIterator[None]:
        yield
        await container.close()

    app.router.lifespan_context = close_container
    return TestClient(app)


def test_index_endpoint_returns_retrieval_response() -> None:
    with make_client(SuccessfulClient()) as client:
        response = client.post(
            "/api/v1/retrieval/index",
            json={
                "documents": [
                    {
                        "id": "news-1",
                        "title": "GDP grows",
                        "text": "GDP grew by 2 percent.",
                        "source": "demo",
                    },
                ],
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "indexed_count": 1,
        "collection_name": "economic_news",
    }


def test_search_endpoint_returns_retrieval_response() -> None:
    with make_client(SuccessfulClient()) as client:
        response = client.post(
            "/api/v1/retrieval/search",
            json={"query": "GDP", "limit": 3, "source": "demo"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {
                "id": "news-1",
                "score": 0.75,
                "title": "GDP grows",
                "text": "GDP grew by 2 percent.",
                "source": "demo",
                "published_at": None,
                "metadata": {"limit": 3},
            },
        ],
    }


def test_index_endpoint_maps_unavailable_error_to_503() -> None:
    with make_client(UnavailableClient()) as client:
        response = client.post(
            "/api/v1/retrieval/index",
            json={
                "documents": [
                    {
                        "id": "news-1",
                        "title": "GDP grows",
                        "text": "GDP grew by 2 percent.",
                        "source": "demo",
                    },
                ],
            },
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "retrieval-service is unavailable"}


def test_search_endpoint_maps_unavailable_error_to_503() -> None:
    with make_client(UnavailableClient()) as client:
        response = client.post("/api/v1/retrieval/search", json={"query": "GDP"})

    assert response.status_code == 503
    assert response.json() == {"detail": "retrieval-service is unavailable"}


def test_retrieval_endpoint_does_not_expose_internal_error_detail() -> None:
    with make_client(SensitiveUnavailableClient()) as client:
        response = client.post("/api/v1/retrieval/search", json={"query": "GDP"})

    assert response.status_code == 503
    assert response.json() == {"detail": "retrieval-service is unavailable"}
