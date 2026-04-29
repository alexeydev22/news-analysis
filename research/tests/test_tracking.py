from pathlib import Path

import numpy as np
import pandas as pd

from economic_news_research.data import load_news_dataset, split_news_dataset
from economic_news_research.embedding import train_embedding_classifier
from economic_news_research.modeling import train_baseline_model
from economic_news_research.tracking import save_model_artifacts, write_model_comparison

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


def test_write_model_comparison_combines_multiple_results(tmp_path: Path) -> None:
    dataset = load_news_dataset(FIXTURE)
    split = split_news_dataset(dataset, random_state=42)
    baseline = train_baseline_model(split, random_state=42)
    embedding = train_embedding_classifier(split, embedder=FakeEmbedder(), random_state=42)

    comparison_path = write_model_comparison(
        [baseline, embedding],
        output_path=tmp_path / "model_comparison.csv",
    )

    comparison = pd.read_csv(comparison_path)
    assert comparison["model_name"].tolist() == ["tfidf-logreg", "embedding-logreg"]
    assert "inference_seconds_per_sample" in comparison.columns


def test_save_model_artifacts_writes_model_named_files(tmp_path: Path) -> None:
    dataset = load_news_dataset(FIXTURE)
    split = split_news_dataset(dataset, random_state=42)
    result = train_baseline_model(split, random_state=42)

    save_model_artifacts(result, output_dir=tmp_path)

    assert (tmp_path / "tfidf-logreg.joblib").exists()
    assert (tmp_path / "tfidf-logreg_metrics.json").exists()
    assert (tmp_path / "tfidf-logreg_confusion_matrix.csv").exists()
    assert (tmp_path / "model_comparison.csv").exists()
