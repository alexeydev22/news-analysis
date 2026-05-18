from pathlib import Path

import joblib
import pytest
from analysis_service.application.use_cases import (
    EnqueueMlReportJob,
    GenerateGeminiTopicForecast,
    GetLatestMlReport,
    GetMlReportJob,
)
from analysis_service.domain.errors import ModelUnavailableError
from analysis_service.domain.model import NewsText
from analysis_service.infrastructure.gemini_forecast_client import (
    GeminiEconomicForecastGenerator,
)
from analysis_service.main.container import AnalysisServiceProvider
from analysis_service.main.settings import AnalysisServiceSettings
from economic_news_contracts.analysis import AnalysisModelName, ImpactLabel


class FakeEstimator:
    def predict(self, texts: list[str]) -> list[str]:
        return ["positive" for _ in texts]


def test_analysis_settings_use_larger_training_caps_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANALYSIS_ML_TRAIN_MAX_ROWS", raising=False)
    monkeypatch.delenv("ANALYSIS_ML_EMBEDDING_MAX_ROWS", raising=False)
    monkeypatch.delenv("ANALYSIS_ML_TRANSFORMER_MAX_ROWS", raising=False)
    settings = AnalysisServiceSettings(_env_file=None)

    assert settings.ml_train_max_rows == 20_000
    assert settings.ml_embedding_max_rows == 5_000
    assert settings.ml_transformer_max_rows == 5_000


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


def test_provider_resolves_ml_report_use_cases(tmp_path: Path) -> None:
    settings = AnalysisServiceSettings(
        ml_report_jobs_dir=tmp_path / "jobs",
        ml_report_output_path=tmp_path / "model-report.json",
    )
    provider = AnalysisServiceProvider(settings)
    storage = provider.ml_report_storage(settings)
    queue = provider.ml_report_task_queue()

    assert isinstance(provider.enqueue_ml_report_job(queue, storage), EnqueueMlReportJob)
    assert isinstance(provider.get_ml_report_job(storage), GetMlReportJob)
    assert isinstance(provider.get_latest_ml_report(storage), GetLatestMlReport)


def test_provider_resolves_gemini_forecast_use_case() -> None:
    settings = AnalysisServiceSettings(use_static_classifier=True)
    provider = AnalysisServiceProvider(settings)
    generator = provider.economic_forecast_generator(settings)

    assert isinstance(generator, GeminiEconomicForecastGenerator)
    assert isinstance(
        provider.generate_gemini_topic_forecast(generator),
        GenerateGeminiTopicForecast,
    )
