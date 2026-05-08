import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from tools.prepare_dataset import normalize_impact, prepare_dataset, stable_id


def test_prepare_dataset_writes_app_and_training_csv_from_custom_columns(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "external.csv"
    app_output_path = tmp_path / "app.csv"
    train_output_path = tmp_path / "train.csv"
    pd.DataFrame(
        {
            "headline": ["Rates rise", "Stocks steady"],
            "body": ["Central bank raised rates", "Market closed flat"],
            "publisher": ["Reuters", "Bloomberg"],
            "date": ["2026-05-01", "2026-05-02T10:30:00"],
            "sentiment": ["pos", "negative"],
        },
    ).to_csv(input_path, index=False)

    prepare_dataset(
        input_path=input_path,
        app_output_path=app_output_path,
        train_output_path=train_output_path,
        id_column=None,
        title_column="headline",
        text_column="body",
        source_column="publisher",
        published_at_column="date",
        label_column="sentiment",
    )

    app_frame = pd.read_csv(app_output_path)
    train_frame = pd.read_csv(train_output_path)

    expected_ids = [
        stable_id("Reuters", "Rates rise", "Central bank raised rates"),
        stable_id("Bloomberg", "Stocks steady", "Market closed flat"),
    ]
    assert app_frame.columns.to_list() == ["id", "title", "text", "source", "published_at"]
    assert app_frame["id"].to_list() == expected_ids
    assert app_frame["title"].to_list() == ["Rates rise", "Stocks steady"]

    assert train_frame.columns.to_list() == [
        "article_id",
        "text",
        "impact",
        "source",
        "published_at",
    ]
    assert train_frame["article_id"].to_list() == expected_ids
    assert train_frame["impact"].to_list() == ["positive", "negative"]


def test_normalize_impact_maps_numeric_scores() -> None:
    assert normalize_impact(0.7, positive_threshold=0.2, negative_threshold=-0.2) == "positive"
    assert normalize_impact(-0.8, positive_threshold=0.2, negative_threshold=-0.2) == "negative"
    assert normalize_impact(0.1, positive_threshold=0.2, negative_threshold=-0.2) == "neutral"


def test_prepare_dataset_validates_required_columns(tmp_path: Path) -> None:
    input_path = tmp_path / "external.csv"
    pd.DataFrame(
        {
            "headline": ["Rates rise"],
            "publisher": ["Reuters"],
            "date": ["2026-05-01"],
        },
    ).to_csv(input_path, index=False)

    with pytest.raises(ValueError, match="Missing required columns"):
        prepare_dataset(
            input_path=input_path,
            app_output_path=tmp_path / "app.csv",
            train_output_path=tmp_path / "train.csv",
            id_column=None,
            title_column="headline",
            text_column="body",
            source_column="publisher",
            published_at_column="date",
            label_column=None,
        )
