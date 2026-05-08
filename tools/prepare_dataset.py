from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any

import pandas as pd

APP_COLUMNS = ["id", "title", "text", "source", "published_at"]
TRAIN_COLUMNS = ["article_id", "text", "impact", "source", "published_at"]
LABEL_ALIASES = {
    "positive": "positive",
    "pos": "positive",
    "1": "positive",
    "neutral": "neutral",
    "neu": "neutral",
    "0": "neutral",
    "negative": "negative",
    "neg": "negative",
    "-1": "negative",
}


def stable_id(*parts: str) -> str:
    """Возвращает короткий стабильный идентификатор для набора строк."""
    digest = hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest()
    return digest[:16]


def normalize_impact(
    value: Any,
    positive_threshold: float,
    negative_threshold: float,
) -> str:
    """Преобразует текстовую метку или числовой score в класс влияния.

    Args:
        value: Значение внешней метки или числового score.
        positive_threshold: Порог, начиная с которого score считается positive.
        negative_threshold: Порог, до которого score считается negative.

    Returns:
        Одна из меток `positive`, `neutral`, `negative`.

    Raises:
        ValueError: Если значение нельзя преобразовать в поддерживаемую метку.
    """
    normalized_value = str(value).strip().lower()
    if normalized_value in LABEL_ALIASES:
        return LABEL_ALIASES[normalized_value]

    try:
        score = float(normalized_value)
    except ValueError as error:
        raise ValueError(f"Unsupported impact value: {value!r}") from error

    if score >= positive_threshold:
        return "positive"
    if score <= negative_threshold:
        return "negative"
    return "neutral"


def prepare_dataset(
    *,
    input_path: Path,
    app_output_path: Path,
    train_output_path: Path,
    id_column: str | None,
    title_column: str,
    text_column: str,
    source_column: str,
    published_at_column: str,
    label_column: str | None = None,
    positive_threshold: float = 0.2,
    negative_threshold: float = -0.2,
    limit: int | None = None,
) -> None:
    """Готовит CSV для news app и research training из внешнего CSV."""
    frame = pd.read_csv(input_path, nrows=limit)
    validate_columns(
        frame,
        required_columns=[
            title_column,
            text_column,
            source_column,
            published_at_column,
            *([label_column] if label_column is not None else []),
        ],
    )

    app_frame = build_app_frame(
        frame,
        id_column=id_column,
        title_column=title_column,
        text_column=text_column,
        source_column=source_column,
        published_at_column=published_at_column,
    )
    write_csv(app_frame, app_output_path, columns=APP_COLUMNS)

    if label_column is None:
        return

    train_frame = build_train_frame(
        app_frame,
        frame[label_column],
        positive_threshold=positive_threshold,
        negative_threshold=negative_threshold,
    )
    write_csv(train_frame, train_output_path, columns=TRAIN_COLUMNS)


def validate_columns(frame: pd.DataFrame, *, required_columns: list[str]) -> None:
    missing_columns = [column for column in required_columns if column not in frame.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")


def build_app_frame(
    frame: pd.DataFrame,
    *,
    id_column: str | None,
    title_column: str,
    text_column: str,
    source_column: str,
    published_at_column: str,
) -> pd.DataFrame:
    title = normalize_text_column(frame, title_column)
    text = normalize_text_column(frame, text_column)
    source = normalize_text_column(frame, source_column)
    published_at = normalize_published_at(frame[published_at_column])
    ids = normalize_ids(
        frame,
        id_column=id_column,
        title=title,
        text=text,
        source=source,
    )

    return pd.DataFrame(
        {
            "id": ids,
            "title": title,
            "text": text,
            "source": source,
            "published_at": published_at,
        },
    )


def normalize_text_column(frame: pd.DataFrame, column: str) -> pd.Series:
    values = frame[column]
    if values.isna().any():
        raise ValueError(f"{column} values must be non-empty")

    normalized_values = values.astype(str).str.strip()
    if normalized_values.eq("").any():
        raise ValueError(f"{column} values must be non-empty")

    return normalized_values


def normalize_published_at(values: pd.Series) -> pd.Series:
    published_at = pd.to_datetime(values, errors="coerce", format="mixed")
    if published_at.isna().any():
        raise ValueError("published_at values must be parseable dates")

    return published_at.dt.strftime("%Y-%m-%dT%H:%M:%S")


def normalize_ids(
    frame: pd.DataFrame,
    *,
    id_column: str | None,
    title: pd.Series,
    text: pd.Series,
    source: pd.Series,
) -> pd.Series:
    if id_column is not None and id_column in frame.columns:
        ids = normalize_text_column(frame, id_column)
        if ids.duplicated().any():
            raise ValueError(f"{id_column} values must be unique")
        return ids

    generated_ids = [
        stable_id(source_value, title_value, text_value)
        for source_value, title_value, text_value in zip(source, title, text, strict=True)
    ]
    return pd.Series(generated_ids, index=frame.index)


def build_train_frame(
    app_frame: pd.DataFrame,
    labels: pd.Series,
    *,
    positive_threshold: float,
    negative_threshold: float,
) -> pd.DataFrame:
    impact = labels.map(
        lambda value: normalize_impact(
            value,
            positive_threshold=positive_threshold,
            negative_threshold=negative_threshold,
        ),
    )
    return pd.DataFrame(
        {
            "article_id": app_frame["id"],
            "text": app_frame["text"],
            "impact": impact,
            "source": app_frame["source"],
            "published_at": app_frame["published_at"],
        },
    )


def write_csv(frame: pd.DataFrame, output_path: Path, *, columns: list[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.loc[:, columns].to_csv(output_path, index=False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare external news dataset CSV files.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--app-output", type=Path, default=Path("data/raw/economic_news.csv"))
    parser.add_argument("--train-output", type=Path, default=Path("data/raw/news_impact.csv"))
    parser.add_argument("--id-column")
    parser.add_argument("--title-column", default="title")
    parser.add_argument("--text-column", default="text")
    parser.add_argument("--source-column", default="source")
    parser.add_argument("--published-at-column", default="published_at")
    parser.add_argument("--label-column")
    parser.add_argument("--positive-threshold", type=float, default=0.2)
    parser.add_argument("--negative-threshold", type=float, default=-0.2)
    parser.add_argument("--limit", type=int)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    prepare_dataset(
        input_path=args.input,
        app_output_path=args.app_output,
        train_output_path=args.train_output,
        id_column=args.id_column,
        title_column=args.title_column,
        text_column=args.text_column,
        source_column=args.source_column,
        published_at_column=args.published_at_column,
        label_column=args.label_column,
        positive_threshold=args.positive_threshold,
        negative_threshold=args.negative_threshold,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
