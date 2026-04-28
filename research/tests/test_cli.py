from pathlib import Path

import mlflow

from economic_news_research.cli import run_eda, run_train_baseline, run_validate
from economic_news_research.paths import MLFLOW_DIR, REPO_ROOT

FIXTURE = Path(__file__).parent / "fixtures" / "news_impact_sample.csv"


def test_run_validate_returns_row_count() -> None:
    assert run_validate(dataset_path=FIXTURE) == 9


def test_run_eda_writes_report(tmp_path: Path) -> None:
    run_eda(dataset_path=FIXTURE, output_dir=tmp_path)

    assert (tmp_path / "eda_summary.json").exists()


def test_run_train_baseline_writes_model_artifacts(tmp_path: Path) -> None:
    previous_tracking_uri = mlflow.get_tracking_uri()
    try:
        run_train_baseline(dataset_path=FIXTURE, output_dir=tmp_path, random_state=42)
    finally:
        mlflow.set_tracking_uri(previous_tracking_uri)

    assert (tmp_path / "tfidf-logreg.joblib").exists()
    assert (tmp_path / "model_comparison.csv").exists()
    assert (MLFLOW_DIR / "mlflow.db").exists()
    assert not (REPO_ROOT / "mlflow.db").exists()
    assert not (REPO_ROOT / "mlruns").exists()
