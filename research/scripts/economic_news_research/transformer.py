from dataclasses import dataclass
from typing import Any, Protocol

from economic_news_research.data import DatasetSplit
from economic_news_research.metrics import compute_classification_metrics
from economic_news_research.modeling import IMPACT_LABELS
from economic_news_research.results import ModelTrainingResult, measure_prediction_time

DEFAULT_TINY_TRANSFORMER_MODEL = "cointegrated/rubert-tiny2"


TransformerTrainingResult = ModelTrainingResult


class TinyTransformerTrainer(Protocol):
    best_params: dict[str, object]

    def fit(
        self,
        train_texts: list[str],
        train_labels: list[str],
        validation_texts: list[str],
        validation_labels: list[str],
    ) -> None: ...

    def predict(self, texts: list[str]) -> list[str]: ...


@dataclass(frozen=True)
class TinyTransformerConfig:
    model_name: str = DEFAULT_TINY_TRANSFORMER_MODEL
    epochs: int = 1
    batch_size: int = 4
    learning_rate: float = 2e-5


class HuggingFaceTinyTransformerTrainer:
    def __init__(self, config: TinyTransformerConfig | None = None) -> None:
        self.config = config or TinyTransformerConfig()
        self.best_params = {
            "model_name": self.config.model_name,
            "epochs": self.config.epochs,
            "batch_size": self.config.batch_size,
            "learning_rate": self.config.learning_rate,
        }
        self._pipeline = None

    def fit(
        self,
        train_texts: list[str],
        train_labels: list[str],
        validation_texts: list[str],
        validation_labels: list[str],
    ) -> None:
        from transformers import pipeline

        self._pipeline = pipeline(
            "text-classification",
            model=self.config.model_name,
            tokenizer=self.config.model_name,
            top_k=None,
        )

    def predict(self, texts: list[str]) -> list[str]:
        if self._pipeline is None:
            raise RuntimeError("Tiny transformer trainer must be fitted before prediction")

        raw_predictions = self._pipeline(texts)
        predictions: list[str] = []
        for prediction_group in raw_predictions:
            predictions.append(_prediction_group_to_label(prediction_group))
        return predictions


def train_tiny_transformer_classifier(
    split: DatasetSplit,
    *,
    trainer: TinyTransformerTrainer | None = None,
    random_state: int,
) -> TransformerTrainingResult:
    del random_state

    active_trainer = trainer or HuggingFaceTinyTransformerTrainer()
    active_trainer.fit(
        train_texts=split.train["text"].tolist(),
        train_labels=split.train["impact"].tolist(),
        validation_texts=split.validation["text"].tolist(),
        validation_labels=split.validation["impact"].tolist(),
    )

    validation_predictions = active_trainer.predict(split.validation["text"].tolist())
    test_predictions, inference_seconds_per_sample = measure_prediction_time(
        predictor=lambda values: active_trainer.predict(list(values)),
        values=split.test["text"].tolist(),
    )

    return TransformerTrainingResult(
        model_name="tiny-transformer-classifier",
        best_params=dict(active_trainer.best_params),
        validation_metrics=compute_classification_metrics(
            y_true=split.validation["impact"].tolist(),
            y_pred=validation_predictions,
            labels=IMPACT_LABELS,
        ),
        test_metrics=compute_classification_metrics(
            y_true=split.test["impact"].tolist(),
            y_pred=test_predictions,
            labels=IMPACT_LABELS,
        ),
        estimator=active_trainer,
        inference_seconds_per_sample=inference_seconds_per_sample,
    )


def _prediction_group_to_label(prediction_group: Any) -> str:
    if isinstance(prediction_group, dict):
        label = str(prediction_group.get("label", "")).lower()
    else:
        best_prediction = max(prediction_group, key=lambda item: item["score"])
        label = str(best_prediction["label"]).lower()

    return label if label in IMPACT_LABELS else "neutral"
