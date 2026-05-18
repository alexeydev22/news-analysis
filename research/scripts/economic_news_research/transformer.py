from dataclasses import dataclass
from tempfile import TemporaryDirectory
from typing import Any, Protocol

from economic_news_research.data import DatasetSplit
from economic_news_research.metrics import compute_classification_metrics
from economic_news_research.modeling import IMPACT_LABELS
from economic_news_research.results import ModelTrainingResult, measure_prediction_time

DEFAULT_TINY_TRANSFORMER_MODEL = "google/bert_uncased_L-2_H-128_A-2"


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
    tokenizer_name: str = "bert-base-uncased"
    epochs: int = 2
    batch_size: int = 16
    learning_rate: float = 2e-5
    max_length: int = 192
    seed: int = 42


def compute_class_weights(
    *,
    labels: list[str],
    label_to_id: dict[str, int],
) -> list[float]:
    total = len(labels)
    class_count = len(label_to_id)
    counts = {label: labels.count(label) for label in label_to_id}
    return [
        total / (class_count * max(counts[label], 1))
        for label, _ in sorted(label_to_id.items(), key=lambda item: item[1])
    ]


class WeightedTrainer:
    @staticmethod
    def build(*, class_weights: list[float], trainer_class: Any) -> type[Any]:
        import torch

        class _WeightedTrainer(trainer_class):
            def compute_loss(
                self,
                model: Any,
                inputs: dict[str, Any],
                return_outputs: bool = False,
                **kwargs: Any,
            ) -> Any:
                labels = inputs.pop("labels")
                outputs = model(**inputs)
                weights = torch.tensor(
                    class_weights,
                    dtype=torch.float,
                    device=labels.device,
                )
                loss_function = torch.nn.CrossEntropyLoss(weight=weights)
                loss = loss_function(outputs.logits, labels)
                return (loss, outputs) if return_outputs else loss

        return _WeightedTrainer


class HuggingFaceTinyTransformerTrainer:
    def __init__(self, config: TinyTransformerConfig | None = None) -> None:
        self.config = config or TinyTransformerConfig()
        self.best_params = {
            "model_name": self.config.model_name,
            "tokenizer_name": self.config.tokenizer_name,
            "epochs": self.config.epochs,
            "batch_size": self.config.batch_size,
            "learning_rate": self.config.learning_rate,
        }
        self._label_to_id = {label: index for index, label in enumerate(IMPACT_LABELS)}
        self._id_to_label = {index: label for label, index in self._label_to_id.items()}
        self._tokenizer: Any | None = None
        self._model: Any | None = None
        self._trainer: Any | None = None
        self._training_dir: TemporaryDirectory[str] | None = None

    def fit(
        self,
        train_texts: list[str],
        train_labels: list[str],
        validation_texts: list[str],
        validation_labels: list[str],
    ) -> None:
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            Trainer,
            TrainingArguments,
            set_seed,
        )

        set_seed(self.config.seed)
        tokenizer: Any = AutoTokenizer.from_pretrained(
            self.config.tokenizer_name,
            use_fast=False,
        )
        self._tokenizer = tokenizer
        self._model = AutoModelForSequenceClassification.from_pretrained(
            self.config.model_name,
            num_labels=len(IMPACT_LABELS),
            id2label=self._id_to_label,
            label2id=self._label_to_id,
        )
        class_weights = compute_class_weights(
            labels=train_labels,
            label_to_id=self._label_to_id,
        )
        trainer_class = WeightedTrainer.build(
            class_weights=class_weights,
            trainer_class=Trainer,
        )
        self._training_dir = TemporaryDirectory()
        training_args = TrainingArguments(
            output_dir=self._training_dir.name,
            num_train_epochs=self.config.epochs,
            per_device_train_batch_size=self.config.batch_size,
            per_device_eval_batch_size=self.config.batch_size,
            learning_rate=self.config.learning_rate,
            report_to=[],
            save_strategy="no",
            logging_strategy="no",
            eval_strategy="epoch",
        )
        self._trainer = trainer_class(
            model=self._model,
            args=training_args,
            train_dataset=_NewsTextDataset(
                encodings=tokenizer(
                    train_texts,
                    truncation=True,
                    padding=True,
                    max_length=self.config.max_length,
                ),
                labels=[self._label_to_id[label] for label in train_labels],
            ),
            eval_dataset=_NewsTextDataset(
                encodings=tokenizer(
                    validation_texts,
                    truncation=True,
                    padding=True,
                    max_length=self.config.max_length,
                ),
                labels=[self._label_to_id[label] for label in validation_labels],
            ),
        )
        self._trainer.train()

    def predict(self, texts: list[str]) -> list[str]:
        if self._model is None or self._tokenizer is None:
            raise RuntimeError("Tiny transformer trainer must be fitted before prediction")

        import torch

        device = next(self._model.parameters()).device
        self._model.eval()
        prediction_ids: list[int] = []
        batch_size = max(self.config.batch_size, 1)
        with torch.no_grad():
            for batch_start in range(0, len(texts), batch_size):
                batch_texts = texts[batch_start : batch_start + batch_size]
                encoded = self._tokenizer(
                    batch_texts,
                    truncation=True,
                    padding=True,
                    max_length=self.config.max_length,
                    return_tensors="pt",
                )
                encoded = {key: value.to(device) for key, value in encoded.items()}
                outputs = self._model(**encoded)
                prediction_ids.extend(outputs.logits.argmax(dim=-1).tolist())
        return [self._id_to_label[prediction_id] for prediction_id in prediction_ids]

    def __getstate__(self) -> dict[str, Any]:
        model = self._model
        if model is not None:
            model = model.to("cpu")
        return {
            "config": self.config,
            "best_params": self.best_params,
            "label_to_id": self._label_to_id,
            "id_to_label": self._id_to_label,
            "tokenizer": self._tokenizer,
            "model": model,
        }

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.config = state["config"]
        self.best_params = state["best_params"]
        self._label_to_id = state["label_to_id"]
        self._id_to_label = state["id_to_label"]
        self._tokenizer = state["tokenizer"]
        self._model = state["model"]
        self._trainer = None
        self._training_dir = None


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


@dataclass(frozen=True)
class _NewsTextDataset:
    encodings: dict[str, list[int]]
    labels: list[int]

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, index: int) -> dict[str, Any]:
        import torch

        item = {key: torch.tensor(values[index]) for key, values in self.encodings.items()}
        item["labels"] = torch.tensor(self.labels[index])
        return item
