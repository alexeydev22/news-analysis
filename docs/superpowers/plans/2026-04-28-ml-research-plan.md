# ML Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible ML research pipeline for economic news impact classification with data validation, EDA reports, baseline modeling, MLflow tracking, and exportable artifacts for coursework.

**Architecture:** The research code lives under `research/scripts/economic_news_research` as a small Python package independent from backend services. It reads the full dataset from `data/raw/news_impact.csv`, writes processed datasets and reports into ignored runtime folders, and uses committed test fixtures for deterministic tests.

**Tech Stack:** Python, pandas, scikit-learn, matplotlib, seaborn, joblib, MLflow, pytest, ruff, ty, uv workspace.

---

## Scope

This plan implements the first research slice:

- dataset schema and validation for impact labels;
- deterministic train/validation/test split;
- EDA tables and plots;
- TF-IDF + Logistic Regression baseline;
- grid search over at least 3 hyperparameters;
- MLflow logging;
- export of metrics, confusion matrix, model artifact, and comparison table.

This plan does not implement transformer fine-tuning yet. That belongs to the next `feature/ml-transformers` plan, after the baseline and report format are stable.

## Dataset Contract

The full dataset is expected at:

```text
data/raw/news_impact.csv
```

Required columns:

```text
article_id,text,impact,source,published_at
```

Allowed `impact` values:

```text
positive,neutral,negative
```

The full raw dataset is not committed. Tests use:

```text
research/tests/fixtures/news_impact_sample.csv
```

## File Structure

```text
research/
  README.md
  scripts/
    economic_news_research/
      __init__.py
      cli.py
      data.py
      eda.py
      metrics.py
      modeling.py
      tracking.py
      paths.py
  tests/
    fixtures/
      news_impact_sample.csv
    test_data.py
    test_eda.py
    test_modeling.py
    test_metrics.py
```

---

### Task 1: Configure Research Dependencies and Package Skeleton

**Files:**
- Modify: `pyproject.toml`
- Create: `research/README.md`
- Create: `research/scripts/economic_news_research/__init__.py`
- Create: `research/scripts/economic_news_research/paths.py`
- Create: `research/tests/fixtures/news_impact_sample.csv`

- [ ] **Step 1: Update root dev dependencies**

Modify `[dependency-groups].dev` in `pyproject.toml` so it contains these additional packages:

```toml
  "joblib>=1.4",
  "matplotlib>=3.9",
  "mlflow>=2.19",
  "pandas>=2.2",
  "scikit-learn>=1.6",
  "seaborn>=0.13",
```

Keep existing dependencies.

- [ ] **Step 2: Add research package to pytest pythonpath**

Modify `[tool.pytest.ini_options].pythonpath` in `pyproject.toml` to include:

```toml
  "research/scripts",
```

- [ ] **Step 3: Add research package marker**

Create `research/scripts/economic_news_research/__init__.py`:

```python
"""Research pipeline for economic news impact classification."""
```

- [ ] **Step 4: Add path helpers**

Create `research/scripts/economic_news_research/paths.py`:

```python
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
RESEARCH_DIR = REPO_ROOT / "research"
REPORTS_DIR = RESEARCH_DIR / "reports"
ARTIFACTS_DIR = REPO_ROOT / "artifacts"
MODELS_DIR = ARTIFACTS_DIR / "models"
MLFLOW_DIR = ARTIFACTS_DIR / "mlflow"

DEFAULT_RAW_DATASET = RAW_DATA_DIR / "news_impact.csv"
DEFAULT_PROCESSED_DATASET = PROCESSED_DATA_DIR / "news_impact_processed.csv"
```

- [ ] **Step 5: Add sample fixture**

Create `research/tests/fixtures/news_impact_sample.csv`:

```csv
article_id,text,impact,source,published_at
n-001,"Central bank signals lower rates as inflation slows",positive,reuters,2026-01-12
n-002,"Oil prices fall after weak manufacturing data",negative,reuters,2026-01-13
n-003,"Markets wait for budget decision with limited movement",neutral,interfax,2026-01-14
n-004,"Technology shares rise after strong earnings forecast",positive,bloomberg,2026-01-15
n-005,"Retail sales decline amid tighter credit conditions",negative,bloomberg,2026-01-16
n-006,"Analysts keep GDP forecast unchanged before new data",neutral,interfax,2026-01-17
n-007,"Exporters gain as national currency weakens",positive,rbc,2026-01-18
n-008,"Banking sector drops after loan quality warning",negative,rbc,2026-01-19
n-009,"Bond yields remain stable before treasury auction",neutral,kommersant,2026-01-20
```

- [ ] **Step 6: Add research README**

Create `research/README.md`:

```markdown
# ML Research

This folder contains reproducible research code for economic news impact classification.

## Dataset

Place the full dataset at:

```text
data/raw/news_impact.csv
```

Required columns:

```text
article_id,text,impact,source,published_at
```

Allowed labels:

```text
positive,neutral,negative
```

Raw datasets are not committed. Tests use a small committed fixture in `research/tests/fixtures`.

## Commands

```bash
uv run python -m economic_news_research.cli validate
uv run python -m economic_news_research.cli eda
uv run python -m economic_news_research.cli train-baseline
```
```

- [ ] **Step 7: Lock dependencies**

Run:

```bash
uv lock
```

Expected: lockfile updates successfully.

- [ ] **Step 8: Run existing checks**

Run:

```bash
uv run ruff check apps packages research
uv run pytest packages apps -v
```

Expected: ruff passes and existing 10 tests pass.

- [ ] **Step 9: Commit**

Run:

```bash
git add pyproject.toml uv.lock research/README.md research/scripts/economic_news_research/__init__.py research/scripts/economic_news_research/paths.py research/tests/fixtures/news_impact_sample.csv
git commit -m "feat: настроить исследовательский пакет"
git push -u origin feature/ml-research
```

Expected: commit succeeds and branch is pushed.

---

### Task 2: Implement Dataset Loading and Validation

**Files:**
- Create: `research/scripts/economic_news_research/data.py`
- Create: `research/tests/test_data.py`

- [ ] **Step 1: Write failing tests**

Create `research/tests/test_data.py`:

```python
from pathlib import Path

import pandas as pd
import pytest

from economic_news_research.data import (
    ImpactLabel,
    NewsDatasetError,
    load_news_dataset,
    split_news_dataset,
    validate_news_dataset,
)


FIXTURE = Path(__file__).parent / "fixtures" / "news_impact_sample.csv"


def test_load_news_dataset_returns_valid_frame() -> None:
    dataset = load_news_dataset(FIXTURE)

    assert list(dataset.columns) == ["article_id", "text", "impact", "source", "published_at"]
    assert set(dataset["impact"]) == {ImpactLabel.POSITIVE, ImpactLabel.NEUTRAL, ImpactLabel.NEGATIVE}
    assert len(dataset) == 9


def test_validate_news_dataset_rejects_missing_columns() -> None:
    frame = pd.DataFrame({"text": ["Market rises"], "impact": ["positive"]})

    with pytest.raises(NewsDatasetError, match="Missing required columns"):
        validate_news_dataset(frame)


def test_validate_news_dataset_rejects_unknown_label() -> None:
    frame = pd.read_csv(FIXTURE)
    frame.loc[0, "impact"] = "mixed"

    with pytest.raises(NewsDatasetError, match="Unknown impact labels"):
        validate_news_dataset(frame)


def test_split_news_dataset_is_deterministic() -> None:
    dataset = load_news_dataset(FIXTURE)

    first = split_news_dataset(dataset, random_state=42)
    second = split_news_dataset(dataset, random_state=42)

    assert first.train["article_id"].tolist() == second.train["article_id"].tolist()
    assert first.validation["article_id"].tolist() == second.validation["article_id"].tolist()
    assert first.test["article_id"].tolist() == second.test["article_id"].tolist()
    assert len(first.train) == 5
    assert len(first.validation) == 2
    assert len(first.test) == 2
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest research/tests/test_data.py -v
```

Expected: FAIL with missing module or functions.

- [ ] **Step 3: Implement dataset module**

Create `research/scripts/economic_news_research/data.py`:

```python
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
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing_columns:
        raise NewsDatasetError(f"Missing required columns: {missing_columns}")

    dataset = frame.loc[:, REQUIRED_COLUMNS].copy()
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
```

- [ ] **Step 4: Run tests**

Run:

```bash
uv run pytest research/tests/test_data.py -v
```

Expected: PASS.

- [ ] **Step 5: Run checks**

Run:

```bash
uv run ruff check research
uv run ty check research
```

Expected: both pass.

- [ ] **Step 6: Commit**

Run:

```bash
git add research/scripts/economic_news_research/data.py research/tests/test_data.py
git commit -m "feat: добавить валидацию датасета новостей"
git push
```

Expected: commit succeeds and branch is pushed.

---

### Task 3: Implement EDA Report Generation

**Files:**
- Create: `research/scripts/economic_news_research/eda.py`
- Create: `research/tests/test_eda.py`

- [ ] **Step 1: Write failing tests**

Create `research/tests/test_eda.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest research/tests/test_eda.py -v
```

Expected: FAIL with missing EDA module.

- [ ] **Step 3: Implement EDA module**

Create `research/scripts/economic_news_research/eda.py`:

```python
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


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
```

- [ ] **Step 4: Run tests**

Run:

```bash
uv run pytest research/tests/test_eda.py -v
```

Expected: PASS.

- [ ] **Step 5: Run checks**

Run:

```bash
uv run ruff check research
uv run ty check research
```

Expected: both pass.

- [ ] **Step 6: Commit**

Run:

```bash
git add research/scripts/economic_news_research/eda.py research/tests/test_eda.py
git commit -m "feat: добавить eda отчеты для новостей"
git push
```

Expected: commit succeeds and branch is pushed.

---

### Task 4: Implement Metrics and Baseline Model

**Files:**
- Create: `research/scripts/economic_news_research/metrics.py`
- Create: `research/scripts/economic_news_research/modeling.py`
- Create: `research/tests/test_metrics.py`
- Create: `research/tests/test_modeling.py`

- [ ] **Step 1: Write metrics tests**

Create `research/tests/test_metrics.py`:

```python
from economic_news_research.metrics import ClassificationMetrics, compute_classification_metrics


def test_compute_classification_metrics_returns_macro_scores() -> None:
    metrics = compute_classification_metrics(
        y_true=["positive", "negative", "neutral", "positive"],
        y_pred=["positive", "neutral", "neutral", "positive"],
        labels=["negative", "neutral", "positive"],
    )

    assert isinstance(metrics, ClassificationMetrics)
    assert metrics.accuracy == 0.75
    assert 0 <= metrics.macro_precision <= 1
    assert 0 <= metrics.macro_recall <= 1
    assert 0 <= metrics.macro_f1 <= 1
    assert metrics.confusion_matrix.shape == (3, 3)
```

- [ ] **Step 2: Write modeling tests**

Create `research/tests/test_modeling.py`:

```python
from pathlib import Path

from economic_news_research.data import load_news_dataset, split_news_dataset
from economic_news_research.modeling import (
    BaselineTrainingResult,
    build_baseline_pipeline,
    train_baseline_model,
)


FIXTURE = Path(__file__).parent / "fixtures" / "news_impact_sample.csv"


def test_build_baseline_pipeline_predicts_labels() -> None:
    pipeline = build_baseline_pipeline(max_features=100, c_value=1.0, ngram_range=(1, 1))
    dataset = load_news_dataset(FIXTURE)

    pipeline.fit(dataset["text"], dataset["impact"])
    predictions = pipeline.predict(dataset["text"])

    assert len(predictions) == len(dataset)
    assert set(predictions).issubset({"positive", "neutral", "negative"})


def test_train_baseline_model_returns_metrics() -> None:
    dataset = load_news_dataset(FIXTURE)
    split = split_news_dataset(dataset, random_state=42)

    result = train_baseline_model(split, random_state=42)

    assert isinstance(result, BaselineTrainingResult)
    assert result.model_name == "tfidf-logreg"
    assert result.validation_metrics.confusion_matrix.shape == (3, 3)
    assert result.best_params["classifier__C"] in {0.1, 1.0, 10.0}
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
uv run pytest research/tests/test_metrics.py research/tests/test_modeling.py -v
```

Expected: FAIL with missing modules.

- [ ] **Step 4: Implement metrics**

Create `research/scripts/economic_news_research/metrics.py`:

```python
from dataclasses import dataclass

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support


@dataclass(frozen=True)
class ClassificationMetrics:
    accuracy: float
    macro_precision: float
    macro_recall: float
    macro_f1: float
    confusion_matrix: np.ndarray


def compute_classification_metrics(
    *,
    y_true: list[str],
    y_pred: list[str],
    labels: list[str],
) -> ClassificationMetrics:
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=labels,
        average="macro",
        zero_division=0,
    )
    return ClassificationMetrics(
        accuracy=float(accuracy_score(y_true, y_pred)),
        macro_precision=float(precision),
        macro_recall=float(recall),
        macro_f1=float(f1),
        confusion_matrix=confusion_matrix(y_true, y_pred, labels=labels),
    )
```

- [ ] **Step 5: Implement baseline modeling**

Create `research/scripts/economic_news_research/modeling.py`:

```python
from dataclasses import dataclass
from typing import Any

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline

from economic_news_research.data import DatasetSplit
from economic_news_research.metrics import ClassificationMetrics, compute_classification_metrics


IMPACT_LABELS = ["negative", "neutral", "positive"]


@dataclass(frozen=True)
class BaselineTrainingResult:
    model_name: str
    best_params: dict[str, Any]
    validation_metrics: ClassificationMetrics
    test_metrics: ClassificationMetrics
    estimator: Pipeline


def build_baseline_pipeline(
    *,
    max_features: int,
    c_value: float,
    ngram_range: tuple[int, int],
) -> Pipeline:
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    max_features=max_features,
                    ngram_range=ngram_range,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    C=c_value,
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )


def train_baseline_model(split: DatasetSplit, *, random_state: int) -> BaselineTrainingResult:
    pipeline = build_baseline_pipeline(max_features=1000, c_value=1.0, ngram_range=(1, 1))
    grid = GridSearchCV(
        estimator=pipeline,
        param_grid={
            "tfidf__max_features": [100, 1000],
            "tfidf__ngram_range": [(1, 1), (1, 2)],
            "classifier__C": [0.1, 1.0, 10.0],
        },
        scoring="f1_macro",
        cv=_safe_cv(split.train),
        n_jobs=1,
    )
    grid.fit(split.train["text"], split.train["impact"])
    estimator = grid.best_estimator_

    validation_predictions = estimator.predict(split.validation["text"])
    test_predictions = estimator.predict(split.test["text"])

    return BaselineTrainingResult(
        model_name="tfidf-logreg",
        best_params=dict(grid.best_params_),
        validation_metrics=compute_classification_metrics(
            y_true=split.validation["impact"].tolist(),
            y_pred=validation_predictions.tolist(),
            labels=IMPACT_LABELS,
        ),
        test_metrics=compute_classification_metrics(
            y_true=split.test["impact"].tolist(),
            y_pred=test_predictions.tolist(),
            labels=IMPACT_LABELS,
        ),
        estimator=estimator,
    )


def _safe_cv(train: pd.DataFrame) -> int:
    min_class_count = int(train["impact"].value_counts().min())
    return max(2, min(3, min_class_count))
```

- [ ] **Step 6: Run tests**

Run:

```bash
uv run pytest research/tests/test_metrics.py research/tests/test_modeling.py -v
```

Expected: PASS.

- [ ] **Step 7: Run checks**

Run:

```bash
uv run ruff check research
uv run ty check research
```

Expected: both pass.

- [ ] **Step 8: Commit**

Run:

```bash
git add research/scripts/economic_news_research/metrics.py research/scripts/economic_news_research/modeling.py research/tests/test_metrics.py research/tests/test_modeling.py
git commit -m "feat: добавить baseline модель классификации"
git push
```

Expected: commit succeeds and branch is pushed.

---

### Task 5: Implement MLflow Tracking and Artifact Export

**Files:**
- Create: `research/scripts/economic_news_research/tracking.py`
- Modify: `research/tests/test_modeling.py`

- [ ] **Step 1: Add tracking test**

Append to `research/tests/test_modeling.py`:

```python
from economic_news_research.tracking import save_baseline_artifacts


def test_save_baseline_artifacts_writes_expected_files(tmp_path: Path) -> None:
    dataset = load_news_dataset(FIXTURE)
    split = split_news_dataset(dataset, random_state=42)
    result = train_baseline_model(split, random_state=42)

    save_baseline_artifacts(result, output_dir=tmp_path)

    assert (tmp_path / "tfidf-logreg.joblib").exists()
    assert (tmp_path / "tfidf-logreg_metrics.json").exists()
    assert (tmp_path / "tfidf-logreg_confusion_matrix.csv").exists()
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
uv run pytest research/tests/test_modeling.py::test_save_baseline_artifacts_writes_expected_files -v
```

Expected: FAIL with missing tracking module.

- [ ] **Step 3: Implement tracking module**

Create `research/scripts/economic_news_research/tracking.py`:

```python
import json
from dataclasses import asdict
from pathlib import Path

import joblib
import mlflow
import pandas as pd

from economic_news_research.modeling import BaselineTrainingResult, IMPACT_LABELS


def save_baseline_artifacts(result: BaselineTrainingResult, *, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / f"{result.model_name}.joblib"
    metrics_path = output_dir / f"{result.model_name}_metrics.json"
    confusion_matrix_path = output_dir / f"{result.model_name}_confusion_matrix.csv"

    joblib.dump(result.estimator, model_path)
    metrics_payload = {
        "model_name": result.model_name,
        "best_params": result.best_params,
        "validation": _serializable_metrics(result.validation_metrics),
        "test": _serializable_metrics(result.test_metrics),
    }
    metrics_path.write_text(json.dumps(metrics_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    confusion_frame = pd.DataFrame(
        result.test_metrics.confusion_matrix,
        index=IMPACT_LABELS,
        columns=IMPACT_LABELS,
    )
    confusion_frame.to_csv(confusion_matrix_path)


def log_baseline_to_mlflow(result: BaselineTrainingResult, *, artifact_dir: Path) -> None:
    with mlflow.start_run(run_name=result.model_name):
        mlflow.log_params(result.best_params)
        mlflow.log_metric("validation_accuracy", result.validation_metrics.accuracy)
        mlflow.log_metric("validation_macro_f1", result.validation_metrics.macro_f1)
        mlflow.log_metric("test_accuracy", result.test_metrics.accuracy)
        mlflow.log_metric("test_macro_f1", result.test_metrics.macro_f1)
        mlflow.log_artifacts(str(artifact_dir))


def _serializable_metrics(metrics) -> dict[str, float]:
    payload = asdict(metrics)
    payload.pop("confusion_matrix")
    return payload
```

- [ ] **Step 4: Run tracking test**

Run:

```bash
uv run pytest research/tests/test_modeling.py::test_save_baseline_artifacts_writes_expected_files -v
```

Expected: PASS.

- [ ] **Step 5: Run checks**

Run:

```bash
uv run pytest research/tests -v
uv run ruff check research
uv run ty check research
```

Expected: all pass.

- [ ] **Step 6: Commit**

Run:

```bash
git add research/scripts/economic_news_research/tracking.py research/tests/test_modeling.py
git commit -m "feat: добавить экспорт артефактов baseline"
git push
```

Expected: commit succeeds and branch is pushed.

---

### Task 6: Implement Research CLI

**Files:**
- Create: `research/scripts/economic_news_research/cli.py`
- Create: `research/tests/test_cli.py`

- [ ] **Step 1: Write CLI tests**

Create `research/tests/test_cli.py`:

```python
from pathlib import Path

from economic_news_research.cli import run_eda, run_train_baseline, run_validate


FIXTURE = Path(__file__).parent / "fixtures" / "news_impact_sample.csv"


def test_run_validate_returns_row_count() -> None:
    assert run_validate(dataset_path=FIXTURE) == 9


def test_run_eda_writes_report(tmp_path: Path) -> None:
    run_eda(dataset_path=FIXTURE, output_dir=tmp_path)

    assert (tmp_path / "eda_summary.json").exists()


def test_run_train_baseline_writes_model_artifacts(tmp_path: Path) -> None:
    run_train_baseline(dataset_path=FIXTURE, output_dir=tmp_path, random_state=42)

    assert (tmp_path / "tfidf-logreg.joblib").exists()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest research/tests/test_cli.py -v
```

Expected: FAIL with missing CLI module.

- [ ] **Step 3: Implement CLI module**

Create `research/scripts/economic_news_research/cli.py`:

```python
import argparse
from pathlib import Path

from economic_news_research.data import load_news_dataset, split_news_dataset
from economic_news_research.eda import save_eda_artifacts
from economic_news_research.modeling import train_baseline_model
from economic_news_research.paths import DEFAULT_RAW_DATASET, MODELS_DIR, REPORTS_DIR
from economic_news_research.tracking import log_baseline_to_mlflow, save_baseline_artifacts


def run_validate(*, dataset_path: Path) -> int:
    dataset = load_news_dataset(dataset_path)
    return len(dataset)


def run_eda(*, dataset_path: Path, output_dir: Path) -> None:
    dataset = load_news_dataset(dataset_path)
    save_eda_artifacts(dataset, output_dir=output_dir)


def run_train_baseline(*, dataset_path: Path, output_dir: Path, random_state: int) -> None:
    dataset = load_news_dataset(dataset_path)
    split = split_news_dataset(dataset, random_state=random_state)
    result = train_baseline_model(split, random_state=random_state)
    save_baseline_artifacts(result, output_dir=output_dir)
    log_baseline_to_mlflow(result, artifact_dir=output_dir)


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--dataset", type=Path, default=DEFAULT_RAW_DATASET)

    eda_parser = subparsers.add_parser("eda")
    eda_parser.add_argument("--dataset", type=Path, default=DEFAULT_RAW_DATASET)
    eda_parser.add_argument("--output-dir", type=Path, default=REPORTS_DIR / "eda")

    train_parser = subparsers.add_parser("train-baseline")
    train_parser.add_argument("--dataset", type=Path, default=DEFAULT_RAW_DATASET)
    train_parser.add_argument("--output-dir", type=Path, default=MODELS_DIR / "baseline")
    train_parser.add_argument("--random-state", type=int, default=42)

    args = parser.parse_args()
    if args.command == "validate":
        rows = run_validate(dataset_path=args.dataset)
        print(f"validated_rows={rows}")
    elif args.command == "eda":
        run_eda(dataset_path=args.dataset, output_dir=args.output_dir)
        print(f"eda_output_dir={args.output_dir}")
    elif args.command == "train-baseline":
        run_train_baseline(
            dataset_path=args.dataset,
            output_dir=args.output_dir,
            random_state=args.random_state,
        )
        print(f"baseline_output_dir={args.output_dir}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run CLI tests**

Run:

```bash
uv run pytest research/tests/test_cli.py -v
```

Expected: PASS.

- [ ] **Step 5: Run all checks**

Run:

```bash
uv run ruff format apps packages research
uv run ruff check apps packages research
uv run ty check apps packages research
uv run pytest packages apps research/tests -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

Run:

```bash
git add research/scripts/economic_news_research/cli.py research/tests/test_cli.py
git commit -m "feat: добавить cli для ml исследования"
git push
```

Expected: commit succeeds and branch is pushed.

---

## Self-Review Checklist

- Spec coverage:
  - Dataset validation and processing: Tasks 1-2.
  - EDA and visualizations: Task 3.
  - Baseline model and grid search over 3 hyperparameters: Task 4.
  - MLflow/artifact export: Task 5.
  - Reproducible commands for coursework: Task 6.
- Follow-up scope:
  - Transformer embedding classifier and fine-tuned model are scheduled for the next plan because they require model downloads, longer runtime, and broader hardware checks.
  - Full raw dataset acquisition is outside this plan; this plan defines the committed schema and test fixture, while `data/raw/news_impact.csv` remains a local input.
- Completion-marker scan: no unfinished markers or unspecified test instructions.
- Type consistency:
  - `ImpactLabel`, `DatasetSplit`, `ClassificationMetrics`, `BaselineTrainingResult`, and CLI function names are defined before later tasks use them.
