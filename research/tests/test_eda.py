from pathlib import Path

import pandas as pd

from economic_news_research.data import load_news_dataset
from economic_news_research.eda import build_eda_summary, save_eda_artifacts

FIXTURE = Path(__file__).parent / "fixtures" / "news_impact_sample.csv"


def test_build_eda_summary_contains_core_statistics() -> None:
    dataset = load_news_dataset(FIXTURE)
    summary = build_eda_summary(dataset)
    assert summary.total_rows == 9
    assert summary.class_counts == {"negative": 3, "neutral": 3, "positive": 3}
    assert summary.min_text_length > 0
    assert summary.max_text_length >= summary.min_text_length
    assert set(summary.source_counts) == {"bloomberg", "interfax", "rbc", "reuters", "kommersant"}


def test_save_eda_artifacts_writes_tables_and_plots(tmp_path: Path) -> None:
    dataset = load_news_dataset(FIXTURE)
    save_eda_artifacts(dataset, output_dir=tmp_path)
    assert (tmp_path / "eda_summary.json").exists()
    assert (tmp_path / "class_distribution.csv").exists()
    assert (tmp_path / "source_distribution.csv").exists()
    assert (tmp_path / "class_distribution.png").exists()
    assert (tmp_path / "text_length_distribution.png").exists()
    assert pd.read_csv(tmp_path / "class_distribution.csv")["count"].sum() == 9
