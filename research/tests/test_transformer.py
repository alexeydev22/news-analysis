from collections.abc import Iterator
from pathlib import Path

from economic_news_research.data import load_news_dataset, split_news_dataset
from economic_news_research.transformer import (
    HuggingFaceTinyTransformerTrainer,
    TransformerTrainingResult,
    train_tiny_transformer_classifier,
)

FIXTURE = Path(__file__).parent / "fixtures" / "news_impact_sample.csv"


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
        predictions: list[str] = []
        for text in texts:
            lowered = text.lower()
            if "rise" in lowered or "gain" in lowered or "strong" in lowered:
                predictions.append("positive")
            elif "fall" in lowered or "decline" in lowered or "drops" in lowered:
                predictions.append("negative")
            else:
                predictions.append("neutral")
        return predictions


class RecordingTinyTransformerTrainer(FakeTinyTransformerTrainer):
    def fit(
        self,
        train_texts: list[str],
        train_labels: list[str],
        validation_texts: list[str],
        validation_labels: list[str],
    ) -> None:
        super().fit(
            train_texts=train_texts,
            train_labels=train_labels,
            validation_texts=validation_texts,
            validation_labels=validation_labels,
        )
        self.fit_call = {
            "train_texts": train_texts,
            "train_labels": train_labels,
            "validation_texts": validation_texts,
            "validation_labels": validation_labels,
        }


class FakeTensor:
    def __init__(self) -> None:
        self.received_device: str | None = None

    def to(self, device: str) -> "FakeTensor":
        self.received_device = device
        return self


class FakeParameter:
    device = "fake-accelerator"


class FakeLogits:
    def argmax(self, *, dim: int) -> "FakeLogits":
        assert dim == -1
        return self

    def tolist(self) -> list[int]:
        return [0]


class FakeModelOutput:
    logits = FakeLogits()


class DeviceCheckingModel:
    def __init__(self, input_ids: FakeTensor) -> None:
        self.input_ids = input_ids
        self.evaluated = False

    def parameters(self) -> Iterator[FakeParameter]:
        return iter([FakeParameter()])

    def eval(self) -> None:
        self.evaluated = True

    def __call__(self, **kwargs: FakeTensor) -> FakeModelOutput:
        assert kwargs["input_ids"].received_device == FakeParameter.device
        assert self.evaluated
        return FakeModelOutput()


class FakeTokenizer:
    def __init__(self, input_ids: FakeTensor) -> None:
        self.input_ids = input_ids

    def __call__(self, texts: list[str], **kwargs: object) -> dict[str, FakeTensor]:
        assert texts == ["Markets rise"]
        assert kwargs["return_tensors"] == "pt"
        return {"input_ids": self.input_ids}


def test_train_tiny_transformer_classifier_returns_metrics_without_downloads() -> None:
    dataset = load_news_dataset(FIXTURE)
    split = split_news_dataset(dataset, random_state=42)

    result = train_tiny_transformer_classifier(
        split,
        trainer=FakeTinyTransformerTrainer(),
        random_state=42,
    )

    assert isinstance(result, TransformerTrainingResult)
    assert result.model_name == "tiny-transformer-classifier"
    assert result.validation_metrics.confusion_matrix.shape == (3, 3)
    assert result.test_metrics.confusion_matrix.shape == (3, 3)
    assert result.best_params["model_name"] == "fake-tiny-transformer"


def test_train_tiny_transformer_classifier_passes_training_data_to_trainer() -> None:
    dataset = load_news_dataset(FIXTURE)
    split = split_news_dataset(dataset, random_state=42)
    trainer = RecordingTinyTransformerTrainer()

    train_tiny_transformer_classifier(
        split,
        trainer=trainer,
        random_state=42,
    )

    assert trainer.fit_call["train_texts"] == split.train["text"].tolist()
    assert trainer.fit_call["train_labels"] == split.train["impact"].tolist()
    assert trainer.fit_call["validation_texts"] == split.validation["text"].tolist()
    assert trainer.fit_call["validation_labels"] == split.validation["impact"].tolist()


def test_huggingface_tiny_transformer_predict_moves_batch_to_model_device() -> None:
    input_ids = FakeTensor()
    trainer = HuggingFaceTinyTransformerTrainer()
    trainer._tokenizer = FakeTokenizer(input_ids)
    trainer._model = DeviceCheckingModel(input_ids)

    predictions = trainer.predict(["Markets rise"])

    assert predictions == ["negative"]
    assert input_ids.received_device == FakeParameter.device
