from collections.abc import Iterable
from pathlib import Path
from typing import Any

import joblib
from economic_news_contracts.analysis import AnalysisModelName, ImpactLabel

from analysis_service.application.ports import ImpactClassifier
from analysis_service.domain.errors import ModelUnavailableError
from analysis_service.domain.model import ImpactPrediction, NewsText


class StaticImpactClassifier:
    def __init__(
        self,
        *,
        model_name: AnalysisModelName,
        impact: ImpactLabel = ImpactLabel.NEUTRAL,
    ) -> None:
        self.model_name = model_name
        self._impact = impact

    def predict(self, text: NewsText) -> ImpactPrediction:
        return ImpactPrediction(
            model_name=self.model_name,
            impact=self._impact,
            metadata={"source": "static"},
        )


class JoblibImpactClassifier:
    def __init__(self, *, model_name: AnalysisModelName, artifact_path: Path) -> None:
        self.model_name = model_name
        self._artifact_path = artifact_path
        self._estimator: Any | None = None

    def predict(self, text: NewsText) -> ImpactPrediction:
        estimator = self._load_estimator()
        try:
            raw_prediction = estimator.predict([text.value])[0]
            impact = ImpactLabel(str(raw_prediction))
        except Exception as exc:
            raise ModelUnavailableError(self.model_name) from exc
        return ImpactPrediction(
            model_name=self.model_name,
            impact=impact,
            metadata={"artifact_path": str(self._artifact_path)},
        )

    def _load_estimator(self) -> Any:
        if self._estimator is not None:
            return self._estimator
        if not self._artifact_path.exists():
            raise ModelUnavailableError(self.model_name)
        try:
            self._estimator = joblib.load(self._artifact_path)
        except Exception as exc:
            raise ModelUnavailableError(self.model_name) from exc
        return self._estimator


class StaticModelRegistry:
    def __init__(self, classifiers: Iterable[ImpactClassifier]) -> None:
        self._classifiers = {classifier.model_name: classifier for classifier in classifiers}

    def get(self, model_name: AnalysisModelName) -> ImpactClassifier:
        try:
            return self._classifiers[model_name]
        except KeyError as exc:
            raise ModelUnavailableError(model_name) from exc
