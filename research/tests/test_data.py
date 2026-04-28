from pathlib import Path

import pandas as pd
import pytest

from economic_news_research.data import (
    ImpactLabel,
    NewsDatasetError,
    load_news_dataset,
    split_news_dataset,
    validate_news_dataset,
)

FIXTURE = Path(__file__).parent / "fixtures" / "news_impact_sample.csv"


def test_load_news_dataset_returns_valid_frame() -> None:
    dataset = load_news_dataset(FIXTURE)

    assert list(dataset.columns) == ["article_id", "text", "impact", "source", "published_at"]
    assert set(dataset["impact"]) == {
        ImpactLabel.POSITIVE,
        ImpactLabel.NEUTRAL,
        ImpactLabel.NEGATIVE,
    }
    assert len(dataset) == 9


def test_validate_news_dataset_rejects_missing_columns() -> None:
    frame = pd.DataFrame({"text": ["Market rises"], "impact": ["positive"]})

    with pytest.raises(NewsDatasetError, match="Missing required columns"):
        validate_news_dataset(frame)


def test_validate_news_dataset_rejects_unknown_label() -> None:
    frame = pd.read_csv(FIXTURE)
    frame.loc[0, "impact"] = "mixed"

    with pytest.raises(NewsDatasetError, match="Unknown impact labels"):
        validate_news_dataset(frame)


def test_validate_news_dataset_rejects_missing_text() -> None:
    frame = pd.read_csv(FIXTURE)
    frame.loc[0, "text"] = None

    with pytest.raises(NewsDatasetError, match="text values must be non-empty"):
        validate_news_dataset(frame)


def test_split_news_dataset_is_deterministic() -> None:
    dataset = load_news_dataset(FIXTURE)

    first = split_news_dataset(dataset, random_state=42)
    second = split_news_dataset(dataset, random_state=42)

    assert first.train["article_id"].tolist() == second.train["article_id"].tolist()
    assert first.validation["article_id"].tolist() == second.validation["article_id"].tolist()
    assert first.test["article_id"].tolist() == second.test["article_id"].tolist()
    assert len(first.train) == 5
    assert len(first.validation) == 2
    assert len(first.test) == 2
