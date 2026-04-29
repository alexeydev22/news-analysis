from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from api_gateway.application.errors import AnalysisServiceUnavailableError
from api_gateway.application.ports import AnalysisClient
from api_gateway.application.use_cases import AnalyzeNewsUseCase
from api_gateway.presentation.router import router
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider, setup_dishka
from economic_news_contracts.analysis import AnalyzeNewsRequest, AnalyzeNewsResponse, ImpactLabel
from economic_news_framework.apps import create_service_app
from fastapi.testclient import TestClient


class SuccessfulClient:
    async def analyze(self, request: AnalyzeNewsRequest) -> AnalyzeNewsResponse:
        return AnalyzeNewsResponse(
            model_name=request.analysis_model,
            impact=ImpactLabel.NEUTRAL,
            confidence=0.7,
            explanation="Существенного влияния не ожидается.",
            metadata={"source": "test"},
        )


class UnavailableClient:
    async def analyze(self, request: AnalyzeNewsRequest) -> AnalyzeNewsResponse:
        raise AnalysisServiceUnavailableError("analysis-service is unavailable")


class AnalysisProvider(Provider):
    def __init__(self, analysis_client: AnalysisClient) -> None:
        super().__init__()
        self._analysis_client = analysis_client

    @provide(scope=Scope.APP)
    def analyze_news_use_case(self) -> AnalyzeNewsUseCase:
        return AnalyzeNewsUseCase(self._analysis_client)


def make_client(analysis_client: AnalysisClient) -> TestClient:
    app = create_service_app(
        service_name="api-gateway",
        routers=(router,),
        log_level="INFO",
    )
    container = make_async_container(AnalysisProvider(analysis_client), FastapiProvider())
    setup_dishka(container=container, app=app)

    @asynccontextmanager
    async def close_container(_: object) -> AsyncIterator[None]:
        yield
        await container.close()

    app.router.lifespan_context = close_container
    return TestClient(app)


def test_analyze_endpoint_returns_analysis_response() -> None:
    with make_client(SuccessfulClient()) as client:
        response = client.post(
            "/api/v1/analyze",
            json={"text": "Инфляция замедлилась", "analysis_model": "tfidf-logreg"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "model_name": "tfidf-logreg",
        "impact": "neutral",
        "confidence": 0.7,
        "explanation": "Существенного влияния не ожидается.",
        "metadata": {"source": "test"},
    }


def test_analyze_endpoint_maps_unavailable_error_to_503() -> None:
    with make_client(UnavailableClient()) as client:
        response = client.post("/api/v1/analyze", json={"text": "Индекс снизился"})

    assert response.status_code == 503
    assert response.json() == {"detail": "analysis-service is unavailable"}
