from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
import pytest

from economic_news_research import cli
from economic_news_research.cli import (
    run_build_model_report,
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
    best_params: dict[str, object] = {
        "model_name": "fake-tiny-transformer",
        "epochs": 1,
    }

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


def test_run_build_model_report_writes_report(tmp_path: Path) -> None:
    baseline_dir = tmp_path / "baseline"
    baseline_dir.mkdir()
    pd.DataFrame(
        [
            {
                "model_name": "tfidf-logreg",
                "validation_accuracy": 1.0,
                "validation_macro_f1": 1.0,
                "test_accuracy": 1.0,
                "test_macro_f1": 1.0,
                "inference_seconds_per_sample": 0.001,
            },
        ],
    ).to_csv(tmp_path / "model_comparison.csv", index=False)
    pd.DataFrame(
        [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
        index=["negative", "neutral", "positive"],
        columns=["negative", "neutral", "positive"],
    ).to_csv(baseline_dir / "tfidf-logreg_confusion_matrix.csv")

    output_path = run_build_model_report(
        dataset_path=FIXTURE,
        comparison_path=tmp_path / "model_comparison.csv",
        model_dirs=[baseline_dir],
        output_path=tmp_path / "model-report.json",
    )

    assert output_path == tmp_path / "model-report.json"
    assert output_path.exists()


def test_main_compare_models_uses_custom_comparisons_without_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    default_models_dir = tmp_path / "default-models"
    baseline_dir = default_models_dir / "baseline"
    baseline_dir.mkdir(parents=True)
    pd.DataFrame([{"model_name": "tfidf-logreg", "test_macro_f1": 0.4}]).to_csv(
        baseline_dir / "model_comparison.csv",
        index=False,
    )
    custom_path = tmp_path / "custom_model_comparison.csv"
    output_path = tmp_path / "model_comparison.csv"
    pd.DataFrame([{"model_name": "custom-model", "test_macro_f1": 0.9}]).to_csv(
        custom_path,
        index=False,
    )

    monkeypatch.setattr(cli, "MODELS_DIR", default_models_dir)
    monkeypatch.setattr(
        "sys.argv",
        [
            "economic-news-research",
            "compare-models",
            "--comparison",
            str(custom_path),
            "--output-path",
            str(output_path),
        ],
    )

    cli.main()

    assert capsys.readouterr().out == f"comparison_path={output_path}\n"
    comparison = pd.read_csv(output_path)
    assert comparison["model_name"].tolist() == ["custom-model"]


def test_main_compare_models_reports_missing_files_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "MODELS_DIR", tmp_path / "missing-models")
    monkeypatch.setattr(
        "sys.argv",
        [
            "economic-news-research",
            "compare-models",
            "--output-path",
            str(tmp_path / "model_comparison.csv"),
        ],
    )

    with pytest.raises(SystemExit) as error:
        cli.main()

    assert error.value.code == 2
    assert "No model comparison files found" in capsys.readouterr().err
