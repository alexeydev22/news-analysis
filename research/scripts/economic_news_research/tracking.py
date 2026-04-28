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

MLFLOW_EXPERIMENT_NAME = "economic-news-research"


def save_baseline_artifacts(result: BaselineTrainingResult, *, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(result.estimator, output_dir / f"{result.model_name}.joblib")
    (output_dir / f"{result.model_name}_metrics.json").write_text(
        json.dumps(_serialize_baseline_metrics(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    confusion_matrix = pd.DataFrame(
        result.test_metrics.confusion_matrix,
        index=pd.Index(IMPACT_LABELS),
        columns=pd.Index(IMPACT_LABELS),
    )
    confusion_matrix.to_csv(output_dir / f"{result.model_name}_confusion_matrix.csv")


def log_baseline_to_mlflow(result: BaselineTrainingResult, *, artifact_dir: Path) -> None:
    experiment = _ensure_experiment(artifact_dir=artifact_dir)
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


def _ensure_experiment(*, artifact_dir: Path) -> Experiment:
    experiment = mlflow.get_experiment_by_name(MLFLOW_EXPERIMENT_NAME)
    if experiment is not None:
        return experiment

    experiment_id = mlflow.create_experiment(
        MLFLOW_EXPERIMENT_NAME,
        artifact_location=_build_artifact_store_path(artifact_dir=artifact_dir).as_uri(),
    )
    experiment = mlflow.get_experiment(experiment_id)
    if experiment is None:
        raise RuntimeError(f"MLflow experiment was not created: {MLFLOW_EXPERIMENT_NAME}")
    return experiment


def _build_artifact_store_path(*, artifact_dir: Path) -> Path:
    artifact_path = artifact_dir.resolve()
    return artifact_path.parent / f"{artifact_path.name}-mlflow-artifacts"


def _serialize_baseline_metrics(result: BaselineTrainingResult) -> dict[str, Any]:
    return {
        "model_name": result.model_name,
        "best_params": _to_json_value(result.best_params),
        "validation": _serialize_classification_metrics(result.validation_metrics),
        "test": _serialize_classification_metrics(result.test_metrics),
    }


def _serialize_classification_metrics(metrics: ClassificationMetrics) -> dict[str, float]:
    return {
        "accuracy": float(metrics.accuracy),
        "macro_precision": float(metrics.macro_precision),
        "macro_recall": float(metrics.macro_recall),
        "macro_f1": float(metrics.macro_f1),
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
