from pathlib import Path

from economic_news_research.data import load_news_dataset, split_news_dataset
from economic_news_research.modeling import (
    BaselineTrainingResult,
    build_baseline_pipeline,
    train_baseline_model,
)

FIXTURE = Path(__file__).parent / "fixtures" / "news_impact_sample.csv"


def test_build_baseline_pipeline_predicts_labels() -> None:
    pipeline = build_baseline_pipeline(max_features=100, c_value=1.0, ngram_range=(1, 1))
    dataset = load_news_dataset(FIXTURE)

    pipeline.fit(dataset["text"], dataset["impact"])
    predictions = pipeline.predict(dataset["text"])

    assert len(predictions) == len(dataset)
    assert set(predictions).issubset({"positive", "neutral", "negative"})


def test_train_baseline_model_returns_metrics() -> None:
    dataset = load_news_dataset(FIXTURE)
    split = split_news_dataset(dataset, random_state=42)

    result = train_baseline_model(split, random_state=42)

    assert isinstance(result, BaselineTrainingResult)
    assert result.model_name == "tfidf-logreg"
    assert result.validation_metrics.confusion_matrix.shape == (3, 3)
    assert result.best_params["classifier__C"] in {0.1, 1.0, 10.0}
