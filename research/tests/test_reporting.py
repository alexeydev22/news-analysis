import json
from pathlib import Path

import pandas as pd

from economic_news_research.data import load_news_dataset, split_news_dataset
from economic_news_research.modeling import train_baseline_model
from economic_news_research.reporting import build_model_report, save_model_report
from economic_news_research.tracking import save_model_artifacts

FIXTURE = Path(__file__).parent / "fixtures" / "news_impact_sample.csv"


def test_build_model_report_summarizes_dataset_models_and_features(tmp_path: Path) -> None:
    dataset = load_news_dataset(FIXTURE)
    split = split_news_dataset(dataset, random_state=42)
    result = train_baseline_model(split, random_state=42)
    baseline_dir = tmp_path / "baseline"
    save_model_artifacts(result, output_dir=baseline_dir)
    comparison_path = tmp_path / "model_comparison.csv"
    pd.read_csv(baseline_dir / "model_comparison.csv").to_csv(comparison_path, index=False)

    report = build_model_report(
        dataset_path=FIXTURE,
        comparison_path=comparison_path,
        model_dirs=[baseline_dir],
    )

    assert report["dataset"]["row_count"] == 9
    assert report["dataset"]["class_distribution"] == {
        "negative": 3,
        "neutral": 3,
        "positive": 3,
    }
    assert report["best_model"]["model_name"] == "tfidf-logreg"
    assert report["models"][0]["model_name"] == "tfidf-logreg"
    assert report["models"][0]["confusion_matrix"]["labels"] == [
        "negative",
        "neutral",
        "positive",
    ]
    assert report["top_features"]["tfidf-logreg"]["positive"]


def test_save_model_report_writes_json(tmp_path: Path) -> None:
    output_path = tmp_path / "model-report.json"

    saved_path = save_model_report(
        {
            "dataset": {"row_count": 1},
            "models": [],
            "best_model": None,
            "top_features": {},
        },
        output_path=output_path,
    )

    assert saved_path == output_path
    assert json.loads(output_path.read_text(encoding="utf-8"))["dataset"]["row_count"] == 1
