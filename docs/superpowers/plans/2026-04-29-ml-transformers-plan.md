# ML Transformers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the research pipeline from one baseline model to a reproducible three-model comparison for economic news impact classification.

**Architecture:** Keep this as a research-only slice under `research/scripts/economic_news_research`. Generalize the training result/export contract first, then add an embedding classifier and a tiny transformer orchestration layer with offline deterministic tests. Real model downloads are only used by manual training commands, never by unit tests.

**Tech Stack:** Python, pandas, scikit-learn, sentence-transformers, transformers, torch, MLflow, joblib, pytest, ruff, ty, uv workspace.

---

## Scope

This plan implements:

- shared research model result with inference timing;
- `embedding-logreg` model with sentence-transformer embeddings and deterministic fake embedder tests;
- `tiny-transformer-classifier` orchestration with Hugging Face production adapter and fake offline tests;
- generic artifact export for multiple models;
- CLI commands for embedding, transformer, and model comparison;
- ignored local Hugging Face cache and generated reports/artifacts.

This plan does not implement backend services, Qdrant, React UI, SSE, or dialog LLM integration.

## File Structure

```text
research/scripts/economic_news_research/
  cli.py
  embedding.py
  modeling.py
  results.py
  tracking.py
  transformer.py

research/tests/
  test_cli.py
  test_embedding.py
  test_modeling.py
  test_results.py
  test_transformer.py
```

---

### Task 1: Add Transformer Dependencies and Runtime Ignores

**Files:**
- Modify: `pyproject.toml`
- Modify: `research/pyproject.toml`
- Modify: `.gitignore`
- Modify: `research/README.md`

- [ ] **Step 1: Add dependencies to root dev group**

Modify `[dependency-groups].dev` in `pyproject.toml` so it includes:

```toml
  "sentence-transformers>=3.4",
  "torch>=2.6",
  "transformers>=4.48",
```

Keep existing dependencies.

- [ ] **Step 2: Add dependencies to research package**

Modify `[project].dependencies` in `research/pyproject.toml` so it includes:

```toml
  "sentence-transformers>=3.4",
  "torch>=2.6",
  "transformers>=4.48",
```

- [ ] **Step 3: Ignore local model caches**

Append these lines to `.gitignore`:

```gitignore
.cache/
artifacts/hf-cache/*
!artifacts/hf-cache/.gitkeep
```

Create `artifacts/hf-cache/.gitkeep` with an empty file.

- [ ] **Step 4: Update research README commands**

Add these commands to `research/README.md`:

```markdown
uv run python -m economic_news_research.cli train-embedding
uv run python -m economic_news_research.cli train-transformer
uv run python -m economic_news_research.cli compare-models
```

Add a short note:

```markdown
Transformer and embedding model weights are downloaded into a local Hugging Face cache and are not committed.
Unit tests use fake model adapters and do not require network access.
```

- [ ] **Step 5: Lock dependencies**

Run:

```bash
uv lock
```

Expected: lockfile updates successfully.

- [ ] **Step 6: Run checks**

Run:

```bash
uv run ruff check apps packages research
uv run ty check apps packages research
uv run pytest packages apps research/tests -v -W error
```

Expected: all checks pass.

- [ ] **Step 7: Commit**

Run:

```bash
git add pyproject.toml research/pyproject.toml uv.lock .gitignore artifacts/hf-cache/.gitkeep research/README.md
git commit -m "feat: добавить зависимости transformer research"
git push -u origin feature/ml-transformers
```

Expected: commit succeeds and branch is pushed.

---

### Task 2: Generalize Training Results and Timing

**Files:**
- Create: `research/scripts/economic_news_research/results.py`
- Modify: `research/scripts/economic_news_research/modeling.py`
- Modify: `research/scripts/economic_news_research/tracking.py`
- Create: `research/tests/test_results.py`
- Modify: `research/tests/test_modeling.py`

- [ ] **Step 1: Write result tests**

Create `research/tests/test_results.py`:

```python
from economic_news_research.results import measure_prediction_time


def test_measure_prediction_time_returns_predictions_and_average_seconds() -> None:
    predictions, seconds = measure_prediction_time(
        predictor=lambda values: [value.upper() for value in values],
        values=["a", "b", "c"],
    )

    assert predictions == ["A", "B", "C"]
    assert seconds >= 0


def test_measure_prediction_time_handles_empty_values() -> None:
    predictions, seconds = measure_prediction_time(
        predictor=lambda values: [],
        values=[],
    )

    assert predictions == []
    assert seconds == 0
```

- [ ] **Step 2: Update modeling tests for timing and comparison table**

Modify `research/tests/test_modeling.py`:

```python
def test_train_baseline_model_returns_metrics() -> None:
    dataset = load_news_dataset(FIXTURE)
    split = split_news_dataset(dataset, random_state=42)

    result = train_baseline_model(split, random_state=42)

    assert isinstance(result, BaselineTrainingResult)
    assert result.model_name == "tfidf-logreg"
    assert result.validation_metrics.confusion_matrix.shape == (3, 3)
    assert result.best_params["classifier__C"] in {0.1, 1.0, 10.0}
    assert result.inference_seconds_per_sample >= 0
```

Keep existing artifact assertions, including `model_comparison.csv`.

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
uv run pytest research/tests/test_results.py research/tests/test_modeling.py -v
```

Expected: FAIL because `economic_news_research.results` and `inference_seconds_per_sample` do not exist.

- [ ] **Step 4: Implement shared result module**

Create `research/scripts/economic_news_research/results.py`:

```python
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from economic_news_research.metrics import ClassificationMetrics


@dataclass(frozen=True)
class ModelTrainingResult:
    model_name: str
    best_params: dict[str, Any]
    validation_metrics: ClassificationMetrics
    test_metrics: ClassificationMetrics
    estimator: Any
    inference_seconds_per_sample: float


def measure_prediction_time(
    *,
    predictor: Callable[[Sequence[str]], Sequence[str]],
    values: Sequence[str],
) -> tuple[list[str], float]:
    if not values:
        return [], 0.0

    started_at = perf_counter()
    predictions = list(predictor(values))
    elapsed = perf_counter() - started_at
    return predictions, elapsed / len(values)
```

- [ ] **Step 5: Adapt baseline result**

Modify `research/scripts/economic_news_research/modeling.py`:

```python
from economic_news_research.results import ModelTrainingResult, measure_prediction_time

BaselineTrainingResult = ModelTrainingResult
```

In `train_baseline_model`, replace direct test prediction timing with:

```python
validation_predictions = best_estimator.predict(split.validation["text"]).tolist()
test_predictions, inference_seconds_per_sample = measure_prediction_time(
    predictor=lambda values: best_estimator.predict(values).tolist(),
    values=split.test["text"].tolist(),
)
```

Pass `inference_seconds_per_sample=inference_seconds_per_sample` to `BaselineTrainingResult`.

- [ ] **Step 6: Update tracking comparison table**

Modify `_build_comparison_frame` in `tracking.py` so each row includes:

```python
"inference_seconds_per_sample": float(result.inference_seconds_per_sample),
```

- [ ] **Step 7: Run checks**

Run:

```bash
uv run pytest research/tests/test_results.py research/tests/test_modeling.py -v -W error
uv run ruff check research
uv run ty check research
```

Expected: all pass.

- [ ] **Step 8: Commit**

Run:

```bash
git add research/scripts/economic_news_research/results.py research/scripts/economic_news_research/modeling.py research/scripts/economic_news_research/tracking.py research/tests/test_results.py research/tests/test_modeling.py
git commit -m "feat: обобщить результат обучения моделей"
git push
```

Expected: commit succeeds and branch is pushed.

---

### Task 3: Add Embedding Classifier

**Files:**
- Create: `research/scripts/economic_news_research/embedding.py`
- Create: `research/tests/test_embedding.py`

- [ ] **Step 1: Write embedding tests**

Create `research/tests/test_embedding.py`:

```python
from pathlib import Path

import numpy as np

from economic_news_research.data import load_news_dataset, split_news_dataset
from economic_news_research.embedding import (
    EmbeddingTrainingResult,
    train_embedding_classifier,
)

FIXTURE = Path(__file__).parent / "fixtures" / "news_impact_sample.csv"


class FakeEmbedder:
    def encode(self, texts: list[str]) -> np.ndarray:
        rows: list[list[float]] = []
        for text in texts:
            lowered = text.lower()
            rows.append(
                [
                    float("rise" in lowered or "gain" in lowered or "strong" in lowered),
                    float("fall" in lowered or "decline" in lowered or "drops" in lowered),
                    float("stable" in lowered or "unchanged" in lowered or "wait" in lowered),
                ]
            )
        return np.array(rows, dtype=float)


def test_train_embedding_classifier_returns_metrics() -> None:
    dataset = load_news_dataset(FIXTURE)
    split = split_news_dataset(dataset, random_state=42)

    result = train_embedding_classifier(
        split,
        embedder=FakeEmbedder(),
        random_state=42,
    )

    assert isinstance(result, EmbeddingTrainingResult)
    assert result.model_name == "embedding-logreg"
    assert result.validation_metrics.confusion_matrix.shape == (3, 3)
    assert result.test_metrics.confusion_matrix.shape == (3, 3)
    assert result.inference_seconds_per_sample >= 0
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest research/tests/test_embedding.py -v
```

Expected: FAIL because `economic_news_research.embedding` does not exist.

- [ ] **Step 3: Implement embedding module**

Create `research/scripts/economic_news_research/embedding.py`:

```python
from typing import Protocol

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV

from economic_news_research.data import DatasetSplit
from economic_news_research.metrics import compute_classification_metrics
from economic_news_research.modeling import IMPACT_LABELS, _safe_cv
from economic_news_research.results import ModelTrainingResult, measure_prediction_time

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EmbeddingTrainingResult = ModelTrainingResult


class TextEmbedder(Protocol):
    def encode(self, texts: list[str]) -> np.ndarray: ...


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        self.model_name = model_name
        self._model = None

    def encode(self, texts: list[str]) -> np.ndarray:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        embeddings = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return np.asarray(embeddings)


def train_embedding_classifier(
    split: DatasetSplit,
    *,
    embedder: TextEmbedder | None = None,
    random_state: int,
) -> EmbeddingTrainingResult:
    active_embedder = embedder or SentenceTransformerEmbedder()
    train_embeddings = active_embedder.encode(split.train["text"].tolist())
    validation_embeddings = active_embedder.encode(split.validation["text"].tolist())
    test_texts = split.test["text"].tolist()

    search = GridSearchCV(
        estimator=LogisticRegression(max_iter=1000, class_weight="balanced", random_state=random_state),
        param_grid={"C": [0.1, 1.0, 10.0]},
        scoring="f1_macro",
        cv=_safe_cv(split.train["impact"].tolist(), random_state=random_state),
        n_jobs=1,
    )
    search.fit(train_embeddings, split.train["impact"])

    validation_predictions = search.best_estimator_.predict(validation_embeddings).tolist()
    test_predictions, inference_seconds_per_sample = measure_prediction_time(
        predictor=lambda values: search.best_estimator_.predict(
            active_embedder.encode(list(values))
        ).tolist(),
        values=test_texts,
    )

    return EmbeddingTrainingResult(
        model_name="embedding-logreg",
        best_params=dict(search.best_params_),
        validation_metrics=compute_classification_metrics(
            y_true=split.validation["impact"].tolist(),
            y_pred=validation_predictions,
            labels=IMPACT_LABELS,
        ),
        test_metrics=compute_classification_metrics(
            y_true=split.test["impact"].tolist(),
            y_pred=test_predictions,
            labels=IMPACT_LABELS,
        ),
        estimator=search.best_estimator_,
        inference_seconds_per_sample=inference_seconds_per_sample,
    )
```

- [ ] **Step 4: Run checks**

Run:

```bash
uv run pytest research/tests/test_embedding.py -v -W error
uv run ruff check research
uv run ty check research
```

Expected: all pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add research/scripts/economic_news_research/embedding.py research/tests/test_embedding.py
git commit -m "feat: добавить embedding classifier"
git push
```

Expected: commit succeeds and branch is pushed.

---

### Task 4: Add Tiny Transformer Orchestration

**Files:**
- Create: `research/scripts/economic_news_research/transformer.py`
- Create: `research/tests/test_transformer.py`

- [ ] **Step 1: Write transformer tests**

Create `research/tests/test_transformer.py`:

```python
from pathlib import Path

from economic_news_research.data import load_news_dataset, split_news_dataset
from economic_news_research.transformer import (
    TransformerTrainingResult,
    train_tiny_transformer_classifier,
)

FIXTURE = Path(__file__).parent / "fixtures" / "news_impact_sample.csv"


class FakeTinyTransformerTrainer:
    best_params = {"model_name": "fake-tiny-transformer", "epochs": 1}

    def fit(self, train_texts: list[str], train_labels: list[str], validation_texts: list[str], validation_labels: list[str]) -> None:
        self.majority_label = max(set(train_labels), key=train_labels.count)

    def predict(self, texts: list[str]) -> list[str]:
        predictions: list[str] = []
        for text in texts:
            lowered = text.lower()
            if "rise" in lowered or "gain" in lowered or "strong" in lowered:
                predictions.append("positive")
            elif "fall" in lowered or "decline" in lowered or "drops" in lowered:
                predictions.append("negative")
            else:
                predictions.append("neutral")
        return predictions


def test_train_tiny_transformer_classifier_returns_metrics_without_downloads() -> None:
    dataset = load_news_dataset(FIXTURE)
    split = split_news_dataset(dataset, random_state=42)

    result = train_tiny_transformer_classifier(
        split,
        trainer=FakeTinyTransformerTrainer(),
        random_state=42,
    )

    assert isinstance(result, TransformerTrainingResult)
    assert result.model_name == "tiny-transformer-classifier"
    assert result.validation_metrics.confusion_matrix.shape == (3, 3)
    assert result.test_metrics.confusion_matrix.shape == (3, 3)
    assert result.best_params["model_name"] == "fake-tiny-transformer"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest research/tests/test_transformer.py -v
```

Expected: FAIL because `economic_news_research.transformer` does not exist.

- [ ] **Step 3: Implement transformer orchestration**

Create `research/scripts/economic_news_research/transformer.py`:

```python
from dataclasses import dataclass
from typing import Protocol

from economic_news_research.data import DatasetSplit
from economic_news_research.metrics import compute_classification_metrics
from economic_news_research.modeling import IMPACT_LABELS
from economic_news_research.results import ModelTrainingResult, measure_prediction_time

DEFAULT_TINY_TRANSFORMER_MODEL = "cointegrated/rubert-tiny2"
TransformerTrainingResult = ModelTrainingResult


class TinyTransformerTrainer(Protocol):
    best_params: dict[str, object]

    def fit(
        self,
        train_texts: list[str],
        train_labels: list[str],
        validation_texts: list[str],
        validation_labels: list[str],
    ) -> None: ...

    def predict(self, texts: list[str]) -> list[str]: ...


@dataclass(frozen=True)
class TinyTransformerConfig:
    model_name: str = DEFAULT_TINY_TRANSFORMER_MODEL
    epochs: int = 1
    batch_size: int = 4
    learning_rate: float = 2e-5


class HuggingFaceTinyTransformerTrainer:
    def __init__(self, config: TinyTransformerConfig | None = None) -> None:
        self.config = config or TinyTransformerConfig()
        self.best_params = {
            "model_name": self.config.model_name,
            "epochs": self.config.epochs,
            "batch_size": self.config.batch_size,
            "learning_rate": self.config.learning_rate,
        }
        self._labels = IMPACT_LABELS
        self._pipeline = None

    def fit(
        self,
        train_texts: list[str],
        train_labels: list[str],
        validation_texts: list[str],
        validation_labels: list[str],
    ) -> None:
        from transformers import pipeline

        self._pipeline = pipeline(
            "text-classification",
            model=self.config.model_name,
            tokenizer=self.config.model_name,
            top_k=None,
        )

    def predict(self, texts: list[str]) -> list[str]:
        if self._pipeline is None:
            raise RuntimeError("Tiny transformer trainer must be fitted before prediction")

        raw_predictions = self._pipeline(texts)
        predictions: list[str] = []
        for prediction_group in raw_predictions:
            best = max(prediction_group, key=lambda item: item["score"])
            label = str(best["label"]).lower()
            predictions.append(label if label in IMPACT_LABELS else "neutral")
        return predictions


def train_tiny_transformer_classifier(
    split: DatasetSplit,
    *,
    trainer: TinyTransformerTrainer | None = None,
    random_state: int,
) -> TransformerTrainingResult:
    active_trainer = trainer or HuggingFaceTinyTransformerTrainer()
    active_trainer.fit(
        train_texts=split.train["text"].tolist(),
        train_labels=split.train["impact"].tolist(),
        validation_texts=split.validation["text"].tolist(),
        validation_labels=split.validation["impact"].tolist(),
    )

    validation_predictions = active_trainer.predict(split.validation["text"].tolist())
    test_predictions, inference_seconds_per_sample = measure_prediction_time(
        predictor=active_trainer.predict,
        values=split.test["text"].tolist(),
    )

    return TransformerTrainingResult(
        model_name="tiny-transformer-classifier",
        best_params=dict(active_trainer.best_params),
        validation_metrics=compute_classification_metrics(
            y_true=split.validation["impact"].tolist(),
            y_pred=validation_predictions,
            labels=IMPACT_LABELS,
        ),
        test_metrics=compute_classification_metrics(
            y_true=split.test["impact"].tolist(),
            y_pred=test_predictions,
            labels=IMPACT_LABELS,
        ),
        estimator=active_trainer,
        inference_seconds_per_sample=inference_seconds_per_sample,
    )
```

- [ ] **Step 4: Run checks**

Run:

```bash
uv run pytest research/tests/test_transformer.py -v -W error
uv run ruff check research
uv run ty check research
```

Expected: all pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add research/scripts/economic_news_research/transformer.py research/tests/test_transformer.py
git commit -m "feat: добавить tiny transformer orchestration"
git push
```

Expected: commit succeeds and branch is pushed.

---

### Task 5: Add Generic Artifact Export and Model Comparison

**Files:**
- Modify: `research/scripts/economic_news_research/tracking.py`
- Modify: `research/tests/test_modeling.py`
- Create: `research/tests/test_tracking.py`

- [ ] **Step 1: Write tracking tests**

Create `research/tests/test_tracking.py`:

```python
from pathlib import Path

import numpy as np
import pandas as pd

from economic_news_research.data import load_news_dataset, split_news_dataset
from economic_news_research.embedding import train_embedding_classifier
from economic_news_research.modeling import train_baseline_model
from economic_news_research.tracking import save_model_artifacts, write_model_comparison

FIXTURE = Path(__file__).parent / "fixtures" / "news_impact_sample.csv"


class FakeEmbedder:
    def encode(self, texts: list[str]) -> np.ndarray:
        rows: list[list[float]] = []
        for text in texts:
            lowered = text.lower()
            rows.append(
                [
                    float("rise" in lowered or "gain" in lowered or "strong" in lowered),
                    float("fall" in lowered or "decline" in lowered or "drops" in lowered),
                    float("stable" in lowered or "unchanged" in lowered or "wait" in lowered),
                ]
            )
        return np.array(rows, dtype=float)


def test_write_model_comparison_combines_multiple_results(tmp_path: Path) -> None:
    dataset = load_news_dataset(FIXTURE)
    split = split_news_dataset(dataset, random_state=42)
    baseline = train_baseline_model(split, random_state=42)
    embedding = train_embedding_classifier(split, embedder=FakeEmbedder(), random_state=42)

    comparison_path = write_model_comparison(
        [baseline, embedding],
        output_path=tmp_path / "model_comparison.csv",
    )

    comparison = pd.read_csv(comparison_path)
    assert comparison["model_name"].tolist() == ["tfidf-logreg", "embedding-logreg"]
    assert "inference_seconds_per_sample" in comparison.columns


def test_save_model_artifacts_writes_model_named_files(tmp_path: Path) -> None:
    dataset = load_news_dataset(FIXTURE)
    split = split_news_dataset(dataset, random_state=42)
    result = train_baseline_model(split, random_state=42)

    save_model_artifacts(result, output_dir=tmp_path)

    assert (tmp_path / "tfidf-logreg.joblib").exists()
    assert (tmp_path / "tfidf-logreg_metrics.json").exists()
    assert (tmp_path / "tfidf-logreg_confusion_matrix.csv").exists()
    assert (tmp_path / "model_comparison.csv").exists()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest research/tests/test_tracking.py -v
```

Expected: FAIL because `save_model_artifacts` and `write_model_comparison` do not exist.

- [ ] **Step 3: Refactor tracking exports**

Modify `tracking.py`:

```python
def save_model_artifacts(result: ModelTrainingResult, *, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(result.estimator, output_dir / f"{result.model_name}.joblib")
    (output_dir / f"{result.model_name}_metrics.json").write_text(
        json.dumps(_serialize_model_metrics(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    confusion_matrix = pd.DataFrame(
        result.test_metrics.confusion_matrix,
        index=pd.Index(IMPACT_LABELS),
        columns=pd.Index(IMPACT_LABELS),
    )
    confusion_matrix.to_csv(output_dir / f"{result.model_name}_confusion_matrix.csv")
    write_model_comparison([result], output_path=output_dir / "model_comparison.csv")


def save_baseline_artifacts(result: ModelTrainingResult, *, output_dir: Path) -> None:
    save_model_artifacts(result, output_dir=output_dir)


def write_model_comparison(
    results: list[ModelTrainingResult],
    *,
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([_build_comparison_row(result) for result in results]).to_csv(
        output_path,
        index=False,
    )
    return output_path
```

Rename `_serialize_baseline_metrics` to `_serialize_model_metrics` and `_build_comparison_frame` to `_build_comparison_row`.

- [ ] **Step 4: Run checks**

Run:

```bash
uv run pytest research/tests/test_tracking.py research/tests/test_modeling.py -v -W error
uv run ruff check research
uv run ty check research
```

Expected: all pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add research/scripts/economic_news_research/tracking.py research/tests/test_tracking.py research/tests/test_modeling.py
git commit -m "feat: добавить общее сравнение моделей"
git push
```

Expected: commit succeeds and branch is pushed.

---

### Task 6: Extend Research CLI

**Files:**
- Modify: `research/scripts/economic_news_research/cli.py`
- Modify: `research/tests/test_cli.py`

- [ ] **Step 1: Add CLI tests**

Append to `research/tests/test_cli.py`:

```python
import numpy as np
import pandas as pd


class FakeEmbedder:
    def encode(self, texts: list[str]) -> np.ndarray:
        rows: list[list[float]] = []
        for text in texts:
            lowered = text.lower()
            rows.append(
                [
                    float("rise" in lowered or "gain" in lowered or "strong" in lowered),
                    float("fall" in lowered or "decline" in lowered or "drops" in lowered),
                    float("stable" in lowered or "unchanged" in lowered or "wait" in lowered),
                ]
            )
        return np.array(rows, dtype=float)


class FakeTinyTransformerTrainer:
    best_params = {"model_name": "fake-tiny-transformer", "epochs": 1}

    def fit(
        self,
        train_texts: list[str],
        train_labels: list[str],
        validation_texts: list[str],
        validation_labels: list[str],
    ) -> None:
        self.majority_label = max(set(train_labels), key=train_labels.count)

    def predict(self, texts: list[str]) -> list[str]:
        return ["neutral" for _ in texts]


def test_run_train_embedding_writes_model_artifacts(tmp_path: Path) -> None:
    run_train_embedding(
        dataset_path=FIXTURE,
        output_dir=tmp_path,
        random_state=42,
        embedder=FakeEmbedder(),
    )

    assert (tmp_path / "embedding-logreg.joblib").exists()
    assert (tmp_path / "model_comparison.csv").exists()


def test_run_train_transformer_writes_model_artifacts(tmp_path: Path) -> None:
    run_train_transformer(
        dataset_path=FIXTURE,
        output_dir=tmp_path,
        random_state=42,
        trainer=FakeTinyTransformerTrainer(),
    )

    assert (tmp_path / "tiny-transformer-classifier.joblib").exists()
    assert (tmp_path / "model_comparison.csv").exists()


def test_run_compare_models_combines_existing_comparisons(tmp_path: Path) -> None:
    baseline_dir = tmp_path / "baseline"
    embedding_dir = tmp_path / "embedding"
    baseline_dir.mkdir()
    embedding_dir.mkdir()
    pd.DataFrame([{"model_name": "tfidf-logreg", "test_macro_f1": 0.4}]).to_csv(
        baseline_dir / "model_comparison.csv",
        index=False,
    )
    pd.DataFrame([{"model_name": "embedding-logreg", "test_macro_f1": 0.5}]).to_csv(
        embedding_dir / "model_comparison.csv",
        index=False,
    )

    output_path = run_compare_models(
        comparison_paths=[
            baseline_dir / "model_comparison.csv",
            embedding_dir / "model_comparison.csv",
        ],
        output_path=tmp_path / "model_comparison.csv",
    )

    comparison = pd.read_csv(output_path)
    assert comparison["model_name"].tolist() == ["tfidf-logreg", "embedding-logreg"]
```

Also update the import line:

```python
from economic_news_research.cli import (
    run_eda,
    run_compare_models,
    run_train_baseline,
    run_train_embedding,
    run_train_transformer,
    run_validate,
)
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest research/tests/test_cli.py -v
```

Expected: FAIL because CLI functions do not exist.

- [ ] **Step 3: Implement CLI functions**

Modify `cli.py`:

```python
import pandas as pd

from economic_news_research.embedding import TextEmbedder, train_embedding_classifier
from economic_news_research.transformer import TinyTransformerTrainer, train_tiny_transformer_classifier
from economic_news_research.tracking import save_model_artifacts
```

Add:

```python
def run_train_embedding(
    *,
    dataset_path: Path,
    output_dir: Path,
    random_state: int,
    embedder: TextEmbedder | None = None,
) -> None:
    dataset = load_news_dataset(dataset_path)
    split = split_news_dataset(dataset, random_state=random_state)
    result = train_embedding_classifier(split, embedder=embedder, random_state=random_state)
    save_model_artifacts(result, output_dir=output_dir)
    log_baseline_to_mlflow(result, artifact_dir=output_dir)


def run_train_transformer(
    *,
    dataset_path: Path,
    output_dir: Path,
    random_state: int,
    trainer: TinyTransformerTrainer | None = None,
) -> None:
    dataset = load_news_dataset(dataset_path)
    split = split_news_dataset(dataset, random_state=random_state)
    result = train_tiny_transformer_classifier(split, trainer=trainer, random_state=random_state)
    save_model_artifacts(result, output_dir=output_dir)
    log_baseline_to_mlflow(result, artifact_dir=output_dir)


def run_compare_models(*, comparison_paths: list[Path], output_path: Path) -> Path:
    frames = [pd.read_csv(path) for path in comparison_paths if path.exists()]
    if not frames:
        raise FileNotFoundError("No model comparison files found")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.concat(frames, ignore_index=True).to_csv(output_path, index=False)
    return output_path
```

Add argparse subcommands:

```python
embedding_parser = subparsers.add_parser("train-embedding")
embedding_parser.add_argument("--dataset", type=Path, default=DEFAULT_RAW_DATASET)
embedding_parser.add_argument("--output-dir", type=Path, default=MODELS_DIR / "embedding")
embedding_parser.add_argument("--random-state", type=int, default=42)

transformer_parser = subparsers.add_parser("train-transformer")
transformer_parser.add_argument("--dataset", type=Path, default=DEFAULT_RAW_DATASET)
transformer_parser.add_argument("--output-dir", type=Path, default=MODELS_DIR / "transformer")
transformer_parser.add_argument("--random-state", type=int, default=42)

compare_parser = subparsers.add_parser("compare-models")
compare_parser.add_argument(
    "--comparison",
    action="append",
    type=Path,
    default=[
        MODELS_DIR / "baseline" / "model_comparison.csv",
        MODELS_DIR / "embedding" / "model_comparison.csv",
        MODELS_DIR / "transformer" / "model_comparison.csv",
    ],
)
compare_parser.add_argument("--output-path", type=Path, default=MODELS_DIR / "model_comparison.csv")
```

Handle command output:

```python
if args.command == "train-embedding":
    run_train_embedding(
        dataset_path=args.dataset,
        output_dir=args.output_dir,
        random_state=args.random_state,
    )
    print(f"embedding_output_dir={args.output_dir}")
    return

if args.command == "train-transformer":
    run_train_transformer(
        dataset_path=args.dataset,
        output_dir=args.output_dir,
        random_state=args.random_state,
    )
    print(f"transformer_output_dir={args.output_dir}")
    return

if args.command == "compare-models":
    output_path = run_compare_models(
        comparison_paths=args.comparison,
        output_path=args.output_path,
    )
    print(f"comparison_path={output_path}")
    return
```

- [ ] **Step 4: Run checks**

Run:

```bash
uv run pytest research/tests/test_cli.py -v -W error
uv run ruff check research
uv run ty check research
```

Expected: all pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add research/scripts/economic_news_research/cli.py research/tests/test_cli.py
git commit -m "feat: добавить cli для transformer моделей"
git push
```

Expected: commit succeeds and branch is pushed.

---

### Task 7: Final Verification and PR

**Files:**
- Modify if needed: `research/README.md`

- [ ] **Step 1: Run full checks**

Run:

```bash
uv run ruff format apps packages research
uv run ruff check apps packages research
uv run ty check apps packages research
uv run pytest packages apps research/tests -v -W error
```

Expected: all pass.

- [ ] **Step 2: Check runtime artifacts**

Run:

```bash
find . -maxdepth 2 -name "mlruns" -o -name "mlflow.db"
git status --short --ignored artifacts research/reports
```

Expected:

- no root `mlruns` or `mlflow.db`;
- only ignored runtime files under `artifacts/` if tests created MLflow data;
- no untracked generated reports.

- [ ] **Step 3: Final review**

Dispatch final code review for `dev..feature/ml-transformers`.

Expected: APPROVED or fix requested issues before PR.

- [ ] **Step 4: Create PR**

Run:

```bash
gh pr create --base dev --head feature/ml-transformers --title "feat: добавить transformer research модели" --body "## Summary
- Added shared model result contract with inference timing.
- Added embedding classifier and tiny transformer research orchestration.
- Extended model comparison artifacts and CLI commands.

## Test Plan
- uv run ruff check apps packages research
- uv run ty check apps packages research
- uv run pytest packages apps research/tests -v -W error"
```

Expected: GitHub PR is created.
