from economic_news_contracts.analysis import AnalysisModelName, ImpactLabel
from economic_news_contracts.events import EventEnvelope
from economic_news_contracts.health import HealthResponse


def test_impact_label_values_are_stable() -> None:
    assert ImpactLabel.POSITIVE == "positive"
    assert ImpactLabel.NEUTRAL == "neutral"
    assert ImpactLabel.NEGATIVE == "negative"


def test_analysis_model_names_are_stable() -> None:
    assert AnalysisModelName.TFIDF_LOGREG == "tfidf-logreg"
    assert AnalysisModelName.RUBERT_TINY2_CLASSIFIER == "rubert-tiny2-classifier"
    assert AnalysisModelName.RUBERT_TINY2_FINETUNED == "rubert-tiny2-finetuned"


def test_event_envelope_contains_type_and_payload() -> None:
    event = EventEnvelope(event_type="analysis.completed", payload={"article_id": "a-1"})

    assert event.event_type == "analysis.completed"
    assert event.payload == {"article_id": "a-1"}


def test_health_response_defaults_to_ok() -> None:
    response = HealthResponse(service="api-gateway")

    assert response.status == "ok"
    assert response.service == "api-gateway"
