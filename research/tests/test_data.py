from pathlib import Path

import pandas as pd
import pytest

from economic_news_research.data import (
    ImpactLabel,
    NewsDatasetError,
    load_news_dataset,
    sample_news_dataset,
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


def test_validate_news_dataset_adapts_fnspid_format_with_weak_labels() -> None:
    frame = pd.DataFrame(
        {
            "id": ["news-positive", "news-negative", "news-neutral"],
            "title": [
                "GDP grows",
                "Shares drop after warning",
                "Central bank keeps rate unchanged",
            ],
            "text": [
                "Company revenue rises and profit beats expectations.",
                "The stock fell after a weak outlook and lower demand.",
                "The regulator published a scheduled market update.",
            ],
            "source": ["FNSPID", "FNSPID", "FNSPID"],
            "published_at": [
                "2024-01-01T00:00:00Z",
                "2024-01-02T00:00:00Z",
                "2024-01-03T00:00:00Z",
            ],
        },
    )

    dataset = validate_news_dataset(frame)

    assert list(dataset.columns) == [
        "article_id",
        "text",
        "impact",
        "source",
        "published_at",
        "label_source",
        "weak_label_margin",
        "weak_positive_score",
        "weak_negative_score",
    ]
    assert dataset["article_id"].tolist() == ["news-positive", "news-negative", "news-neutral"]
    assert dataset["text"].tolist() == [
        "GDP grows. Company revenue rises and profit beats expectations.",
        "Shares drop after warning. The stock fell after a weak outlook and lower demand.",
        "Central bank keeps rate unchanged. The regulator published a scheduled market update.",
    ]
    assert dataset["impact"].tolist() == [
        ImpactLabel.POSITIVE,
        ImpactLabel.NEGATIVE,
        ImpactLabel.NEUTRAL,
    ]
    assert dataset["label_source"].tolist() == ["weak_rules", "weak_rules", "weak_rules"]
    assert dataset["weak_label_margin"].tolist() == [4, 5, 0]
    assert dataset["weak_positive_score"].tolist() == [4, 0, 0]
    assert dataset["weak_negative_score"].tolist() == [0, 5, 0]


def test_validate_news_dataset_infers_fnspid_weak_metadata_from_normalized_text() -> None:
    frame = pd.DataFrame(
        {
            "id": ["news-positive"],
            "title": ["Revenue rises"],
            "text": [
                "Fintel reports that on December 13, 2023, revenue   rises. "
                "See our leaderboard of companies with the largest price target upside. "
                "Read more at https://example.com/page"
            ],
            "source": ["FNSPID"],
            "published_at": ["2024-01-01T00:00:00Z"],
        },
    )

    dataset = validate_news_dataset(frame)

    assert dataset["text"].tolist() == ["Revenue rises. revenue rises. Read more at"]
    assert dataset["impact"].tolist() == [ImpactLabel.NEUTRAL]
    assert dataset["label_source"].tolist() == ["weak_rules"]
    assert dataset["weak_label_margin"].tolist() == [1]
    assert dataset["weak_positive_score"].tolist() == [1]
    assert dataset["weak_negative_score"].tolist() == [0]


def test_validate_news_dataset_preserves_optional_weak_label_metadata() -> None:
    frame = pd.DataFrame(
        {
            "article_id": ["news-1"],
            "text": ["Market update"],
            "impact": ["neutral"],
            "source": ["fixture"],
            "published_at": ["2024-01-01T00:00:00Z"],
            "label_source": ["weak_rules"],
            "weak_label_margin": [1],
            "weak_positive_score": [2],
            "weak_negative_score": [1],
            "ignored": ["value"],
        },
    )

    dataset = validate_news_dataset(frame)

    assert list(dataset.columns) == [
        "article_id",
        "text",
        "impact",
        "source",
        "published_at",
        "label_source",
        "weak_label_margin",
        "weak_positive_score",
        "weak_negative_score",
    ]
    assert dataset["label_source"].tolist() == ["weak_rules"]
    assert dataset["weak_label_margin"].tolist() == [1]
    assert dataset["weak_positive_score"].tolist() == [2]
    assert dataset["weak_negative_score"].tolist() == [1]


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


def test_sample_news_dataset_is_deterministic_and_stratified() -> None:
    dataset = pd.DataFrame(
        {
            "article_id": [f"positive-{index}" for index in range(10)]
            + [f"negative-{index}" for index in range(10)]
            + [f"neutral-{index}" for index in range(10)],
            "text": [f"text {index}" for index in range(30)],
            "impact": ["positive"] * 10 + ["negative"] * 10 + ["neutral"] * 10,
            "source": ["fixture"] * 30,
            "published_at": ["2024-01-01"] * 30,
        },
    )

    first = sample_news_dataset(dataset, max_rows=9, random_state=42)
    second = sample_news_dataset(dataset, max_rows=9, random_state=42)

    assert first["article_id"].tolist() == second["article_id"].tolist()
    assert first["impact"].value_counts().to_dict() == {
        "negative": 3,
        "neutral": 3,
        "positive": 3,
    }
