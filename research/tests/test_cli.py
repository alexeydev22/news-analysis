from pathlib import Path

import mlflow
import numpy as np
import pandas as pd

from economic_news_research.cli import (
    run_compare_models,
    run_eda,
    run_train_baseline,
    run_train_embedding,
    run_train_transformer,
    run_validate,
)
from economic_news_research.paths import MLFLOW_DIR, REPO_ROOT

FIXTURE = Path(__file__).parent / "fixtures" / "news_impact_sample.csv"


class FakeEmbedder:
    def encode(self, texts: list[str]) -> np.ndarray:
        rows: list[list[float]] = []
        for text in texts:
            lowered = text.lower()
            rows.append(
                [
                    float("rise" in lowered or "gain" in lowered or "strong" in lowered),
                    float("fall" in lowered or "decline" in lowered or "drops" in lowered),
                    float("stable" in lowered or "unchanged" in lowered or "wait" in lowered),
                ]
            )
        return np.array(rows, dtype=float)


class FakeTinyTransformerTrainer:
    best_params = {"model_name": "fake-tiny-transformer", "epochs": 1}

    def fit(
        self,
        train_texts: list[str],
        train_labels: list[str],
        validation_texts: list[str],
        validation_labels: list[str],
    ) -> None:
        self.majority_label = max(set(train_labels), key=train_labels.count)

    def predict(self, texts: list[str]) -> list[str]:
        return ["neutral" for _ in texts]


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


def test_run_train_embedding_writes_model_artifacts(tmp_path: Path) -> None:
    previous_tracking_uri = mlflow.get_tracking_uri()
    try:
        run_train_embedding(
            dataset_path=FIXTURE,
            output_dir=tmp_path,
            random_state=42,
            embedder=FakeEmbedder(),
        )
    finally:
        mlflow.set_tracking_uri(previous_tracking_uri)

    assert (tmp_path / "embedding-logreg.joblib").exists()
    assert (tmp_path / "model_comparison.csv").exists()


def test_run_train_transformer_writes_model_artifacts(tmp_path: Path) -> None:
    previous_tracking_uri = mlflow.get_tracking_uri()
    try:
        run_train_transformer(
            dataset_path=FIXTURE,
            output_dir=tmp_path,
            random_state=42,
            trainer=FakeTinyTransformerTrainer(),
        )
    finally:
        mlflow.set_tracking_uri(previous_tracking_uri)

    assert (tmp_path / "tiny-transformer-classifier.joblib").exists()
    assert (tmp_path / "model_comparison.csv").exists()


def test_run_compare_models_combines_existing_comparisons(tmp_path: Path) -> None:
    baseline_dir = tmp_path / "baseline"
    embedding_dir = tmp_path / "embedding"
    baseline_dir.mkdir()
    embedding_dir.mkdir()
    pd.DataFrame([{"model_name": "tfidf-logreg", "test_macro_f1": 0.4}]).to_csv(
        baseline_dir / "model_comparison.csv",
        index=False,
    )
    pd.DataFrame([{"model_name": "embedding-logreg", "test_macro_f1": 0.5}]).to_csv(
        embedding_dir / "model_comparison.csv",
        index=False,
    )

    output_path = run_compare_models(
        comparison_paths=[
            baseline_dir / "model_comparison.csv",
            embedding_dir / "model_comparison.csv",
        ],
        output_path=tmp_path / "model_comparison.csv",
    )

    comparison = pd.read_csv(output_path)
    assert comparison["model_name"].tolist() == ["tfidf-logreg", "embedding-logreg"]
