from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from economic_news_research.text_normalization import normalize_news_text
from economic_news_research.weak_labeling import ImpactLabel, infer_weak_impact

REQUIRED_COLUMNS = ["article_id", "text", "impact", "source", "published_at"]
FNSPID_COLUMNS = ["id", "title", "text", "source", "published_at"]
OPTIONAL_COLUMNS = [
    "label_source",
    "weak_label_margin",
    "weak_positive_score",
    "weak_negative_score",
]


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

    selected_columns = REQUIRED_COLUMNS + [
        column for column in OPTIONAL_COLUMNS if column in frame.columns
    ]
    dataset = frame.loc[:, selected_columns].copy()
    if dataset["text"].isna().any():
        raise NewsDatasetError("text values must be non-empty")

    dataset["text"] = [normalize_news_text(value) for value in dataset["text"]]
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
        dataset["text"] = [
            normalize_news_text(f"{title}. {text}")
            for title, text in zip(dataset["title"], dataset["text"], strict=True)
        ]
        weak_labels = [
            infer_weak_impact(title="", text=text)
            for text in dataset["text"]
        ]
        dataset["impact"] = [label.label for label in weak_labels]
        dataset["label_source"] = "weak_rules"
        dataset["weak_label_margin"] = [label.margin for label in weak_labels]
        dataset["weak_positive_score"] = [label.positive_score for label in weak_labels]
        dataset["weak_negative_score"] = [label.negative_score for label in weak_labels]
        return dataset
    return frame


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
