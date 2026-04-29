import pytest
from analysis_service.domain.errors import EmptyNewsTextError
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

    assert prediction.explanation == "Model classified the news text as positive."
    assert prediction.confidence is None
    assert prediction.metadata == {}
