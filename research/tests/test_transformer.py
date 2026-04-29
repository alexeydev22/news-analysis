from pathlib import Path

from economic_news_research.data import load_news_dataset, split_news_dataset
from economic_news_research.transformer import (
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
