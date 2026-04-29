from typing import Any

from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider
from economic_news_contracts.analysis import AnalysisModelName, ImpactLabel

from analysis_service.application.ports import ModelRegistry
from analysis_service.application.use_cases import AnalyzeNewsImpact
from analysis_service.infrastructure.classifiers import (
    JoblibImpactClassifier,
    StaticImpactClassifier,
    StaticModelRegistry,
)
from analysis_service.main.settings import AnalysisServiceSettings


class AnalysisServiceProvider(Provider):
    def __init__(self, settings: AnalysisServiceSettings | None = None) -> None:
        super().__init__()
        self._settings = settings

    @provide(scope=Scope.APP)
    def settings(self) -> AnalysisServiceSettings:
        return self._settings or AnalysisServiceSettings()

    @provide(scope=Scope.APP, provides=ModelRegistry)
    def model_registry(self, settings: AnalysisServiceSettings) -> StaticModelRegistry:
        if settings.use_static_classifier:
            return StaticModelRegistry(
                [
                    StaticImpactClassifier(
                        model_name=AnalysisModelName.TFIDF_LOGREG,
                        impact=ImpactLabel.NEUTRAL,
                    ),
                ],
            )
        return StaticModelRegistry(
            [
                JoblibImpactClassifier(
                    model_name=AnalysisModelName.TFIDF_LOGREG,
                    artifact_path=settings.tfidf_artifact_path,
                ),
                JoblibImpactClassifier(
                    model_name=AnalysisModelName.EMBEDDING_LOGREG,
                    artifact_path=settings.embedding_artifact_path,
                ),
                JoblibImpactClassifier(
                    model_name=AnalysisModelName.TINY_TRANSFORMER_CLASSIFIER,
                    artifact_path=settings.transformer_artifact_path,
                ),
            ],
        )

    @provide(scope=Scope.APP)
    def analyze_news_impact(self, registry: ModelRegistry) -> AnalyzeNewsImpact:
        return AnalyzeNewsImpact(registry)


def create_container(settings: AnalysisServiceSettings | None = None) -> Any:
    return make_async_container(AnalysisServiceProvider(settings), FastapiProvider())
