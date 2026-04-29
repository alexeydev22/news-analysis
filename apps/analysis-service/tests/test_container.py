from pathlib import Path

import joblib
import pytest
from analysis_service.domain.errors import ModelUnavailableError
from analysis_service.domain.model import NewsText
from analysis_service.main.container import AnalysisServiceProvider
from analysis_service.main.settings import AnalysisServiceSettings
from economic_news_contracts.analysis import AnalysisModelName, ImpactLabel


class FakeEstimator:
    def predict(self, texts: list[str]) -> list[str]:
        return ["positive" for _ in texts]


def test_production_registry_uses_only_existing_artifact_paths(tmp_path: Path) -> None:
    tfidf_artifact_path = tmp_path / "tfidf-logreg.joblib"
    joblib.dump(FakeEstimator(), tfidf_artifact_path)
    settings = AnalysisServiceSettings(
        tfidf_artifact_path=tfidf_artifact_path,
        embedding_artifact_path=tmp_path / "missing-embedding.joblib",
        transformer_artifact_path=tmp_path / "missing-transformer.joblib",
    )
    registry = AnalysisServiceProvider(settings).model_registry(settings)

    prediction = registry.get(AnalysisModelName.TFIDF_LOGREG).predict(
        NewsText.from_raw("Markets rise"),
    )

    assert prediction.impact == ImpactLabel.POSITIVE
    with pytest.raises(ModelUnavailableError):
        registry.get(AnalysisModelName.TINY_TRANSFORMER_CLASSIFIER)
