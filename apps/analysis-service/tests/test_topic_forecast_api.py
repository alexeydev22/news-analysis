from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from analysis_service.application.use_cases import (
    EnqueueTopicForecastJob,
    GetLatestTopicForecast,
    GetTopicForecastJob,
)
from analysis_service.domain.errors import TopicForecastJobNotFoundError
from analysis_service.main.settings import AnalysisServiceSettings
from analysis_service.presentation.errors import register_error_handlers
from analysis_service.presentation.router import router
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider, setup_dishka
from economic_news_contracts.analysis import (
    EnqueueTopicForecastJobResponse,
    ImpactLabel,
    TopicForecastItemResponse,
    TopicForecastJobResponse,
    TopicForecastJobStatus,
    TopicForecastNewsItemResponse,
    TopicForecastResponse,
)
from economic_news_framework.apps import create_service_app
from fastapi.testclient import TestClient


class StubEnqueueTopicForecastJob(EnqueueTopicForecastJob):
    def __init__(self) -> None:
        pass

    async def execute(self) -> EnqueueTopicForecastJobResponse:
        return EnqueueTopicForecastJobResponse(job_id="topic-job-1")


class StubGetTopicForecastJob(GetTopicForecastJob):
    def __init__(self) -> None:
        pass

    async def execute(self, job_id: str) -> TopicForecastJobResponse:
        return TopicForecastJobResponse(
            job_id=job_id,
            status=TopicForecastJobStatus.SUCCEEDED,
            report_path="reports/topic-forecast/latest.json",
        )


class StubMissingTopicForecastJob(GetTopicForecastJob):
    def __init__(self) -> None:
        pass

    async def execute(self, job_id: str) -> TopicForecastJobResponse:
        raise TopicForecastJobNotFoundError(job_id)


class StubGetLatestTopicForecast(GetLatestTopicForecast):
    def __init__(self) -> None:
        pass

    async def execute(self) -> TopicForecastResponse | None:
        return TopicForecastResponse(
            generated_at="2026-05-10T10:00:00Z",
            topics=[
                TopicForecastItemResponse(
                    topic_id="topic-1",
                    title="GDP grows",
                    summary="GDP grows",
                    overall_impact=ImpactLabel.POSITIVE,
                    confidence=0.8,
                    positive_count=1,
                    neutral_count=0,
                    negative_count=0,
                    forecast="Позитивное влияние; не финансовая рекомендация.",
                    arguments=["Рост ВВП поддерживает ожидания."],
                    risks=[],
                    news=[
                        TopicForecastNewsItemResponse(
                            id="news-1",
                            title="GDP grows",
                            source="demo",
                            impact=ImpactLabel.POSITIVE,
                            score=None,
                        ),
                    ],
                ),
            ],
            metadata={"document_count": 1},
        )


class TopicForecastProvider(Provider):
    def __init__(
        self,
        enqueue: StubEnqueueTopicForecastJob,
        get_job: GetTopicForecastJob | None = None,
        latest: GetLatestTopicForecast | None = None,
    ) -> None:
        super().__init__()
        self._enqueue = enqueue
        self._get_job = get_job or StubGetTopicForecastJob()
        self._latest = latest or StubGetLatestTopicForecast()

    @provide(scope=Scope.APP)
    def settings(self) -> AnalysisServiceSettings:
        return AnalysisServiceSettings(use_static_classifier=True)

    @provide(scope=Scope.APP)
    def enqueue_topic_forecast_job(self) -> EnqueueTopicForecastJob:
        return self._enqueue

    @provide(scope=Scope.APP)
    def get_topic_forecast_job(self) -> GetTopicForecastJob:
        return self._get_job

    @provide(scope=Scope.APP)
    def get_latest_topic_forecast(self) -> GetLatestTopicForecast:
        return self._latest


def make_client(
    enqueue: StubEnqueueTopicForecastJob,
    get_job: GetTopicForecastJob | None = None,
    latest: GetLatestTopicForecast | None = None,
) -> TestClient:
    app = create_service_app(service_name="analysis-service", routers=(router,))
    container = make_async_container(
        TopicForecastProvider(enqueue, get_job, latest),
        FastapiProvider(),
    )
    setup_dishka(container=container, app=app)
    register_error_handlers(app)

    @asynccontextmanager
    async def close_container(_: object) -> AsyncIterator[None]:
        yield
        await container.close()

    app.router.lifespan_context = close_container
    return TestClient(app)


def test_enqueue_topic_forecast_job_endpoint_returns_accepted_status() -> None:
    with make_client(StubEnqueueTopicForecastJob()) as client:
        response = client.post("/api/v1/topic-forecast/jobs", json={})

    assert response.status_code == 202
    assert response.json() == {"job_id": "topic-job-1", "status": "queued"}


def test_get_topic_forecast_job_endpoint_returns_status() -> None:
    with make_client(StubEnqueueTopicForecastJob()) as client:
        response = client.get("/api/v1/topic-forecast/jobs/topic-job-1")

    assert response.status_code == 200
    assert response.json() == {
        "job_id": "topic-job-1",
        "status": "succeeded",
        "message": None,
        "report_path": "reports/topic-forecast/latest.json",
    }


def test_get_topic_forecast_job_endpoint_returns_404_for_missing_job() -> None:
    with make_client(
        StubEnqueueTopicForecastJob(),
        StubMissingTopicForecastJob(),
    ) as client:
        response = client.get("/api/v1/topic-forecast/jobs/missing-job")

    assert response.status_code == 404
    assert response.json()["detail"] == "Topic forecast job not found: missing-job"


def test_get_latest_topic_forecast_endpoint_returns_report() -> None:
    with make_client(StubEnqueueTopicForecastJob()) as client:
        response = client.get("/api/v1/topic-forecast/latest")

    assert response.status_code == 200
    assert response.json()["topics"][0]["overall_impact"] == "positive"
    assert response.json()["metadata"]["document_count"] == 1


class EmptyLatestTopicForecast(GetLatestTopicForecast):
    def __init__(self) -> None:
        pass

    async def execute(self) -> TopicForecastResponse | None:
        return None


def test_get_latest_topic_forecast_endpoint_returns_null_when_missing() -> None:
    with make_client(
        StubEnqueueTopicForecastJob(),
        latest=EmptyLatestTopicForecast(),
    ) as client:
        response = client.get("/api/v1/topic-forecast/latest")

    assert response.status_code == 200
    assert response.json() is None
