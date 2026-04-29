import pytest
from analysis_service.application.ports import ImpactClassifier
from analysis_service.application.use_cases import AnalyzeNewsImpact
from analysis_service.domain.errors import ModelUnavailableError
from analysis_service.domain.model import ImpactPrediction, NewsText
from economic_news_contracts.analysis import AnalysisModelName, ImpactLabel


class FakeClassifier:
    model_name = AnalysisModelName.TFIDF_LOGREG

    def predict(self, text: NewsText) -> ImpactPrediction:
        assert text.value == "Markets rise"
        return ImpactPrediction(
            model_name=self.model_name,
            impact=ImpactLabel.POSITIVE,
            confidence=0.9,
        )


class FakeRegistry:
    def __init__(self, classifier: ImpactClassifier | None = None) -> None:
        self.classifier = classifier
        self.requested_model: AnalysisModelName | None = None

    def get(self, model_name: AnalysisModelName) -> ImpactClassifier:
        self.requested_model = model_name
        if self.classifier is None:
            raise ModelUnavailableError(model_name)
        return self.classifier


def test_analyze_news_impact_uses_requested_model() -> None:
    registry = FakeRegistry(FakeClassifier())
    use_case = AnalyzeNewsImpact(registry)

    prediction = use_case.execute(
        text=" Markets rise ",
        model_name=AnalysisModelName.TFIDF_LOGREG,
    )

    assert registry.requested_model == AnalysisModelName.TFIDF_LOGREG
    assert prediction.impact == ImpactLabel.POSITIVE
    assert prediction.confidence == 0.9


def test_analyze_news_impact_propagates_unavailable_model() -> None:
    use_case = AnalyzeNewsImpact(FakeRegistry())

    with pytest.raises(ModelUnavailableError):
        use_case.execute(
            text="Markets rise",
            model_name=AnalysisModelName.TFIDF_LOGREG,
        )
