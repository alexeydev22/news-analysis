from fastapi import FastAPI
from fastapi.testclient import TestClient
from retrieval_service.domain.errors import EmptyDocumentTextError, RetrievalUnavailableError
from retrieval_service.domain.model import NewsDocument, SearchQuery, SearchResult
from retrieval_service.main.app import create_app
from retrieval_service.main.container import FakeVectorRepository
from retrieval_service.presentation.errors import register_error_handlers


def test_retrieval_service_health_endpoint() -> None:
    with TestClient(create_app(use_fake_components=True)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"service": "retrieval-service", "status": "ok"}


def test_index_endpoint_returns_indexed_count() -> None:
    with TestClient(create_app(use_fake_components=True)) as client:
        response = client.post(
            "/api/v1/index",
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
    assert response.json() == {"indexed_count": 1, "collection_name": "economic_news"}


def test_search_endpoint_returns_results() -> None:
    with TestClient(create_app(use_fake_components=True)) as client:
        response = client.post("/api/v1/search", json={"query": "GDP", "limit": 3})

    assert response.status_code == 200
    assert response.json()["results"][0]["id"] == "news-1"


def test_search_endpoint_clamps_vector_score_rounding(monkeypatch) -> None:
    async def search_with_rounding_score(
        self: FakeVectorRepository,
        query: SearchQuery,
        vector: list[float],
    ) -> list[SearchResult]:
        return [
            SearchResult(
                document=NewsDocument(
                    id="news-1",
                    title="GDP grows",
                    text="GDP grew by 2 percent.",
                    source=query.source or "demo",
                ),
                score=1.0000001,
            ),
        ]

    monkeypatch.setattr(FakeVectorRepository, "search", search_with_rounding_score)

    with TestClient(create_app(use_fake_components=True)) as client:
        response = client.post("/api/v1/search", json={"query": "GDP", "limit": 3})

    assert response.status_code == 200
    assert response.json()["results"][0]["score"] == 1.0


def test_domain_validation_error_maps_to_422() -> None:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/validation-error")
    async def validation_error() -> None:
        raise EmptyDocumentTextError("query")

    with TestClient(app) as client:
        response = client.get("/validation-error")

    assert response.status_code == 422
    assert response.json() == {"detail": "query must not be empty"}


def test_retrieval_unavailable_error_maps_to_503() -> None:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/retrieval-unavailable")
    async def retrieval_unavailable() -> None:
        raise RetrievalUnavailableError()

    with TestClient(app) as client:
        response = client.get("/retrieval-unavailable")

    assert response.status_code == 503
    assert response.json() == {"detail": "Retrieval infrastructure is unavailable"}
