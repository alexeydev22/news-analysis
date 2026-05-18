from pathlib import Path

import mlflow
import pytest
from sklearn.model_selection import LeaveOneOut, StratifiedKFold

from economic_news_research import modeling
from economic_news_research.data import load_news_dataset, split_news_dataset
from economic_news_research.model_selection import safe_cv
from economic_news_research.modeling import (
    BaselineTrainingResult,
    baseline_param_grid,
    build_baseline_pipeline,
    train_baseline_model,
)
from economic_news_research.tracking import log_baseline_to_mlflow, save_baseline_artifacts

FIXTURE = Path(__file__).parent / "fixtures" / "news_impact_sample.csv"


@pytest.fixture
def fixture_safe_baseline_grid(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[object]]:
    grid = {
        "tfidf__max_features": [100],
        "tfidf__ngram_range": [(1, 1)],
        "tfidf__min_df": [1],
        "tfidf__max_df": [1.0],
        "tfidf__sublinear_tf": [True],
        "classifier__C": [1.0],
    }
    monkeypatch.setattr(modeling, "baseline_param_grid", lambda: grid)
    return grid


def test_build_baseline_pipeline_predicts_labels() -> None:
    pipeline = build_baseline_pipeline(max_features=100, c_value=1.0, ngram_range=(1, 1))
    dataset = load_news_dataset(FIXTURE)

    pipeline.fit(dataset["text"], dataset["impact"])
    predictions = pipeline.predict(dataset["text"])

    assert len(predictions) == len(dataset)
    assert set(predictions).issubset({"positive", "neutral", "negative"})


def test_build_baseline_pipeline_uses_richer_tfidf_defaults() -> None:
    pipeline = build_baseline_pipeline(
        max_features=20_000,
        c_value=3.0,
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.95,
        sublinear_tf=True,
    )

    vectorizer = pipeline.named_steps["tfidf"]
    classifier = pipeline.named_steps["classifier"]

    assert vectorizer.max_features == 20_000
    assert vectorizer.ngram_range == (1, 2)
    assert vectorizer.min_df == 2
    assert vectorizer.max_df == 0.95
    assert vectorizer.sublinear_tf is True
    assert classifier.class_weight == "balanced"


def test_baseline_param_grid_contains_large_vocabularies() -> None:
    grid = baseline_param_grid()

    assert grid["tfidf__max_features"] == [20_000, 50_000]
    assert grid["tfidf__min_df"] == [2]
    assert grid["tfidf__max_df"] == [0.95]
    assert grid["tfidf__sublinear_tf"] == [True]
    assert grid["tfidf__ngram_range"] == [(1, 2)]
    assert grid["classifier__C"] == [1.0, 3.0]


def test_train_baseline_model_returns_metrics(
    fixture_safe_baseline_grid: dict[str, list[object]],
) -> None:
    dataset = load_news_dataset(FIXTURE)
    split = split_news_dataset(dataset, random_state=42)

    result = train_baseline_model(split, random_state=42)

    assert isinstance(result, BaselineTrainingResult)
    assert result.model_name == "tfidf-logreg"
    assert result.validation_metrics.confusion_matrix.shape == (3, 3)
    assert result.best_params["classifier__C"] in fixture_safe_baseline_grid["classifier__C"]
    assert result.inference_seconds_per_sample >= 0


def test_safe_cv_uses_leave_one_out_for_tiny_classes() -> None:
    cv = safe_cv(["positive", "neutral", "negative"], random_state=42)

    assert isinstance(cv, LeaveOneOut)


def test_safe_cv_uses_stratified_k_fold_for_repeated_classes() -> None:
    cv = safe_cv(
        ["positive", "positive", "neutral", "neutral", "negative", "negative"],
        random_state=42,
    )

    assert isinstance(cv, StratifiedKFold)
    assert cv.n_splits == 2


@pytest.mark.usefixtures("fixture_safe_baseline_grid")
def test_save_baseline_artifacts_writes_expected_files(tmp_path: Path) -> None:
    dataset = load_news_dataset(FIXTURE)
    split = split_news_dataset(dataset, random_state=42)
    result = train_baseline_model(split, random_state=42)

    save_baseline_artifacts(result, output_dir=tmp_path)

    assert (tmp_path / "tfidf-logreg.joblib").exists()
    assert (tmp_path / "tfidf-logreg_metrics.json").exists()
    assert (tmp_path / "tfidf-logreg_confusion_matrix.csv").exists()
    assert (tmp_path / "model_comparison.csv").exists()


@pytest.mark.usefixtures("fixture_safe_baseline_grid")
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
