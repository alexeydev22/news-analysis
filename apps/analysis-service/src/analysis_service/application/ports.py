from typing import Protocol

from economic_news_contracts.analysis import AnalysisModelName

from analysis_service.domain.model import ImpactPrediction, NewsText


class ImpactClassifier(Protocol):
    model_name: AnalysisModelName

    def predict(self, text: NewsText) -> ImpactPrediction:
        """Predict economic impact for a normalized news text."""
        ...


class ModelRegistry(Protocol):
    def get(self, model_name: AnalysisModelName) -> ImpactClassifier:
        """Return classifier by model name or raise ModelUnavailableError."""
        ...
