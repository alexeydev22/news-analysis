from pathlib import Path

import mlflow

from economic_news_research.data import load_news_dataset, split_news_dataset
from economic_news_research.modeling import (
    BaselineTrainingResult,
    build_baseline_pipeline,
    train_baseline_model,
)
from economic_news_research.tracking import log_baseline_to_mlflow, save_baseline_artifacts

FIXTURE = Path(__file__).parent / "fixtures" / "news_impact_sample.csv"


def test_build_baseline_pipeline_predicts_labels() -> None:
    pipeline = build_baseline_pipeline(max_features=100, c_value=1.0, ngram_range=(1, 1))
    dataset = load_news_dataset(FIXTURE)

    pipeline.fit(dataset["text"], dataset["impact"])
    predictions = pipeline.predict(dataset["text"])

    assert len(predictions) == len(dataset)
    assert set(predictions).issubset({"positive", "neutral", "negative"})


def test_train_baseline_model_returns_metrics() -> None:
    dataset = load_news_dataset(FIXTURE)
    split = split_news_dataset(dataset, random_state=42)

    result = train_baseline_model(split, random_state=42)

    assert isinstance(result, BaselineTrainingResult)
    assert result.model_name == "tfidf-logreg"
    assert result.validation_metrics.confusion_matrix.shape == (3, 3)
    assert result.best_params["classifier__C"] in {0.1, 1.0, 10.0}


def test_save_baseline_artifacts_writes_expected_files(tmp_path: Path) -> None:
    dataset = load_news_dataset(FIXTURE)
    split = split_news_dataset(dataset, random_state=42)
    result = train_baseline_model(split, random_state=42)

    save_baseline_artifacts(result, output_dir=tmp_path)

    assert (tmp_path / "tfidf-logreg.joblib").exists()
    assert (tmp_path / "tfidf-logreg_metrics.json").exists()
    assert (tmp_path / "tfidf-logreg_confusion_matrix.csv").exists()
    assert (tmp_path / "model_comparison.csv").exists()


def test_log_baseline_to_mlflow_creates_experiment_for_fresh_tracking_uri(
    tmp_path: Path,
) -> None:
    dataset = load_news_dataset(FIXTURE)
    split = split_news_dataset(dataset, random_state=42)
    result = train_baseline_model(split, random_state=42)
    artifacts_dir = tmp_path / "artifacts"
    save_baseline_artifacts(result, output_dir=artifacts_dir)

    previous_tracking_uri = mlflow.get_tracking_uri()
    tracking_database = tmp_path / "mlflow.db"
    mlflow.set_tracking_uri(f"sqlite:///{tracking_database}")
    try:
        log_baseline_to_mlflow(
            result,
            artifact_dir=artifacts_dir,
            tracking_uri=f"sqlite:///{tracking_database}",
        )
    finally:
        mlflow.set_tracking_uri(previous_tracking_uri)

    assert tracking_database.exists()
