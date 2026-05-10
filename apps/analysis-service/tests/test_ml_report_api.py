from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from analysis_service.application.use_cases import (
    EnqueueMlReportJob,
    GetLatestMlReport,
    GetMlReportJob,
)
from analysis_service.domain.errors import MlReportJobNotFoundError
from analysis_service.main.settings import AnalysisServiceSettings
from analysis_service.presentation.errors import register_error_handlers
from analysis_service.presentation.router import router
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider, setup_dishka
from economic_news_contracts.analysis import (
    EnqueueMlReportJobResponse,
    MlReportJobResponse,
    MlReportJobStatus,
)
from economic_news_framework.apps import create_service_app
from fastapi.testclient import TestClient


class StubEnqueueMlReportJob(EnqueueMlReportJob):
    def __init__(self) -> None:
        pass

    async def execute(self) -> EnqueueMlReportJobResponse:
        return EnqueueMlReportJobResponse(job_id="job-1")


class StubGetMlReportJob(GetMlReportJob):
    def __init__(self) -> None:
        pass

    async def execute(self, job_id: str) -> MlReportJobResponse:
        return MlReportJobResponse(
            job_id=job_id,
            status=MlReportJobStatus.SUCCEEDED,
            report_path="reports/ml/model-report.json",
        )


class StubMissingMlReportJob(GetMlReportJob):
    def __init__(self) -> None:
        pass

    async def execute(self, job_id: str) -> MlReportJobResponse:
        raise MlReportJobNotFoundError(job_id)


class StubGetLatestMlReport(GetLatestMlReport):
    def __init__(self) -> None:
        pass

    async def execute(self) -> dict[str, object] | None:
        return {
            "generated_at": "2026-05-10T10:00:00Z",
            "dataset": {
                "path": "data/raw/news_impact.csv",
                "row_count": 9,
                "class_distribution": {
                    "negative": 3,
                    "neutral": 3,
                    "positive": 3,
                },
            },
            "models": [
                {
                    "model_name": "tfidf-logreg",
                    "validation_accuracy": 1.0,
                    "validation_macro_f1": 1.0,
                    "test_accuracy": 1.0,
                    "test_macro_f1": 1.0,
                    "inference_seconds_per_sample": 0.001,
                    "confusion_matrix": {
                        "labels": ["negative", "neutral", "positive"],
                        "matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                    },
                },
            ],
            "best_model": {
                "model_name": "tfidf-logreg",
                "validation_accuracy": 1.0,
                "validation_macro_f1": 1.0,
                "test_accuracy": 1.0,
                "test_macro_f1": 1.0,
                "inference_seconds_per_sample": 0.001,
                "confusion_matrix": None,
            },
            "top_features": {"tfidf-logreg": {"positive": ["gdp"]}},
        }


class MlReportProvider(Provider):
    def __init__(
        self,
        enqueue: StubEnqueueMlReportJob,
        get_job: GetMlReportJob | None = None,
    ) -> None:
        super().__init__()
        self._enqueue = enqueue
        self._get_job = get_job or StubGetMlReportJob()

    @provide(scope=Scope.APP)
    def settings(self) -> AnalysisServiceSettings:
        return AnalysisServiceSettings(use_static_classifier=True)

    @provide(scope=Scope.APP)
    def enqueue_ml_report_job(self) -> EnqueueMlReportJob:
        return self._enqueue

    @provide(scope=Scope.APP)
    def get_ml_report_job(self) -> GetMlReportJob:
        return self._get_job

    @provide(scope=Scope.APP)
    def get_latest_ml_report(self) -> GetLatestMlReport:
        return StubGetLatestMlReport()


def make_client(
    enqueue: StubEnqueueMlReportJob,
    get_job: GetMlReportJob | None = None,
) -> TestClient:
    app = create_service_app(service_name="analysis-service", routers=(router,))
    container = make_async_container(MlReportProvider(enqueue, get_job), FastapiProvider())
    setup_dishka(container=container, app=app)
    register_error_handlers(app)

    @asynccontextmanager
    async def close_container(_: object) -> AsyncIterator[None]:
        yield
        await container.close()

    app.router.lifespan_context = close_container
    return TestClient(app)


def test_enqueue_ml_report_job_endpoint_uses_configured_dataset() -> None:
    enqueue = StubEnqueueMlReportJob()

    with make_client(enqueue) as client:
        response = client.post(
            "/api/v1/ml-report/jobs",
            json={},
        )

    assert response.status_code == 202
    assert response.json() == {"job_id": "job-1", "status": "queued"}


def test_enqueue_ml_report_job_endpoint_rejects_dataset_path_override() -> None:
    with make_client(StubEnqueueMlReportJob()) as client:
        response = client.post(
            "/api/v1/ml-report/jobs",
            json={"dataset_path": "data/raw/other.csv"},
        )

    assert response.status_code == 422


def test_get_ml_report_job_endpoint_returns_status() -> None:
    with make_client(StubEnqueueMlReportJob()) as client:
        response = client.get("/api/v1/ml-report/jobs/job-1")

    assert response.status_code == 200
    assert response.json() == {
        "job_id": "job-1",
        "status": "succeeded",
        "message": None,
        "report_path": "reports/ml/model-report.json",
    }


def test_get_ml_report_job_endpoint_returns_404_for_missing_job() -> None:
    with make_client(StubEnqueueMlReportJob(), StubMissingMlReportJob()) as client:
        response = client.get("/api/v1/ml-report/jobs/missing-job")

    assert response.status_code == 404
    assert response.json()["detail"] == "ML report job not found: missing-job"


def test_get_latest_ml_report_endpoint_returns_report() -> None:
    with make_client(StubEnqueueMlReportJob()) as client:
        response = client.get("/api/v1/ml-report/latest")

    assert response.status_code == 200
    assert response.json()["dataset"]["row_count"] == 9
    assert response.json()["models"][0]["model_name"] == "tfidf-logreg"
