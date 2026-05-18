import weakref
from collections.abc import Iterator
from pathlib import Path

import joblib

from economic_news_research import transformer
from economic_news_research.data import load_news_dataset, split_news_dataset
from economic_news_research.transformer import (
    HuggingFaceTinyTransformerTrainer,
    TinyTransformerConfig,
    TransformerTrainingResult,
    WeightedTrainer,
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
        self.to_device_calls: list[str] = []

    def parameters(self) -> Iterator[FakeParameter]:
        return iter([FakeParameter()])

    def eval(self) -> None:
        self.evaluated = True

    def to(self, device: str) -> "DeviceCheckingModel":
        self.to_device_calls.append(device)
        return self

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


class BatchFakeTensor(FakeTensor):
    def __init__(self, length: int) -> None:
        super().__init__()
        self.length = length


class BatchFakeLogits:
    def __init__(self, length: int) -> None:
        self.length = length

    def argmax(self, *, dim: int) -> "BatchFakeLogits":
        assert dim == -1
        return self

    def tolist(self) -> list[int]:
        return [0] * self.length


class BatchFakeModelOutput:
    def __init__(self, length: int) -> None:
        self.logits = BatchFakeLogits(length)


class BatchDeviceCheckingModel:
    def __init__(self) -> None:
        self.evaluated = False

    def parameters(self) -> Iterator[FakeParameter]:
        return iter([FakeParameter()])

    def eval(self) -> None:
        self.evaluated = True

    def __call__(self, **kwargs: BatchFakeTensor) -> BatchFakeModelOutput:
        input_ids = kwargs["input_ids"]
        assert input_ids.received_device == FakeParameter.device
        assert self.evaluated
        return BatchFakeModelOutput(input_ids.length)


class RecordingBatchTokenizer:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self, texts: list[str], **kwargs: object) -> dict[str, BatchFakeTensor]:
        self.calls.append(texts)
        assert kwargs["return_tensors"] == "pt"
        return {"input_ids": BatchFakeTensor(len(texts))}


class WeakRefTarget:
    pass


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


def test_tiny_transformer_config_uses_english_default_model() -> None:
    config = TinyTransformerConfig()

    assert config.model_name == "google/bert_uncased_L-2_H-128_A-2"
    assert config.tokenizer_name == "bert-base-uncased"
    assert config.epochs == 2
    assert config.batch_size == 16
    assert config.max_length == 192


def test_compute_class_weights_gives_larger_weight_to_minor_classes() -> None:
    weights = transformer.compute_class_weights(
        labels=["positive"] * 8 + ["neutral"] * 2 + ["negative"],
        label_to_id={"negative": 0, "neutral": 1, "positive": 2},
    )

    assert weights[0] > weights[1]
    assert weights[1] > weights[2]


def test_weighted_trainer_uses_class_weights_for_cross_entropy() -> None:
    import torch

    class BaseTrainer:
        pass

    class Output:
        logits = torch.tensor([[2.0, 0.0], [0.0, 2.0]])

    class Model:
        def __call__(self, **kwargs: object) -> Output:
            assert torch.equal(kwargs["input_ids"], torch.tensor([1, 2]))
            return Output()

    trainer_class = WeightedTrainer.build(
        class_weights=[1.0, 3.0],
        trainer_class=BaseTrainer,
    )
    labels = torch.tensor([0, 1])

    loss = trainer_class().compute_loss(
        Model(),
        {"input_ids": torch.tensor([1, 2]), "labels": labels},
    )

    expected_loss = torch.nn.CrossEntropyLoss(weight=torch.tensor([1.0, 3.0]))(
        Output.logits,
        labels,
    )
    assert torch.equal(loss, expected_loss)


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


def test_huggingface_tiny_transformer_predict_uses_configured_batches() -> None:
    tokenizer = RecordingBatchTokenizer()
    trainer = HuggingFaceTinyTransformerTrainer(TinyTransformerConfig(batch_size=2))
    trainer._tokenizer = tokenizer
    trainer._model = BatchDeviceCheckingModel()

    predictions = trainer.predict(["one", "two", "three", "four", "five"])

    assert predictions == ["negative"] * 5
    assert tokenizer.calls == [["one", "two"], ["three", "four"], ["five"]]


def test_huggingface_tiny_transformer_joblib_state_excludes_trainer(
    tmp_path: Path,
) -> None:
    input_ids = FakeTensor()
    target = WeakRefTarget()
    artifact_path = tmp_path / "transformer.joblib"
    trainer = HuggingFaceTinyTransformerTrainer()
    trainer._tokenizer = FakeTokenizer(input_ids)
    trainer._model = DeviceCheckingModel(input_ids)
    trainer._trainer = weakref.ref(target)

    joblib.dump(trainer, artifact_path)

    loaded = joblib.load(artifact_path)
    assert trainer._model.to_device_calls == ["cpu"]
    assert loaded._trainer is None
    assert loaded.predict(["Markets rise"]) == ["negative"]
