from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split


class ImpactLabel(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


REQUIRED_COLUMNS = ["article_id", "text", "impact", "source", "published_at"]
FNSPID_COLUMNS = ["id", "title", "text", "source", "published_at"]
POSITIVE_TERMS = frozenset(
    {
        "approval",
        "approved",
        "beat",
        "beats",
        "bullish",
        "gain",
        "gains",
        "grew",
        "grow",
        "grows",
        "growth",
        "higher",
        "improve",
        "improves",
        "profit",
        "profits",
        "record",
        "rise",
        "rises",
        "rose",
        "strong buy",
        "surge",
        "upgraded",
        "upside",
    },
)
NEGATIVE_TERMS = frozenset(
    {
        "bankruptcy",
        "bearish",
        "cut",
        "decline",
        "declines",
        "downgrade",
        "downgraded",
        "drop",
        "drops",
        "fell",
        "fall",
        "falls",
        "lawsuit",
        "loss",
        "losses",
        "lower",
        "miss",
        "misses",
        "recession",
        "risk",
        "risks",
        "weak",
        "warning",
    },
)


class NewsDatasetError(ValueError):
    pass


@dataclass(frozen=True)
class DatasetSplit:
    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame


def load_news_dataset(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise NewsDatasetError(f"Dataset file does not exist: {path}")
    frame = pd.read_csv(path)
    return validate_news_dataset(frame)


def validate_news_dataset(frame: pd.DataFrame) -> pd.DataFrame:
    frame = adapt_news_dataset(frame)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing_columns:
        raise NewsDatasetError(f"Missing required columns: {missing_columns}")

    dataset = frame.loc[:, REQUIRED_COLUMNS].copy()
    if dataset["text"].isna().any():
        raise NewsDatasetError("text values must be non-empty")

    dataset["text"] = dataset["text"].astype(str).str.strip()
    dataset["impact"] = dataset["impact"].astype(str).str.strip().str.lower()
    dataset["source"] = dataset["source"].astype(str).str.strip()
    dataset["published_at"] = pd.to_datetime(dataset["published_at"], errors="coerce")

    unknown_labels = sorted(set(dataset["impact"]) - {label.value for label in ImpactLabel})
    if unknown_labels:
        raise NewsDatasetError(f"Unknown impact labels: {unknown_labels}")

    if dataset["article_id"].isna().any() or dataset["article_id"].duplicated().any():
        raise NewsDatasetError("article_id values must be present and unique")

    if dataset["text"].eq("").any():
        raise NewsDatasetError("text values must be non-empty")

    if dataset["published_at"].isna().any():
        raise NewsDatasetError("published_at values must be parseable dates")

    return dataset


def adapt_news_dataset(frame: pd.DataFrame) -> pd.DataFrame:
    """Adapts supported raw news formats to the supervised ML schema."""
    if all(column in frame.columns for column in REQUIRED_COLUMNS):
        return frame
    if all(column in frame.columns for column in FNSPID_COLUMNS):
        dataset = frame.copy()
        dataset["article_id"] = dataset["id"]
        dataset["impact"] = [
            infer_weak_impact_label(title=title, text=text)
            for title, text in zip(dataset["title"], dataset["text"], strict=True)
        ]
        return dataset
    return frame


def infer_weak_impact_label(*, title: object, text: object) -> str:
    content = f"{title or ''} {text or ''}".lower()
    positive_score = sum(term in content for term in POSITIVE_TERMS)
    negative_score = sum(term in content for term in NEGATIVE_TERMS)
    if positive_score > negative_score:
        return ImpactLabel.POSITIVE.value
    if negative_score > positive_score:
        return ImpactLabel.NEGATIVE.value
    return ImpactLabel.NEUTRAL.value


def split_news_dataset(
    dataset: pd.DataFrame,
    *,
    random_state: int,
    train_size: float = 0.6,
    validation_size: float = 0.2,
) -> DatasetSplit:
    train, temporary = train_test_split(
        dataset,
        train_size=train_size,
        random_state=random_state,
        shuffle=True,
        stratify=dataset["impact"] if dataset["impact"].value_counts().min() >= 2 else None,
    )
    validation_fraction = validation_size / (1 - train_size)
    validation, test = train_test_split(
        temporary,
        train_size=validation_fraction,
        random_state=random_state,
        shuffle=True,
        stratify=temporary["impact"] if temporary["impact"].value_counts().min() >= 2 else None,
    )
    return DatasetSplit(
        train=train.reset_index(drop=True),
        validation=validation.reset_index(drop=True),
        test=test.reset_index(drop=True),
    )


def sample_news_dataset(
    dataset: pd.DataFrame,
    *,
    max_rows: int | None,
    random_state: int,
) -> pd.DataFrame:
    if max_rows is None or max_rows <= 0 or len(dataset) <= max_rows:
        return dataset.reset_index(drop=True)

    stratify = dataset["impact"] if dataset["impact"].value_counts().min() >= 2 else None
    sampled, _ = train_test_split(
        dataset,
        train_size=max_rows,
        random_state=random_state,
        shuffle=True,
        stratify=stratify,
    )
    return sampled.reset_index(drop=True)
