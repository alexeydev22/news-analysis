from dataclasses import dataclass

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support


@dataclass(frozen=True)
class ClassificationMetrics:
    accuracy: float
    macro_precision: float
    macro_recall: float
    macro_f1: float
    confusion_matrix: np.ndarray
    per_class: dict[str, dict[str, float]]


def compute_classification_metrics(
    *,
    y_true: list[str],
    y_pred: list[str],
    labels: list[str],
) -> ClassificationMetrics:
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=labels,
        average="macro",
        zero_division=0,
    )
    per_class_precision, per_class_recall, per_class_f1, _ = (
        precision_recall_fscore_support(
            y_true,
            y_pred,
            labels=labels,
            average=None,
            zero_division=0,
        )
    )
    per_class = {
        label: {
            "precision": float(per_class_precision[index]),
            "recall": float(per_class_recall[index]),
            "f1": float(per_class_f1[index]),
        }
        for index, label in enumerate(labels)
    }
    return ClassificationMetrics(
        accuracy=float(accuracy_score(y_true, y_pred)),
        macro_precision=float(precision),
        macro_recall=float(recall),
        macro_f1=float(f1),
        confusion_matrix=confusion_matrix(y_true, y_pred, labels=labels),
        per_class=per_class,
    )
