from collections.abc import Callable, Sequence
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from economic_news_research.metrics import ClassificationMetrics


@dataclass(frozen=True)
class ModelTrainingResult:
    model_name: str
    best_params: dict[str, Any]
    validation_metrics: ClassificationMetrics
    test_metrics: ClassificationMetrics
    estimator: Any
    inference_seconds_per_sample: float


def measure_prediction_time(
    *,
    predictor: Callable[[Sequence[str]], Sequence[str]],
    values: Sequence[str],
) -> tuple[list[str], float]:
    if not values:
        return [], 0.0

    started_at = perf_counter()
    predictions = list(predictor(values))
    elapsed_seconds = perf_counter() - started_at

    return predictions, elapsed_seconds / len(values)
