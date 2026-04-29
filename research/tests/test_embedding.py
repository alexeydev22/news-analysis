from pathlib import Path

import joblib
import numpy as np

from economic_news_research.data import load_news_dataset, split_news_dataset
from economic_news_research.embedding import (
    EmbeddingTrainingResult,
    train_embedding_classifier,
)

FIXTURE = Path(__file__).parent / "fixtures" / "news_impact_sample.csv"


class FakeEmbedder:
    def encode(self, texts: list[str]) -> np.ndarray:
        rows: list[list[float]] = []
        for text in texts:
            lowered = text.lower()
            rows.append(
                [
                    float("rise" in lowered or "gain" in lowered or "strong" in lowered),
                    float("fall" in lowered or "decline" in lowered or "drops" in lowered),
                    float("stable" in lowered or "unchanged" in lowered or "wait" in lowered),
                ]
            )
        return np.array(rows, dtype=float)


def test_train_embedding_classifier_returns_metrics() -> None:
    dataset = load_news_dataset(FIXTURE)
    split = split_news_dataset(dataset, random_state=42)

    result = train_embedding_classifier(
        split,
        embedder=FakeEmbedder(),
        random_state=42,
    )

    assert isinstance(result, EmbeddingTrainingResult)
    assert result.model_name == "embedding-logreg"
    assert result.validation_metrics.confusion_matrix.shape == (3, 3)
    assert result.test_metrics.confusion_matrix.shape == (3, 3)
    assert result.inference_seconds_per_sample >= 0


def test_embedding_classifier_artifact_predicts_raw_text_after_load(tmp_path: Path) -> None:
    dataset = load_news_dataset(FIXTURE)
    split = split_news_dataset(dataset, random_state=42)
    result = train_embedding_classifier(
        split,
        embedder=FakeEmbedder(),
        random_state=42,
    )
    model_path = tmp_path / "embedding-logreg.joblib"

    joblib.dump(result.estimator, model_path)
    loaded_estimator = joblib.load(model_path)

    predictions = loaded_estimator.predict(
        ["Technology shares rise after strong earnings forecast"],
    )
    assert predictions == ["positive"]
