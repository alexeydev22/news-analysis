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
    return ClassificationMetrics(
        accuracy=accuracy_score(y_true, y_pred),
        macro_precision=precision,
        macro_recall=recall,
        macro_f1=f1,
        confusion_matrix=confusion_matrix(y_true, y_pred, labels=labels),
    )
