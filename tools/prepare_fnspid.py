from __future__ import annotations

import argparse
import hashlib
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

FNSPID_SOURCE_URL = (
    "https://huggingface.co/datasets/Zihan1004/FNSPID/resolve/main/"
    "Stock_news/nasdaq_exteral_data.csv"
)

APP_COLUMNS = ["id", "title", "text", "source", "published_at"]
TRAIN_COLUMNS = ["article_id", "text", "impact", "source", "published_at"]

TEXT_COLUMNS = ("Article", "article", "text", "body", "content", "description")
TITLE_COLUMNS = ("Article_title", "title", "headline", "Title")
DATE_COLUMNS = ("Date", "date", "published_at", "published", "time")
SOURCE_COLUMNS = ("source", "publisher", "Stock_symbol", "ticker", "symbol")
ID_COLUMNS = ("id", "article_id", "Url", "url", "link")

POSITIVE_MARKERS: frozenset[str] = frozenset(
    {
        "beat",
        "beats",
        "gain",
        "gains",
        "grow",
        "grows",
        "growth",
        "improve",
        "improves",
        "increase",
        "increases",
        "profit",
        "profits",
        "raise",
        "raises",
        "rise",
        "rises",
        "strong demand",
        "upgrade",
        "upgrades",
    },
)
NEGATIVE_MARKERS: frozenset[str] = frozenset(
    {
        "decline",
        "declines",
        "drop",
        "drops",
        "fall",
        "falls",
        "inflation risks",
        "loss",
        "losses",
        "recession",
        "risk",
        "risks",
        "slowdown",
        "weak demand",
        "weaken",
        "weakens",
    },
)


@dataclass(frozen=True)
class FNSPIDPrepareSummary:
    row_count: int
    class_distribution: dict[str, int]
    news_output_path: Path
    training_output_path: Path
    cache_path: Path


def _marker_score(text: str, markers: frozenset[str]) -> int:
    matched_spans: list[tuple[int, int]] = []

    for marker in sorted(markers, key=lambda value: len(value), reverse=True):
        pattern = rf"\b{re.escape(marker)}\b"
        for match in re.finditer(pattern, text):
            span = match.span()
            if any(start < span[1] and span[0] < end for start, end in matched_spans):
                continue
            matched_spans.append(span)

    return len(matched_spans)


def label_impact_from_text(text: str) -> str:
    normalized_text = text.lower()
    positive_score = _marker_score(normalized_text, POSITIVE_MARKERS)
    negative_score = _marker_score(normalized_text, NEGATIVE_MARKERS)

    if positive_score > negative_score:
        return "positive"
    if negative_score > positive_score:
        return "negative"
    return "neutral"


def stable_id(*parts: str) -> str:
    digest = hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest()
    return digest[:16]


def first_existing_column(frame: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    lowered = {column.lower(): column for column in frame.columns}
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]
    return None


def require_column(frame: pd.DataFrame, candidates: tuple[str, ...], label: str) -> str:
    column = first_existing_column(frame, candidates)
    if column is None:
        raise ValueError(f"FNSPID CSV does not contain a {label} column")
    return column


def normalize_text(values: pd.Series, *, max_chars: int) -> pd.Series:
    normalized = values.fillna("").astype(str).str.strip()
    normalized = normalized.str.replace(r"\s+", " ", regex=True)
    normalized = normalized[normalized.ne("")]
    return normalized.str.slice(0, max_chars)


def normalize_dates(values: pd.Series) -> pd.Series:
    dates = pd.to_datetime(values, errors="coerce", format="mixed", utc=True)
    return dates.dt.strftime("%Y-%m-%dT%H:%M:%SZ").fillna("1970-01-01T00:00:00Z")


def build_frames(frame: pd.DataFrame, *, max_text_chars: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    title_column = require_column(frame, TITLE_COLUMNS, "title")
    text_column = require_column(frame, TEXT_COLUMNS, "text")
    date_column = first_existing_column(frame, DATE_COLUMNS)
    source_column = first_existing_column(frame, SOURCE_COLUMNS)
    id_column = first_existing_column(frame, ID_COLUMNS)

    title = normalize_text(frame[title_column], max_chars=300)
    text = normalize_text(frame[text_column], max_chars=max_text_chars)
    valid_index = title.index.intersection(text.index)
    title = title.loc[valid_index]
    text = text.loc[valid_index]

    if source_column is not None:
        source = frame.loc[valid_index, source_column].fillna("FNSPID").astype(str).str.strip()
        source = source.where(source.ne(""), "FNSPID")
    else:
        source = pd.Series("FNSPID", index=valid_index)

    if date_column is not None:
        published_at = normalize_dates(frame.loc[valid_index, date_column])
    else:
        published_at = pd.Series("1970-01-01T00:00:00Z", index=valid_index)

    if id_column is not None:
        ids = frame.loc[valid_index, id_column].fillna("").astype(str).str.strip()
        ids = ids.where(ids.ne(""))
    else:
        ids = pd.Series(index=valid_index, dtype=str)

    fallback_ids = pd.Series(
        [
            stable_id(source_value, title_value, text_value)
            for source_value, title_value, text_value in zip(source, title, text, strict=True)
        ],
        index=valid_index,
    )
    ids = ids.fillna(fallback_ids)

    app_frame = pd.DataFrame(
        {
            "id": ids,
            "title": title,
            "text": text,
            "source": source,
            "published_at": published_at,
        },
    ).drop_duplicates(subset=["id"])
    impact = app_frame["text"].map(label_impact_from_text)
    training_frame = pd.DataFrame(
        {
            "article_id": app_frame["id"],
            "text": app_frame["text"],
            "impact": impact,
            "source": app_frame["source"],
            "published_at": app_frame["published_at"],
        },
    )
    return app_frame, training_frame


def read_limited_csv(source: Path | str, *, limit: int) -> pd.DataFrame:
    if limit <= 0:
        raise ValueError("FNSPID row limit must be positive")

    chunks: list[pd.DataFrame] = []
    rows_left = limit
    for chunk in pd.read_csv(source, chunksize=min(5000, limit)):
        if rows_left <= 0:
            break
        selected = chunk.head(rows_left)
        chunks.append(selected)
        rows_left -= len(selected)
    if not chunks:
        raise ValueError("FNSPID source did not contain any rows")
    return pd.concat(chunks, ignore_index=True)


def write_csv(frame: pd.DataFrame, output_path: Path, columns: list[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.loc[:, columns].to_csv(output_path, index=False)


def prepare_fnspid(
    *,
    source: Path | str,
    cache_path: Path,
    news_output_path: Path,
    training_output_path: Path,
    limit: int,
    max_text_chars: int,
) -> FNSPIDPrepareSummary:
    raw_frame = read_limited_csv(source, limit=limit)
    app_frame, training_frame = build_frames(raw_frame, max_text_chars=max_text_chars)
    if app_frame.empty:
        raise ValueError("FNSPID sample is empty after filtering")

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    raw_frame.loc[app_frame.index].to_csv(cache_path, index=False)
    write_csv(app_frame, news_output_path, APP_COLUMNS)
    write_csv(training_frame, training_output_path, TRAIN_COLUMNS)

    distribution = dict(sorted(Counter(training_frame["impact"]).items()))
    return FNSPIDPrepareSummary(
        row_count=len(app_frame),
        class_distribution=distribution,
        news_output_path=news_output_path,
        training_output_path=training_output_path,
        cache_path=cache_path,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download and prepare a limited FNSPID news sample.",
    )
    parser.add_argument("--local-file", type=Path)
    parser.add_argument("--source-url", default=FNSPID_SOURCE_URL)
    parser.add_argument("--limit", type=int, default=50000)
    parser.add_argument("--cache-path", type=Path, default=Path("data/external/fnspid_sample.csv"))
    parser.add_argument("--output-news", type=Path, default=Path("data/raw/economic_news.csv"))
    parser.add_argument("--output-training", type=Path, default=Path("data/raw/news_impact.csv"))
    parser.add_argument("--max-text-chars", type=int, default=4000)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    source = args.local_file if args.local_file is not None else args.source_url

    try:
        summary = prepare_fnspid(
            source=source,
            cache_path=args.cache_path,
            news_output_path=args.output_news,
            training_output_path=args.output_training,
            limit=args.limit,
            max_text_chars=args.max_text_chars,
        )
    except Exception as error:
        raise SystemExit(
            "Failed to prepare FNSPID sample. "
            "Use --local-file path/to/fnspid.csv if the public source is unavailable. "
            f"Cause: {error}",
        ) from error

    distribution = " ".join(
        f"{label}={count}" for label, count in summary.class_distribution.items()
    )
    print(
        f"rows={summary.row_count} {distribution} "
        f"news_output={summary.news_output_path} "
        f"training_output={summary.training_output_path} "
        f"cache={summary.cache_path}",
    )


if __name__ == "__main__":
    main()
