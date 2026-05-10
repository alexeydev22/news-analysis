from pathlib import Path

import joblib
import pytest
from analysis_service.domain.errors import ModelUnavailableError
from analysis_service.domain.model import NewsText
from analysis_service.infrastructure.classifiers import (
    JoblibImpactClassifier,
    StaticImpactClassifier,
    StaticModelRegistry,
)
from economic_news_contracts.analysis import AnalysisModelName, ImpactLabel


class FakeEstimator:
    def predict(self, texts: list[str]) -> list[str]:
        assert texts == ["Markets rise"]
        return ["positive"]


class FakeProbabilisticEstimator:
    classes_ = ["negative", "neutral", "positive"]

    def predict(self, texts: list[str]) -> list[str]:
        assert texts == ["Markets rise"]
        return ["positive"]

    def predict_proba(self, texts: list[str]) -> list[list[float]]:
        assert texts == ["Markets rise"]
        return [[0.1, 0.2, 0.7]]


class FailingProbabilisticEstimator(FakeEstimator):
    classes_ = ["negative", "neutral", "positive"]

    def predict_proba(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("broken probability")


class FailingEstimator:
    def predict(self, texts: list[str]) -> list[str]:
        raise RuntimeError("broken estimator")


def test_static_classifier_returns_configured_prediction() -> None:
    classifier = StaticImpactClassifier(
        model_name=AnalysisModelName.TFIDF_LOGREG,
        impact=ImpactLabel.NEUTRAL,
    )

    prediction = classifier.predict(NewsText.from_raw("Markets wait"))

    assert prediction.model_name == AnalysisModelName.TFIDF_LOGREG
    assert prediction.impact == ImpactLabel.NEUTRAL
    assert prediction.metadata == {"source": "static"}


def test_joblib_classifier_predicts_with_loaded_estimator(tmp_path: Path) -> None:
    model_path = tmp_path / "model.joblib"
    joblib.dump(FakeEstimator(), model_path)
    classifier = JoblibImpactClassifier(
        model_name=AnalysisModelName.TFIDF_LOGREG,
        artifact_path=model_path,
    )

    prediction = classifier.predict(NewsText.from_raw("Markets rise"))

    assert prediction.model_name == AnalysisModelName.TFIDF_LOGREG
    assert prediction.impact == ImpactLabel.POSITIVE
    assert prediction.metadata == {"artifact_path": str(model_path), "source": "joblib"}


def test_joblib_classifier_uses_predict_proba_confidence(tmp_path: Path) -> None:
    model_path = tmp_path / "model.joblib"
    joblib.dump(FakeProbabilisticEstimator(), model_path)
    classifier = JoblibImpactClassifier(
        model_name=AnalysisModelName.TFIDF_LOGREG,
        artifact_path=model_path,
    )

    prediction = classifier.predict(NewsText.from_raw("Markets rise"))

    assert prediction.model_name == AnalysisModelName.TFIDF_LOGREG
    assert prediction.impact == ImpactLabel.POSITIVE
    assert prediction.confidence == 0.7
    assert prediction.metadata == {
        "artifact_path": str(model_path),
        "source": "joblib",
    }


def test_joblib_classifier_reports_missing_artifact(tmp_path: Path) -> None:
    classifier = JoblibImpactClassifier(
        model_name=AnalysisModelName.TFIDF_LOGREG,
        artifact_path=tmp_path / "missing.joblib",
    )

    with pytest.raises(ModelUnavailableError):
        classifier.predict(NewsText.from_raw("Markets rise"))


def test_joblib_classifier_wraps_unloadable_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_path = tmp_path / "model.joblib"
    model_path.write_bytes(b"not a real joblib artifact")

    def fail_load(path: Path) -> object:
        raise ModuleNotFoundError("economic_news_research")

    monkeypatch.setattr(joblib, "load", fail_load)
    classifier = JoblibImpactClassifier(
        model_name=AnalysisModelName.TFIDF_LOGREG,
        artifact_path=model_path,
    )

    with pytest.raises(ModelUnavailableError):
        classifier.predict(NewsText.from_raw("Markets rise"))


def test_joblib_classifier_wraps_prediction_failure(tmp_path: Path) -> None:
    model_path = tmp_path / "model.joblib"
    joblib.dump(FailingEstimator(), model_path)
    classifier = JoblibImpactClassifier(
        model_name=AnalysisModelName.TFIDF_LOGREG,
        artifact_path=model_path,
    )

    with pytest.raises(ModelUnavailableError):
        classifier.predict(NewsText.from_raw("Markets rise"))


def test_joblib_classifier_wraps_predict_proba_failure(tmp_path: Path) -> None:
    model_path = tmp_path / "model.joblib"
    joblib.dump(FailingProbabilisticEstimator(), model_path)
    classifier = JoblibImpactClassifier(
        model_name=AnalysisModelName.TFIDF_LOGREG,
        artifact_path=model_path,
    )

    with pytest.raises(ModelUnavailableError):
        classifier.predict(NewsText.from_raw("Markets rise"))


def test_static_registry_returns_classifier_by_name() -> None:
    classifier = StaticImpactClassifier(
        model_name=AnalysisModelName.TFIDF_LOGREG,
        impact=ImpactLabel.POSITIVE,
    )
    registry = StaticModelRegistry([classifier])

    assert registry.get(AnalysisModelName.TFIDF_LOGREG) is classifier


def test_static_registry_reports_unknown_model() -> None:
    registry = StaticModelRegistry([])

    with pytest.raises(ModelUnavailableError):
        registry.get(AnalysisModelName.TFIDF_LOGREG)
