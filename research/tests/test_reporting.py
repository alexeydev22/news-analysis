import json
from pathlib import Path

import pandas as pd
import pytest

from economic_news_research import modeling
from economic_news_research.data import load_news_dataset, split_news_dataset
from economic_news_research.modeling import train_baseline_model
from economic_news_research.reporting import build_model_report, save_model_report
from economic_news_research.tracking import save_model_artifacts

FIXTURE = Path(__file__).parent / "fixtures" / "news_impact_sample.csv"


@pytest.fixture
def fixture_safe_baseline_grid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        modeling,
        "baseline_param_grid",
        lambda: {
            "tfidf__max_features": [100],
            "tfidf__ngram_range": [(1, 1)],
            "tfidf__min_df": [1],
            "tfidf__max_df": [1.0],
            "tfidf__sublinear_tf": [True],
            "classifier__C": [1.0],
        },
    )


@pytest.mark.usefixtures("fixture_safe_baseline_grid")
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
        training_limits={
            "classic_max_rows": 20_000,
            "embedding_max_rows": 5_000,
            "transformer_max_rows": 5_000,
        },
    )

    assert report["dataset"]["row_count"] == 9
    assert report["dataset"]["class_distribution"] == {
        "negative": 3,
        "neutral": 3,
        "positive": 3,
    }
    assert report["dataset"]["label_quality"] == {"label_source": "provided"}
    assert report["best_model"]["model_name"] == "tfidf-logreg"
    assert report["models"][0]["model_name"] == "tfidf-logreg"
    assert report["models"][0]["confusion_matrix"]["labels"] == [
        "negative",
        "neutral",
        "positive",
    ]
    assert report["models"][0]["per_class"]["negative"]["recall"] >= 0.0
    assert report["models"][0]["per_class"]["positive"]["f1"] <= 1.0
    assert report["training"] == {
        "classic_max_rows": 20_000,
        "embedding_max_rows": 5_000,
        "transformer_max_rows": 5_000,
    }
    assert report["top_features"]["tfidf-logreg"]["positive"]


def test_build_model_report_summarizes_weak_label_quality(tmp_path: Path) -> None:
    dataset_path = tmp_path / "fnspid.csv"
    pd.DataFrame(
        {
            "id": ["positive-news", "negative-news", "neutral-news"],
            "title": [
                "Company reports profit growth",
                "Company shares fall",
                "Company updates outlook",
            ],
            "text": [
                "Revenue rose and earnings beat expectations.",
                "Revenue declined and losses increased.",
                "Revenue rose, but management warned about risks.",
            ],
            "source": ["FNSPID", "FNSPID", "FNSPID"],
            "published_at": [
                "2024-01-01T00:00:00Z",
                "2024-01-02T00:00:00Z",
                "2024-01-03T00:00:00Z",
            ],
        },
    ).to_csv(dataset_path, index=False)
    comparison_path = tmp_path / "model_comparison.csv"
    comparison_path.write_text(
        "model_name,validation_accuracy,validation_macro_f1,test_accuracy,"
        "test_macro_f1,inference_seconds_per_sample\n"
        "tfidf-logreg,0.8,0.7,0.81,0.72,0.001\n",
        encoding="utf-8",
    )

    report = build_model_report(
        dataset_path=dataset_path,
        comparison_path=comparison_path,
        model_dirs=[],
    )

    label_quality = report["dataset"]["label_quality"]
    assert label_quality["label_source"] == "weak_rules"
    assert label_quality["low_margin_count"] == 1
    assert label_quality["average_margin"] == pytest.approx(8 / 3)


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
