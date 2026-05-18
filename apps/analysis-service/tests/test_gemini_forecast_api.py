from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from analysis_service.application.use_cases import GenerateGeminiTopicForecast
from analysis_service.infrastructure.gemini_forecast_client import GeminiForecastGenerationError
from analysis_service.main.settings import AnalysisServiceSettings
from analysis_service.presentation.errors import register_error_handlers
from analysis_service.presentation.router import router
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider, setup_dishka
from economic_news_contracts.analysis import (
    GeminiForecastRequest,
    GeminiForecastResponse,
)
from economic_news_framework.apps import create_service_app
from fastapi.testclient import TestClient


class StubGenerateGeminiTopicForecast(GenerateGeminiTopicForecast):
    def __init__(self) -> None:
        pass

    async def execute(self, request: GeminiForecastRequest) -> GeminiForecastResponse:
        return GeminiForecastResponse(
            provider="gemini",
            model_name="gemini-2.5-flash",
            scope=request.scope,
            target_id=request.news_id or request.topic.topic_id,
            prediction="Сценарный прогноз сформирован.",
            metadata={"source_model": request.model_name},
        )


class UnavailableGenerateGeminiTopicForecast(GenerateGeminiTopicForecast):
    def __init__(self) -> None:
        pass

    async def execute(self, request: GeminiForecastRequest) -> GeminiForecastResponse:
        raise GeminiForecastGenerationError("GEMINI API key is not configured")


class GeminiForecastProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> AnalysisServiceSettings:
        return AnalysisServiceSettings(use_static_classifier=True)

    @provide(scope=Scope.APP)
    def generate_gemini_topic_forecast(self) -> GenerateGeminiTopicForecast:
        return StubGenerateGeminiTopicForecast()


class UnavailableGeminiForecastProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> AnalysisServiceSettings:
        return AnalysisServiceSettings(use_static_classifier=True)

    @provide(scope=Scope.APP)
    def generate_gemini_topic_forecast(self) -> GenerateGeminiTopicForecast:
        return UnavailableGenerateGeminiTopicForecast()


def make_client(provider: Provider | None = None) -> TestClient:
    app = create_service_app(service_name="analysis-service", routers=(router,))
    container = make_async_container(provider or GeminiForecastProvider(), FastapiProvider())
    setup_dishka(container=container, app=app)
    register_error_handlers(app)

    @asynccontextmanager
    async def close_container(_: object) -> AsyncIterator[None]:
        yield
        await container.close()

    app.router.lifespan_context = close_container
    return TestClient(app, raise_server_exceptions=False)


def test_post_gemini_topic_prediction_returns_forecast() -> None:
    payload = {
        "scope": "topic",
        "model_name": "tfidf-logreg",
        "topic": {
            "topic_id": "topic-1",
            "title": "GDP grows",
            "summary": "GDP grows",
            "overall_impact": "positive",
            "confidence": 0.8,
            "positive_count": 1,
            "neutral_count": 0,
            "negative_count": 0,
            "forecast": "Базовый прогноз.",
            "arguments": ["Рост ВВП поддерживает ожидания."],
            "risks": [],
            "news": [
                {
                    "id": "news-1",
                    "title": "GDP grows",
                    "source": "demo",
                    "impact": "positive",
                    "score": None,
                }
            ],
        },
        "news_id": None,
    }

    with make_client() as client:
        response = client.post("/api/v1/topic-forecast/gemini-predictions", json=payload)

    assert response.status_code == 200
    assert response.json()["provider"] == "gemini"
    assert response.json()["model_name"] == "gemini-2.5-flash"
    assert response.json()["target_id"] == "topic-1"


def test_post_gemini_topic_prediction_returns_503_when_gemini_unavailable() -> None:
    payload = {
        "scope": "topic",
        "model_name": "tfidf-logreg",
        "topic": {
            "topic_id": "topic-1",
            "title": "GDP grows",
            "summary": "GDP grows",
            "overall_impact": "positive",
            "confidence": 0.8,
            "positive_count": 1,
            "neutral_count": 0,
            "negative_count": 0,
            "forecast": "Базовый прогноз.",
            "arguments": ["Рост ВВП поддерживает ожидания."],
            "risks": [],
            "news": [
                {
                    "id": "news-1",
                    "title": "GDP grows",
                    "source": "demo",
                    "impact": "positive",
                    "score": None,
                }
            ],
        },
        "news_id": None,
    }

    with make_client(UnavailableGeminiForecastProvider()) as client:
        response = client.post("/api/v1/topic-forecast/gemini-predictions", json=payload)

    assert response.status_code == 503
    assert "GEMINI API key is not configured" in response.json()["detail"]
