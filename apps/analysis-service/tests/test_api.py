from analysis_service.application.use_cases import AnalyzeNewsImpact
from analysis_service.domain.model import ImpactPrediction, NewsText
from analysis_service.main.app import create_app
from analysis_service.main.settings import AnalysisServiceSettings
from analysis_service.presentation.router import router
from economic_news_contracts.analysis import AnalysisModelName, ImpactLabel
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_analysis_service_health_endpoint() -> None:
    client = TestClient(create_app(use_static_classifier=True))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"service": "analysis-service", "status": "ok"}


def test_analyze_endpoint_returns_prediction() -> None:
    client = TestClient(create_app(use_static_classifier=True))

    response = client.post(
        "/api/v1/analyze",
        json={
            "text": "Markets rise after strong earnings.",
            "analysis_model": AnalysisModelName.TFIDF_LOGREG,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "model_name": "tfidf-logreg",
        "impact": "neutral",
        "confidence": None,
        "explanation": "Model classified the news text as neutral.",
        "metadata": {"source": "static"},
    }


def test_analyze_endpoint_rejects_blank_text() -> None:
    client = TestClient(create_app(use_static_classifier=True))

    response = client.post(
        "/api/v1/analyze",
        json={"text": "   ", "analysis_model": AnalysisModelName.TFIDF_LOGREG},
    )

    assert response.status_code == 422


def test_analyze_endpoint_reports_unavailable_model() -> None:
    client = TestClient(create_app(use_static_classifier=True))

    response = client.post(
        "/api/v1/analyze",
        json={
            "text": "Markets rise after strong earnings.",
            "analysis_model": AnalysisModelName.EMBEDDING_LOGREG,
        },
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Analysis model is unavailable: embedding-logreg",
    }


class PathMetadataClassifier:
    model_name = AnalysisModelName.TFIDF_LOGREG

    def predict(self, text: NewsText) -> ImpactPrediction:
        return ImpactPrediction(
            model_name=self.model_name,
            impact=ImpactLabel.POSITIVE,
            metadata={
                "artifact_path": "artifacts/models/baseline/tfidf-logreg.joblib",
                "source": "joblib",
            },
        )


class PathMetadataRegistry:
    def get(self, model_name: AnalysisModelName) -> PathMetadataClassifier:
        return PathMetadataClassifier()


def test_analyze_endpoint_hides_internal_metadata_paths() -> None:
    from dishka import Provider, Scope, make_async_container, provide
    from dishka.integrations.fastapi import FastapiProvider, setup_dishka
    from economic_news_framework.apps import create_service_app

    class TestProvider(Provider):
        @provide(scope=Scope.APP)
        def settings(self) -> AnalysisServiceSettings:
            return AnalysisServiceSettings(use_static_classifier=True)

        @provide(scope=Scope.APP)
        def use_case(self) -> AnalyzeNewsImpact:
            return AnalyzeNewsImpact(PathMetadataRegistry())

    app: FastAPI = create_service_app(service_name="analysis-service", routers=(router,))
    setup_dishka(make_async_container(TestProvider(), FastapiProvider()), app)
    client = TestClient(app)

    response = client.post(
        "/api/v1/analyze",
        json={
            "text": "Markets rise after strong earnings.",
            "analysis_model": AnalysisModelName.TFIDF_LOGREG,
        },
    )

    assert response.status_code == 200
    assert response.json()["metadata"] == {"source": "joblib"}
