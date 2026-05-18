import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from economic_news_research.data import load_news_dataset
from economic_news_research.modeling import IMPACT_LABELS

TOP_FEATURE_COUNT = 8


def build_model_report(
    *,
    dataset_path: Path,
    comparison_path: Path,
    model_dirs: list[Path],
    training_limits: dict[str, int | None] | None = None,
) -> dict[str, Any]:
    """Собирает JSON-совместимый отчет по обученным ML-моделям."""
    dataset = load_news_dataset(dataset_path)
    comparison = pd.read_csv(comparison_path)
    models = [
        _build_model_section(row=row, model_dirs=model_dirs)
        for row in comparison.to_dict(orient="records")
    ]
    return {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "dataset": {
            "path": str(dataset_path),
            "row_count": int(len(dataset)),
            "class_distribution": _class_distribution(dataset),
            "label_quality": _label_quality(dataset),
        },
        "training": training_limits or {},
        "models": models,
        "best_model": _best_model(models),
        "top_features": _top_features(model_dirs=model_dirs),
    }


def save_model_report(report: dict[str, Any], *, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def _class_distribution(dataset: pd.DataFrame) -> dict[str, int]:
    counts = dataset["impact"].value_counts().to_dict()
    return {label: int(counts.get(label, 0)) for label in IMPACT_LABELS}


def _label_quality(dataset: pd.DataFrame) -> dict[str, Any]:
    if "weak_label_margin" not in dataset.columns:
        return {"label_source": "provided"}

    margins = pd.to_numeric(dataset["weak_label_margin"], errors="coerce")
    return {
        "label_source": "weak_rules",
        "low_margin_count": int((margins <= 1).sum()),
        "average_margin": float(margins.mean()),
    }


def _build_model_section(row: dict[str, Any], model_dirs: list[Path]) -> dict[str, Any]:
    model_name = str(row["model_name"])
    metrics = _read_metrics_json(model_name=model_name, model_dirs=model_dirs)
    return {
        "model_name": model_name,
        "validation_accuracy": _float_or_none(row.get("validation_accuracy")),
        "validation_macro_f1": _float_or_none(row.get("validation_macro_f1")),
        "test_accuracy": _float_or_none(row.get("test_accuracy")),
        "test_macro_f1": _float_or_none(row.get("test_macro_f1")),
        "inference_seconds_per_sample": _float_or_none(
            row.get("inference_seconds_per_sample"),
        ),
        "confusion_matrix": _read_confusion_matrix(
            model_name=model_name,
            model_dirs=model_dirs,
        ),
        "per_class": metrics.get("test_per_class", {}) if metrics else {},
    }


def _float_or_none(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _read_confusion_matrix(
    *,
    model_name: str,
    model_dirs: list[Path],
) -> dict[str, Any] | None:
    matrix_path = _find_existing_file(
        model_dirs=model_dirs,
        filename=f"{model_name}_confusion_matrix.csv",
    )
    if matrix_path is None:
        return None
    matrix = pd.read_csv(matrix_path, index_col=0)
    labels = [str(label) for label in matrix.index.tolist()]
    return {
        "labels": labels,
        "matrix": [
            [int(value) for value in row]
            for row in matrix.loc[:, labels].to_numpy().tolist()
        ],
    }


def _read_metrics_json(*, model_name: str, model_dirs: list[Path]) -> dict[str, Any] | None:
    metrics_path = _find_existing_file(
        model_dirs=model_dirs,
        filename=f"{model_name}_metrics.json",
    )
    if metrics_path is None:
        return None
    return json.loads(metrics_path.read_text(encoding="utf-8"))


def _best_model(models: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not models:
        return None
    return max(models, key=lambda model: model.get("test_macro_f1") or 0.0)


def _top_features(*, model_dirs: list[Path]) -> dict[str, dict[str, list[str]]]:
    artifact_path = _find_existing_file(
        model_dirs=model_dirs,
        filename="tfidf-logreg.joblib",
    )
    if artifact_path is None:
        return {}

    estimator = joblib.load(artifact_path)
    vectorizer = estimator.named_steps["tfidf"]
    classifier = estimator.named_steps["classifier"]
    feature_names = vectorizer.get_feature_names_out()
    features_by_class: dict[str, list[str]] = {}
    for class_index, class_label in enumerate(classifier.classes_):
        coefficients = classifier.coef_[class_index]
        top_indexes = coefficients.argsort()[-TOP_FEATURE_COUNT:][::-1]
        features_by_class[str(class_label)] = [
            str(feature_names[index])
            for index in top_indexes
        ]
    return {"tfidf-logreg": features_by_class}


def _find_existing_file(*, model_dirs: list[Path], filename: str) -> Path | None:
    for model_dir in model_dirs:
        candidate = model_dir / filename
        if candidate.exists():
            return candidate
    return None
