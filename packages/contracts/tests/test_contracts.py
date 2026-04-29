from economic_news_contracts.analysis import (
    AnalysisModelName,
    AnalyzeNewsRequest,
    AnalyzeNewsResponse,
    ImpactLabel,
)
from economic_news_contracts.events import EventEnvelope
from economic_news_contracts.health import HealthResponse


def test_impact_label_values_are_stable() -> None:
    assert ImpactLabel.POSITIVE == "positive"
    assert ImpactLabel.NEUTRAL == "neutral"
    assert ImpactLabel.NEGATIVE == "negative"


def test_analysis_model_names_are_stable() -> None:
    assert AnalysisModelName.TFIDF_LOGREG == "tfidf-logreg"
    assert AnalysisModelName.EMBEDDING_LOGREG == "embedding-logreg"
    assert AnalysisModelName.TINY_TRANSFORMER_CLASSIFIER == "tiny-transformer-classifier"


def test_analyze_news_request_trims_text() -> None:
    request = AnalyzeNewsRequest(
        text="  Central bank keeps rates unchanged.  ",
        analysis_model=AnalysisModelName.TFIDF_LOGREG,
    )

    assert request.text == "Central bank keeps rates unchanged."
    assert request.analysis_model == AnalysisModelName.TFIDF_LOGREG


def test_analyze_news_response_serializes_model_and_impact() -> None:
    response = AnalyzeNewsResponse(
        model_name=AnalysisModelName.TFIDF_LOGREG,
        impact=ImpactLabel.NEUTRAL,
        confidence=None,
        explanation="Model classified the news text as neutral.",
        metadata={},
    )

    assert response.model_dump(mode="json") == {
        "model_name": "tfidf-logreg",
        "impact": "neutral",
        "confidence": None,
        "explanation": "Model classified the news text as neutral.",
        "metadata": {},
    }


def test_event_envelope_contains_type_and_payload() -> None:
    event = EventEnvelope(event_type="analysis.completed", payload={"article_id": "a-1"})

    assert event.event_type == "analysis.completed"
    assert event.payload == {"article_id": "a-1"}


def test_health_response_defaults_to_ok() -> None:
    response = HealthResponse(service="api-gateway")

    assert response.status == "ok"
    assert response.service == "api-gateway"
