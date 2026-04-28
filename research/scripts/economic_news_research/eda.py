import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib
import pandas as pd
import seaborn as sns

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


@dataclass(frozen=True)
class EdaSummary:
    total_rows: int
    class_counts: dict[str, int]
    source_counts: dict[str, int]
    min_text_length: int
    mean_text_length: float
    max_text_length: int


def build_eda_summary(dataset: pd.DataFrame) -> EdaSummary:
    text_lengths = dataset["text"].str.len()
    return EdaSummary(
        total_rows=len(dataset),
        class_counts=dataset["impact"].value_counts().sort_index().to_dict(),
        source_counts=dataset["source"].value_counts().sort_index().to_dict(),
        min_text_length=int(text_lengths.min()),
        mean_text_length=float(text_lengths.mean()),
        max_text_length=int(text_lengths.max()),
    )


def save_eda_artifacts(dataset: pd.DataFrame, *, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = build_eda_summary(dataset)

    (output_dir / "eda_summary.json").write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    class_distribution = (
        dataset["impact"].value_counts().rename_axis("impact").reset_index(name="count")
    )
    class_distribution.to_csv(output_dir / "class_distribution.csv", index=False)

    source_distribution = (
        dataset["source"].value_counts().rename_axis("source").reset_index(name="count")
    )
    source_distribution.to_csv(output_dir / "source_distribution.csv", index=False)

    _save_bar_plot(
        class_distribution,
        x="impact",
        y="count",
        title="Impact class distribution",
        path=output_dir / "class_distribution.png",
    )
    length_frame = pd.DataFrame({"text_length": dataset["text"].str.len()})
    _save_histogram(
        length_frame,
        column="text_length",
        title="News text length distribution",
        path=output_dir / "text_length_distribution.png",
    )


def _save_bar_plot(frame: pd.DataFrame, *, x: str, y: str, title: str, path: Path) -> None:
    plt.figure(figsize=(8, 5))
    sns.barplot(data=frame, x=x, y=y)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path)
    plt.close()


def _save_histogram(frame: pd.DataFrame, *, column: str, title: str, path: Path) -> None:
    plt.figure(figsize=(8, 5))
    sns.histplot(data=frame, x=column, bins=10)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
