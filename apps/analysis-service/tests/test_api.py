from analysis_service.main.app import create_app
from economic_news_contracts.analysis import AnalysisModelName
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
