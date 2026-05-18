import json
from pathlib import Path
from typing import Any

import joblib
import mlflow
import numpy as np
import pandas as pd
from mlflow.entities import Experiment

from economic_news_research.metrics import ClassificationMetrics
from economic_news_research.modeling import IMPACT_LABELS, BaselineTrainingResult
from economic_news_research.paths import MLFLOW_DIR
from economic_news_research.results import ModelTrainingResult

MLFLOW_EXPERIMENT_NAME = "economic-news-research"
MLFLOW_DATABASE = MLFLOW_DIR / "mlflow.db"
DEFAULT_MLFLOW_TRACKING_URI = f"sqlite:///{MLFLOW_DATABASE}"


def save_baseline_artifacts(result: BaselineTrainingResult, *, output_dir: Path) -> None:
    save_model_artifacts(result, output_dir=output_dir)


def save_model_artifacts(result: ModelTrainingResult, *, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(result.estimator, output_dir / f"{result.model_name}.joblib")
    (output_dir / f"{result.model_name}_metrics.json").write_text(
        json.dumps(_serialize_model_metrics(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    confusion_matrix = pd.DataFrame(
        result.test_metrics.confusion_matrix,
        index=pd.Index(IMPACT_LABELS),
        columns=pd.Index(IMPACT_LABELS),
    )
    confusion_matrix.to_csv(output_dir / f"{result.model_name}_confusion_matrix.csv")
    write_model_comparison([result], output_path=output_dir / "model_comparison.csv")


def write_model_comparison(
    results: list[ModelTrainingResult],
    *,
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([_build_comparison_row(result) for result in results]).to_csv(
        output_path,
        index=False,
    )
    return output_path


def log_baseline_to_mlflow(
    result: BaselineTrainingResult,
    *,
    artifact_dir: Path,
    tracking_uri: str | None = None,
) -> None:
    _configure_default_tracking_uri(tracking_uri=tracking_uri)
    experiment = _ensure_experiment(artifact_dir=artifact_dir, tracking_uri=tracking_uri)
    with mlflow.start_run(
        experiment_id=experiment.experiment_id,
        run_name=result.model_name,
        nested=mlflow.active_run() is not None,
    ):
        mlflow.log_params(result.best_params)
        mlflow.log_metrics(
            {
                "validation_accuracy": float(result.validation_metrics.accuracy),
                "validation_macro_f1": float(result.validation_metrics.macro_f1),
                "test_accuracy": float(result.test_metrics.accuracy),
                "test_macro_f1": float(result.test_metrics.macro_f1),
            }
        )
        mlflow.log_artifacts(str(artifact_dir))


def _configure_default_tracking_uri(*, tracking_uri: str | None) -> None:
    if tracking_uri is not None:
        mlflow.set_tracking_uri(tracking_uri)
        return

    MLFLOW_DIR.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(DEFAULT_MLFLOW_TRACKING_URI)


def _ensure_experiment(*, artifact_dir: Path, tracking_uri: str | None) -> Experiment:
    experiment = mlflow.get_experiment_by_name(MLFLOW_EXPERIMENT_NAME)
    if experiment is not None:
        return experiment

    experiment_id = mlflow.create_experiment(
        MLFLOW_EXPERIMENT_NAME,
        artifact_location=_build_artifact_store_path(
            artifact_dir=artifact_dir,
            tracking_uri=tracking_uri,
        ).as_uri(),
    )
    experiment = mlflow.get_experiment(experiment_id)
    if experiment is None:
        raise RuntimeError(f"MLflow experiment was not created: {MLFLOW_EXPERIMENT_NAME}")
    return experiment


def _build_artifact_store_path(*, artifact_dir: Path, tracking_uri: str | None) -> Path:
    if tracking_uri is None:
        return MLFLOW_DIR / "artifacts"

    artifact_path = artifact_dir.resolve()
    return artifact_path.parent / f"{artifact_path.name}-mlflow-artifacts"


def _build_comparison_row(result: ModelTrainingResult) -> dict[str, Any]:
    return {
        "model_name": result.model_name,
        "validation_accuracy": float(result.validation_metrics.accuracy),
        "validation_macro_f1": float(result.validation_metrics.macro_f1),
        "test_accuracy": float(result.test_metrics.accuracy),
        "test_macro_f1": float(result.test_metrics.macro_f1),
        "inference_seconds_per_sample": float(
            result.inference_seconds_per_sample,
        ),
        "best_params": json.dumps(
            _to_json_value(result.best_params),
            ensure_ascii=False,
            sort_keys=True,
        ),
    }


def _serialize_model_metrics(result: ModelTrainingResult) -> dict[str, Any]:
    return {
        "model_name": result.model_name,
        "best_params": _to_json_value(result.best_params),
        "validation": _serialize_classification_metrics(result.validation_metrics),
        "test": _serialize_classification_metrics(result.test_metrics),
        "validation_per_class": result.validation_metrics.per_class,
        "test_per_class": result.test_metrics.per_class,
    }


def _serialize_classification_metrics(metrics: ClassificationMetrics) -> dict[str, Any]:
    return {
        "accuracy": float(metrics.accuracy),
        "macro_precision": float(metrics.macro_precision),
        "macro_recall": float(metrics.macro_recall),
        "macro_f1": float(metrics.macro_f1),
        "per_class": metrics.per_class,
    }


def _to_json_value(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return [_to_json_value(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _to_json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_to_json_value(item) for item in value]
    return value
