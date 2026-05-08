from typing import Any, cast

import pytest
from analysis_service.domain.errors import EmptyNewsTextError, InvalidPredictionConfidenceError
from analysis_service.domain.model import ImpactPrediction, NewsText
from economic_news_contracts.analysis import AnalysisModelName, ImpactLabel


def test_news_text_trims_value() -> None:
    news_text = NewsText.from_raw("  Markets rise after strong earnings.  ")

    assert news_text.value == "Markets rise after strong earnings."


def test_news_text_rejects_blank_value() -> None:
    with pytest.raises(EmptyNewsTextError):
        NewsText.from_raw("   ")


def test_impact_prediction_builds_default_explanation() -> None:
    prediction = ImpactPrediction(
        model_name=AnalysisModelName.TFIDF_LOGREG,
        impact=ImpactLabel.POSITIVE,
    )

    assert prediction.explanation == "Модель классифицировала влияние новости как позитивное."
    assert prediction.confidence is None
    assert prediction.metadata == {}


def test_impact_prediction_copies_metadata_as_read_only_mapping() -> None:
    metadata = {"source": "classifier"}
    prediction = ImpactPrediction(
        model_name=AnalysisModelName.TFIDF_LOGREG,
        impact=ImpactLabel.POSITIVE,
        metadata=metadata,
    )

    metadata["source"] = "mutated"

    assert prediction.metadata == {"source": "classifier"}
    with pytest.raises(TypeError):
        cast(Any, prediction.metadata)["source"] = "changed"


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_impact_prediction_rejects_invalid_confidence(confidence: float) -> None:
    with pytest.raises(InvalidPredictionConfidenceError):
        ImpactPrediction(
            model_name=AnalysisModelName.TFIDF_LOGREG,
            impact=ImpactLabel.POSITIVE,
            confidence=confidence,
        )
