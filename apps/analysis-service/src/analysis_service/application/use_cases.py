from economic_news_contracts.analysis import AnalysisModelName

from analysis_service.application.ports import ModelRegistry
from analysis_service.domain.model import ImpactPrediction, NewsText


class AnalyzeNewsImpact:
    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    def execute(self, *, text: str, model_name: AnalysisModelName) -> ImpactPrediction:
        news_text = NewsText.from_raw(text)
        classifier = self._registry.get(model_name)
        return classifier.predict(news_text)
