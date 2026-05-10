import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from tools.prepare_fnspid import label_impact_from_text, prepare_fnspid


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Company profit rises and outlook improves after strong demand", "positive"),
        ("Shares fall as losses widen and demand weakens", "negative"),
        ("The company announced a board meeting on Monday", "neutral"),
        ("Revenue rises but inflation risks increase and demand weakens", "neutral"),
    ],
)
def test_label_impact_from_text_uses_economic_markers(text: str, expected: str) -> None:
    assert label_impact_from_text(text) == expected


def test_prepare_fnspid_writes_news_and_training_csv(tmp_path: Path) -> None:
    source_path = tmp_path / "fnspid.csv"
    news_output_path = tmp_path / "economic_news.csv"
    training_output_path = tmp_path / "news_impact.csv"
    cache_path = tmp_path / "fnspid_sample.csv"
    pd.DataFrame(
        {
            "Date": ["2026-05-01", "2026-05-02", "2026-05-03"],
            "Article_title": ["Profit rises", "Losses widen", "Board meeting"],
            "Article": [
                "Company profit rises after strong demand",
                "Shares fall as losses widen",
                "The company announced a board meeting",
            ],
            "Stock_symbol": ["AAPL", "MSFT", "JPM"],
            "Url": [
                "https://example.com/1",
                "https://example.com/2",
                "https://example.com/3",
            ],
        },
    ).to_csv(source_path, index=False)

    summary = prepare_fnspid(
        source=source_path,
        cache_path=cache_path,
        news_output_path=news_output_path,
        training_output_path=training_output_path,
        limit=3,
        max_text_chars=200,
    )

    news_frame = pd.read_csv(news_output_path)
    training_frame = pd.read_csv(training_output_path)
    cached_frame = pd.read_csv(cache_path)

    assert summary.row_count == 3
    assert summary.class_distribution == {"negative": 1, "neutral": 1, "positive": 1}
    assert news_frame.columns.to_list() == ["id", "title", "text", "source", "published_at"]
    assert training_frame.columns.to_list() == [
        "article_id",
        "text",
        "impact",
        "source",
        "published_at",
    ]
    assert training_frame["impact"].to_list() == ["positive", "negative", "neutral"]
    assert cached_frame.shape[0] == 3
