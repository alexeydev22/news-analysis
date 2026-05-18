# ML Quality A-B-C Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Improve economic-news impact classification quality in three ordered phases: stronger classic ML baseline, cleaner weak labels, then a modern transformer-classifier upgrade.

**Architecture:** Keep the production analysis contract stable while improving the research/training pipeline behind it. Phase A changes sampling, TF-IDF search space, and diagnostics; Phase B isolates weak-labeling and text cleanup into focused modules; Phase C upgrades the current tiny transformer path with an English-friendly, class-balanced training loop after labels are less noisy.

**Tech Stack:** Python 3.12, scikit-learn, pandas, joblib, Hugging Face transformers, FastAPI analysis worker, React ML report UI, Docker Compose.

---

## Context And Problem

Current metrics are low for structural reasons:

- `reports/ml/model-report.json` shows `row_count=50000`, but `apps/analysis-service/src/analysis_service/main/settings.py` limits classic training to `ml_train_max_rows=3000` and transformer training to `ml_transformer_max_rows=1000`.
- `research/scripts/economic_news_research/data.py` weak-labels FNSPID rows from keyword dictionaries when the raw CSV has no `impact`.
- Class distribution is heavily skewed toward `positive`; current transformer predicts only `positive`, giving misleading `accuracy=0.700` and poor `macro_f1=0.275`.
- `research/scripts/economic_news_research/modeling.py` caps TF-IDF at only `1000` features, too small for long financial news articles.

External references to use while implementing:

- scikit-learn `TfidfVectorizer` supports `max_df`, `min_df`, `max_features`, `ngram_range`, and `sublinear_tf`.
- scikit-learn `LogisticRegression(class_weight="balanced")` adjusts class weights inversely to observed class frequencies.
- Hugging Face SetFit is a lightweight prompt-free path for sentence-transformer fine-tuning, useful as a later alternative if the full transformer path stays too slow.

## File Structure

Modify:

- `apps/analysis-service/src/analysis_service/main/settings.py`  
  Owns training row-count defaults.
- `.env.example` and `deploy/compose.yaml`  
  Own local and Docker training caps.
- `apps/analysis-service/src/analysis_service/workers/tasks.py`  
  Owns ML report orchestration and stale transformer artifact handling.
- `research/scripts/economic_news_research/modeling.py`  
  Owns TF-IDF + LogisticRegression baseline.
- `research/scripts/economic_news_research/metrics.py`  
  Owns per-class metrics and macro metrics.
- `research/scripts/economic_news_research/reporting.py`  
  Owns report JSON diagnostics shown in the UI.
- `research/scripts/economic_news_research/data.py`  
  Owns dataset validation and adaptation.
- `research/scripts/economic_news_research/transformer.py`  
  Owns transformer training.
- `frontend/web/src/components/MlReportPanel.tsx`  
  Owns ML report display.
- `frontend/web/src/app/types.ts` and `frontend/web/src/test/fixtures.ts`  
  Own frontend report types and test fixtures.

Create:

- `research/scripts/economic_news_research/text_normalization.py`  
  Focused text cleanup for FNSPID/Nasdaq boilerplate.
- `research/scripts/economic_news_research/weak_labeling.py`  
  Focused weak-label inference with score/margin metadata.
- `research/tests/test_text_normalization.py`
- `research/tests/test_weak_labeling.py`

---

### Task 1: Phase A Training Caps And Honest Report Metadata

**Files:**

- Modify: `apps/analysis-service/src/analysis_service/main/settings.py`
- Modify: `.env.example`
- Modify: `deploy/compose.yaml`
- Modify: `apps/analysis-service/src/analysis_service/workers/tasks.py`
- Modify: `research/scripts/economic_news_research/cli.py`
- Modify: `research/scripts/economic_news_research/reporting.py`
- Test: `apps/analysis-service/tests/test_container.py`
- Test: `research/tests/test_cli.py`
- Test: `research/tests/test_reporting.py`

- [x] **Step 1: Write failing settings test for larger default caps**

Add this test to `apps/analysis-service/tests/test_container.py`:

```python
from analysis_service.main.settings import AnalysisServiceSettings


def test_analysis_settings_use_larger_training_caps_by_default() -> None:
    settings = AnalysisServiceSettings()

    assert settings.ml_train_max_rows == 20_000
    assert settings.ml_transformer_max_rows == 5_000
```

- [x] **Step 2: Run the settings test and verify it fails**

Run:

```bash
uv run pytest apps/analysis-service/tests/test_container.py::test_analysis_settings_use_larger_training_caps_by_default -q
```

Expected: FAIL because current defaults are `3000` and `1000`.

- [x] **Step 3: Update analysis settings defaults**

In `apps/analysis-service/src/analysis_service/main/settings.py`, change:

```python
ml_train_max_rows: int | None = Field(default=20_000, ge=100)
ml_transformer_max_rows: int | None = Field(default=5_000, ge=100)
```

- [x] **Step 4: Update local and Docker env defaults**

In `.env.example`, set:

```dotenv
ANALYSIS_ML_TRAIN_MAX_ROWS=20000
ANALYSIS_ML_TRANSFORMER_MAX_ROWS=5000
```

In `deploy/compose.yaml`, update both `analysis-service` and `analysis-worker` sections:

```yaml
ANALYSIS_ML_TRAIN_MAX_ROWS: "${ANALYSIS_ML_TRAIN_MAX_ROWS:-20000}"
ANALYSIS_ML_TRANSFORMER_MAX_ROWS: "${ANALYSIS_ML_TRANSFORMER_MAX_ROWS:-5000}"
```

- [x] **Step 5: Write failing test for training metadata in report**

Extend `research/tests/test_cli.py` with a fake training function test:

```python
def test_run_build_model_report_includes_training_limits(tmp_path: Path) -> None:
    dataset_path = FIXTURE
    comparison_path = tmp_path / "model_comparison.csv"
    comparison_path.write_text(
        "model_name,validation_accuracy,validation_macro_f1,test_accuracy,test_macro_f1,inference_seconds_per_sample\n"
        "tfidf-logreg,0.8,0.7,0.81,0.72,0.001\n",
        encoding="utf-8",
    )

    report_path = run_build_model_report(
        dataset_path=dataset_path,
        comparison_path=comparison_path,
        model_dirs=[],
        output_path=tmp_path / "model-report.json",
        training_limits={"classic_max_rows": 20_000, "transformer_max_rows": 5_000},
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["training"]["classic_max_rows"] == 20_000
    assert report["training"]["transformer_max_rows"] == 5_000
```

Add imports if missing:

```python
import json
from pathlib import Path
```

- [x] **Step 6: Run the metadata test and verify it fails**

Run:

```bash
uv run pytest research/tests/test_cli.py::test_run_build_model_report_includes_training_limits -q
```

Expected: FAIL because `run_build_model_report` does not accept `training_limits`.

- [x] **Step 7: Add `training_limits` through CLI/reporting**

In `research/scripts/economic_news_research/cli.py`, change `run_build_model_report` signature:

```python
def run_build_model_report(
    *,
    dataset_path: Path,
    comparison_path: Path,
    model_dirs: list[Path],
    output_path: Path,
    training_limits: dict[str, int | None] | None = None,
) -> Path:
    report = build_model_report(
        dataset_path=dataset_path,
        comparison_path=comparison_path,
        model_dirs=model_dirs,
        training_limits=training_limits,
    )
    return save_model_report(report, output_path=output_path)
```

In `research/scripts/economic_news_research/reporting.py`, change `build_model_report` signature and output:

```python
def build_model_report(
    *,
    dataset_path: Path,
    comparison_path: Path,
    model_dirs: list[Path],
    training_limits: dict[str, int | None] | None = None,
) -> dict[str, Any]:
    dataset = load_news_dataset(dataset_path)
    comparison = pd.read_csv(comparison_path)
    models = [
        _build_model_section(row=row, model_dirs=model_dirs)
        for row in comparison.to_dict(orient="records")
    ]
    return {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "dataset": {
            "path": str(dataset_path),
            "row_count": int(len(dataset)),
            "class_distribution": _class_distribution(dataset),
        },
        "training": training_limits or {},
        "models": models,
        "best_model": _best_model(models),
        "top_features": _top_features(model_dirs=model_dirs),
    }
```

- [x] **Step 8: Pass training limits from worker**

In `apps/analysis-service/src/analysis_service/workers/tasks.py`, update the report-building call to pass both training caps:

```python
report_path = run_build_model_report(
    dataset_path=selected_dataset_path,
    comparison_path=settings.ml_comparison_path,
    model_dirs=[
        settings.tfidf_artifact_path.parent,
        settings.embedding_artifact_path.parent,
        settings.transformer_artifact_path.parent,
    ],
    output_path=settings.ml_report_output_path,
    training_limits={
        "classic_max_rows": settings.ml_train_max_rows,
        "transformer_max_rows": settings.ml_transformer_max_rows,
    },
)
```

- [x] **Step 9: Run tests for Task 1**

Run:

```bash
uv run pytest apps/analysis-service/tests/test_container.py research/tests/test_cli.py research/tests/test_reporting.py -q
```

Expected: PASS.

- [x] **Step 10: Commit Task 1**

```bash
git add .env.example deploy/compose.yaml apps/analysis-service/src/analysis_service/main/settings.py apps/analysis-service/src/analysis_service/workers/tasks.py research/scripts/economic_news_research/cli.py research/scripts/economic_news_research/reporting.py apps/analysis-service/tests/test_container.py research/tests/test_cli.py research/tests/test_reporting.py
git commit -m "feat: увеличить выборку обучения для ML-отчета"
```

---

### Task 2: Phase A Stronger TF-IDF Baseline

**Files:**

- Modify: `research/scripts/economic_news_research/modeling.py`
- Test: `research/tests/test_modeling.py`

- [x] **Step 1: Write failing test for stronger TF-IDF vectorizer defaults**

Add to `research/tests/test_modeling.py`:

```python
def test_build_baseline_pipeline_uses_richer_tfidf_defaults() -> None:
    pipeline = build_baseline_pipeline(
        max_features=20_000,
        c_value=3.0,
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.95,
        sublinear_tf=True,
    )

    vectorizer = pipeline.named_steps["tfidf"]
    classifier = pipeline.named_steps["classifier"]

    assert vectorizer.max_features == 20_000
    assert vectorizer.ngram_range == (1, 2)
    assert vectorizer.min_df == 2
    assert vectorizer.max_df == 0.95
    assert vectorizer.sublinear_tf is True
    assert classifier.class_weight == "balanced"
```

- [x] **Step 2: Write failing test for expanded parameter grid**

Add to `research/tests/test_modeling.py`:

```python
def test_baseline_param_grid_contains_large_vocabularies() -> None:
    grid = baseline_param_grid()

    assert grid["tfidf__max_features"] == [5_000, 20_000, 50_000]
    assert grid["tfidf__min_df"] == [2, 5]
    assert grid["tfidf__max_df"] == [0.9, 0.95]
    assert grid["tfidf__sublinear_tf"] == [True]
    assert grid["tfidf__ngram_range"] == [(1, 1), (1, 2)]
```

- [x] **Step 3: Run tests and verify they fail**

Run:

```bash
uv run pytest research/tests/test_modeling.py::test_build_baseline_pipeline_uses_richer_tfidf_defaults research/tests/test_modeling.py::test_baseline_param_grid_contains_large_vocabularies -q
```

Expected: FAIL because `build_baseline_pipeline` lacks these params and `baseline_param_grid` does not exist.

- [x] **Step 4: Update `build_baseline_pipeline`**

In `research/scripts/economic_news_research/modeling.py`, replace the function with:

```python
def build_baseline_pipeline(
    max_features: int,
    c_value: float,
    ngram_range: tuple[int, int],
    min_df: int = 2,
    max_df: float = 0.95,
    sublinear_tf: bool = True,
) -> Pipeline:
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    max_features=max_features,
                    ngram_range=ngram_range,
                    min_df=min_df,
                    max_df=max_df,
                    sublinear_tf=sublinear_tf,
                    strip_accents="unicode",
                    lowercase=True,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    C=c_value,
                    max_iter=1500,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ],
    )
```

- [x] **Step 5: Add `baseline_param_grid` and use it in GridSearchCV**

In `research/scripts/economic_news_research/modeling.py`, add:

```python
def baseline_param_grid() -> dict[str, list[object]]:
    return {
        "tfidf__max_features": [5_000, 20_000, 50_000],
        "tfidf__ngram_range": [(1, 1), (1, 2)],
        "tfidf__min_df": [2, 5],
        "tfidf__max_df": [0.9, 0.95],
        "tfidf__sublinear_tf": [True],
        "classifier__C": [0.3, 1.0, 3.0, 10.0],
    }
```

Then change the `GridSearchCV` call:

```python
search = GridSearchCV(
    estimator=estimator,
    param_grid=baseline_param_grid(),
    scoring="f1_macro",
    cv=safe_cv(split.train["impact"].tolist(), random_state=random_state),
    n_jobs=1,
)
```

- [x] **Step 6: Update `_build_training_pipeline`**

In `research/scripts/economic_news_research/modeling.py`, change:

```python
pipeline = build_baseline_pipeline(
    max_features=20_000,
    c_value=1.0,
    ngram_range=(1, 2),
    min_df=2,
    max_df=0.95,
    sublinear_tf=True,
)
```

- [x] **Step 7: Run modeling tests**

Run:

```bash
uv run pytest research/tests/test_modeling.py -q
```

Expected: PASS.

- [x] **Step 8: Run a fast smoke training on fixture**

Run:

```bash
uv run python -m economic_news_research.cli train-baseline --dataset research/tests/fixtures/news_impact.csv --output-dir /private/tmp/tfidf-smoke --max-rows 30
```

Expected output contains:

```text
baseline_output_dir=/private/tmp/tfidf-smoke
```

- [x] **Step 9: Commit Task 2**

```bash
git add research/scripts/economic_news_research/modeling.py research/tests/test_modeling.py
git commit -m "feat: усилить tfidf baseline для новостей"
```

---

### Task 3: Phase A Per-Class Diagnostics In Report And UI

**Files:**

- Modify: `research/scripts/economic_news_research/metrics.py`
- Modify: `research/scripts/economic_news_research/results.py`
- Modify: `research/scripts/economic_news_research/tracking.py`
- Modify: `research/scripts/economic_news_research/reporting.py`
- Modify: `packages/contracts/src/economic_news_contracts/analysis.py`
- Modify: `frontend/web/src/app/types.ts`
- Modify: `frontend/web/src/components/MlReportPanel.tsx`
- Modify: `frontend/web/src/test/fixtures.ts`
- Test: `research/tests/test_metrics.py`
- Test: `research/tests/test_reporting.py`
- Test: `frontend/web/src/app/App.test.tsx`

- [x] **Step 1: Write failing metrics test for per-class values**

Add to `research/tests/test_metrics.py`:

```python
def test_compute_classification_metrics_includes_per_class_metrics() -> None:
    metrics = compute_classification_metrics(
        y_true=["negative", "neutral", "positive", "positive"],
        y_pred=["negative", "positive", "positive", "neutral"],
        labels=["negative", "neutral", "positive"],
    )

    assert metrics.per_class["negative"]["recall"] == 1.0
    assert metrics.per_class["neutral"]["recall"] == 0.0
    assert 0.0 <= metrics.per_class["positive"]["f1"] <= 1.0
```

- [x] **Step 2: Run metrics test and verify it fails**

Run:

```bash
uv run pytest research/tests/test_metrics.py::test_compute_classification_metrics_includes_per_class_metrics -q
```

Expected: FAIL because `per_class` does not exist.

- [x] **Step 3: Add per-class metrics**

In `research/scripts/economic_news_research/metrics.py`, update dataclass:

```python
@dataclass(frozen=True)
class ClassificationMetrics:
    accuracy: float
    macro_precision: float
    macro_recall: float
    macro_f1: float
    confusion_matrix: np.ndarray
    per_class: dict[str, dict[str, float]]
```

Update `compute_classification_metrics`:

```python
per_class_precision, per_class_recall, per_class_f1, _ = precision_recall_fscore_support(
    y_true,
    y_pred,
    labels=labels,
    average=None,
    zero_division=0,
)
per_class = {
    label: {
        "precision": float(per_class_precision[index]),
        "recall": float(per_class_recall[index]),
        "f1": float(per_class_f1[index]),
    }
    for index, label in enumerate(labels)
}
return ClassificationMetrics(
    accuracy=accuracy_score(y_true, y_pred),
    macro_precision=precision,
    macro_recall=recall,
    macro_f1=f1,
    confusion_matrix=confusion_matrix(y_true, y_pred, labels=labels),
    per_class=per_class,
)
```

- [x] **Step 4: Persist per-class metrics in tracking**

In `research/scripts/economic_news_research/tracking.py`, include validation/test `per_class` in metrics JSON:

```python
"validation_per_class": result.validation_metrics.per_class,
"test_per_class": result.test_metrics.per_class,
```

If `tracking.py` builds the JSON inline, add those keys next to `validation` and `test`.

- [x] **Step 5: Read per-class metrics into report**

In `research/scripts/economic_news_research/reporting.py`, update `_build_model_section`:

```python
metrics = _read_metrics_json(model_name=model_name, model_dirs=model_dirs)
return {
    "model_name": model_name,
    "validation_accuracy": _float_or_none(row.get("validation_accuracy")),
    "validation_macro_f1": _float_or_none(row.get("validation_macro_f1")),
    "test_accuracy": _float_or_none(row.get("test_accuracy")),
    "test_macro_f1": _float_or_none(row.get("test_macro_f1")),
    "inference_seconds_per_sample": _float_or_none(row.get("inference_seconds_per_sample")),
    "confusion_matrix": _read_confusion_matrix(model_name=model_name, model_dirs=model_dirs),
    "per_class": metrics.get("test_per_class", {}) if metrics else {},
}
```

Add helper:

```python
def _read_metrics_json(*, model_name: str, model_dirs: list[Path]) -> dict[str, Any] | None:
    metrics_path = _find_existing_file(
        model_dirs=model_dirs,
        filename=f"{model_name}_metrics.json",
    )
    if metrics_path is None:
        return None
    return json.loads(metrics_path.read_text(encoding="utf-8"))
```

- [x] **Step 6: Update contracts and frontend types**

In `packages/contracts/src/economic_news_contracts/analysis.py`, add:

```python
class MlPerClassMetricResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    f1: float = Field(ge=0.0, le=1.0)
```

Add field to ML model response:

```python
per_class: dict[str, MlPerClassMetricResponse] = Field(default_factory=dict)
```

In `frontend/web/src/app/types.ts`, add:

```typescript
  per_class?: Record<string, { precision: number; recall: number; f1: number }>;
```

to `MlReportModel`.

- [x] **Step 7: Render per-class recall/F1 below confusion matrix**

In `frontend/web/src/components/MlReportPanel.tsx`, add helper:

```tsx
function renderPerClassMetrics(model: MlReportModel | null) {
  if (!model?.per_class) {
    return null;
  }

  return (
    <section>
      <h3>Качество по классам</h3>
      <ul className={styles.inlineList}>
        {Object.entries(model.per_class).map(([label, metrics]) => (
          <li key={label}>
            {label}: recall {formatMetric(metrics.recall)}, F1 {formatMetric(metrics.f1)}
          </li>
        ))}
      </ul>
    </section>
  );
}
```

Render it after `renderConfusionMatrix(displayModel)`.

- [x] **Step 8: Run report/frontend tests**

Run:

```bash
uv run pytest research/tests/test_metrics.py research/tests/test_reporting.py packages/contracts/tests -q
npm --prefix frontend/web test -- --run src/app/App.test.tsx
```

Expected: PASS.

- [x] **Step 9: Commit Task 3**

```bash
git add research/scripts/economic_news_research/metrics.py research/scripts/economic_news_research/results.py research/scripts/economic_news_research/tracking.py research/scripts/economic_news_research/reporting.py packages/contracts/src/economic_news_contracts/analysis.py frontend/web/src/app/types.ts frontend/web/src/components/MlReportPanel.tsx frontend/web/src/test/fixtures.ts research/tests/test_metrics.py research/tests/test_reporting.py frontend/web/src/app/App.test.tsx
git commit -m "feat: добавить диагностику качества по классам"
```

---

### Task 4: Phase B Isolate Weak Labeling With Margins

**Files:**

- Create: `research/scripts/economic_news_research/weak_labeling.py`
- Modify: `research/scripts/economic_news_research/data.py`
- Modify: `research/scripts/economic_news_research/reporting.py`
- Test: `research/tests/test_weak_labeling.py`
- Test: `research/tests/test_data.py`
- Test: `research/tests/test_reporting.py`

- [x] **Step 1: Write weak-labeling tests**

Create `research/tests/test_weak_labeling.py`:

```python
from economic_news_research.weak_labeling import infer_weak_impact


def test_infer_weak_impact_returns_positive_with_margin() -> None:
    result = infer_weak_impact(
        title="Company reports profit growth",
        text="Revenue rose and earnings beat expectations.",
    )

    assert result.label == "positive"
    assert result.positive_score > result.negative_score
    assert result.margin >= 2


def test_infer_weak_impact_returns_negative_with_margin() -> None:
    result = infer_weak_impact(
        title="Company shares fall",
        text="Revenue declined and losses increased.",
    )

    assert result.label == "negative"
    assert result.negative_score > result.positive_score
    assert result.margin >= 2


def test_infer_weak_impact_returns_neutral_when_scores_are_close() -> None:
    result = infer_weak_impact(
        title="Company updates outlook",
        text="Revenue rose, but management warned about risks.",
    )

    assert result.label == "neutral"
    assert result.margin <= 1
```

- [x] **Step 2: Run weak-labeling tests and verify they fail**

Run:

```bash
uv run pytest research/tests/test_weak_labeling.py -q
```

Expected: FAIL because module does not exist.

- [x] **Step 3: Implement weak-labeling module**

Create `research/scripts/economic_news_research/weak_labeling.py`:

```python
from dataclasses import dataclass
from enum import StrEnum


class ImpactLabel(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


POSITIVE_TERMS = frozenset(
    {
        "approval",
        "approved",
        "beat",
        "beats",
        "bullish",
        "gain",
        "gains",
        "grew",
        "grow",
        "grows",
        "growth",
        "higher",
        "improve",
        "improves",
        "profit",
        "profits",
        "record",
        "rise",
        "rises",
        "rose",
        "surge",
        "upgraded",
        "upside",
    },
)

NEGATIVE_TERMS = frozenset(
    {
        "bankruptcy",
        "bearish",
        "cut",
        "decline",
        "declines",
        "declined",
        "downgrade",
        "downgraded",
        "drop",
        "drops",
        "fall",
        "falls",
        "fell",
        "lawsuit",
        "loss",
        "losses",
        "lower",
        "miss",
        "misses",
        "recession",
        "risk",
        "risks",
        "weak",
        "warning",
        "warned",
    },
)


@dataclass(frozen=True)
class WeakImpactLabel:
    label: str
    positive_score: int
    negative_score: int
    margin: int


def infer_weak_impact(*, title: object, text: object) -> WeakImpactLabel:
    content = f"{title or ''} {text or ''}".lower()
    positive_score = sum(term in content for term in POSITIVE_TERMS)
    negative_score = sum(term in content for term in NEGATIVE_TERMS)
    margin = abs(positive_score - negative_score)
    if margin <= 1:
        label = ImpactLabel.NEUTRAL.value
    elif positive_score > negative_score:
        label = ImpactLabel.POSITIVE.value
    else:
        label = ImpactLabel.NEGATIVE.value
    return WeakImpactLabel(
        label=label,
        positive_score=positive_score,
        negative_score=negative_score,
        margin=margin,
    )
```

- [x] **Step 4: Wire weak-labeling into dataset adaptation**

In `research/scripts/economic_news_research/data.py`, remove local `POSITIVE_TERMS`, `NEGATIVE_TERMS`, and `infer_weak_impact_label`. Import:

```python
from economic_news_research.weak_labeling import ImpactLabel, infer_weak_impact
```

Update FNSPID adaptation:

```python
weak_labels = [
    infer_weak_impact(title=title, text=text)
    for title, text in zip(dataset["title"], dataset["text"], strict=True)
]
dataset["impact"] = [label.label for label in weak_labels]
dataset["label_source"] = "weak_rules"
dataset["weak_label_margin"] = [label.margin for label in weak_labels]
dataset["weak_positive_score"] = [label.positive_score for label in weak_labels]
dataset["weak_negative_score"] = [label.negative_score for label in weak_labels]
```

- [x] **Step 5: Preserve optional label metadata in validated dataset**

In `research/scripts/economic_news_research/data.py`, add:

```python
OPTIONAL_COLUMNS = [
    "label_source",
    "weak_label_margin",
    "weak_positive_score",
    "weak_negative_score",
]
```

Change the dataset selection:

```python
selected_columns = REQUIRED_COLUMNS + [
    column for column in OPTIONAL_COLUMNS if column in frame.columns
]
dataset = frame.loc[:, selected_columns].copy()
```

- [x] **Step 6: Add report label-quality summary**

In `research/scripts/economic_news_research/reporting.py`, add:

```python
def _label_quality(dataset: pd.DataFrame) -> dict[str, Any]:
    if "weak_label_margin" not in dataset.columns:
        return {"label_source": "provided"}
    margins = pd.to_numeric(dataset["weak_label_margin"], errors="coerce")
    return {
        "label_source": "weak_rules",
        "low_margin_count": int((margins <= 1).sum()),
        "average_margin": float(margins.mean()),
    }
```

Add to report dataset block:

```python
"label_quality": _label_quality(dataset),
```

- [x] **Step 7: Run Phase B tests**

Run:

```bash
uv run pytest research/tests/test_weak_labeling.py research/tests/test_data.py research/tests/test_reporting.py -q
```

Expected: PASS.

- [x] **Step 8: Commit Task 4**

```bash
git add research/scripts/economic_news_research/weak_labeling.py research/scripts/economic_news_research/data.py research/scripts/economic_news_research/reporting.py research/tests/test_weak_labeling.py research/tests/test_data.py research/tests/test_reporting.py
git commit -m "feat: улучшить слабую разметку новостей"
```

---

### Task 5: Phase B Normalize Noisy Financial News Text

**Files:**

- Create: `research/scripts/economic_news_research/text_normalization.py`
- Modify: `research/scripts/economic_news_research/data.py`
- Test: `research/tests/test_text_normalization.py`
- Test: `research/tests/test_data.py`

- [x] **Step 1: Write text normalization tests**

Create `research/tests/test_text_normalization.py`:

```python
from economic_news_research.text_normalization import normalize_news_text


def test_normalize_news_text_removes_urls_and_extra_spaces() -> None:
    text = "Revenue   rose. Read more at https://example.com/page"

    assert normalize_news_text(text) == "Revenue rose. Read more at"


def test_normalize_news_text_removes_common_nasdaq_boilerplate() -> None:
    text = (
        "Fintel reports that on December 13, 2023, analysts updated coverage. "
        "See our leaderboard of companies with the largest price target upside. "
        "Revenue rose."
    )

    assert normalize_news_text(text) == (
        "Analysts updated coverage. Revenue rose."
    )
```

- [x] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run pytest research/tests/test_text_normalization.py -q
```

Expected: FAIL because module does not exist.

- [x] **Step 3: Implement text normalization module**

Create `research/scripts/economic_news_research/text_normalization.py`:

```python
import re

URL_PATTERN = re.compile(r"https?://\S+")
SPACE_PATTERN = re.compile(r"\s+")
BOILERPLATE_PATTERNS = (
    re.compile(r"\bFintel reports that on [^,]+,\s*", re.IGNORECASE),
    re.compile(
        r"\bSee our leaderboard of companies with the largest price target upside\.\s*",
        re.IGNORECASE,
    ),
)


def normalize_news_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = URL_PATTERN.sub("", text)
    for pattern in BOILERPLATE_PATTERNS:
        text = pattern.sub("", text)
    return SPACE_PATTERN.sub(" ", text).strip()
```

- [x] **Step 4: Apply normalization in dataset validation**

In `research/scripts/economic_news_research/data.py`, import:

```python
from economic_news_research.text_normalization import normalize_news_text
```

Replace:

```python
dataset["text"] = dataset["text"].astype(str).str.strip()
```

with:

```python
dataset["text"] = [normalize_news_text(value) for value in dataset["text"]]
```

- [x] **Step 5: Run data tests**

Run:

```bash
uv run pytest research/tests/test_text_normalization.py research/tests/test_data.py -q
```

Expected: PASS.

- [x] **Step 6: Commit Task 5**

```bash
git add research/scripts/economic_news_research/text_normalization.py research/scripts/economic_news_research/data.py research/tests/test_text_normalization.py research/tests/test_data.py
git commit -m "feat: нормализовать тексты финансовых новостей"
```

---

### Task 6: Phase C Class-Balanced Transformer Training

**Files:**

- Modify: `research/scripts/economic_news_research/transformer.py`
- Modify: `apps/analysis-service/src/analysis_service/workers/tasks.py`
- Test: `research/tests/test_transformer.py`
- Test: `apps/analysis-service/tests/test_ml_report_api.py`

- [x] **Step 1: Write failing test for English transformer config**

Add to `research/tests/test_transformer.py`:

```python
def test_tiny_transformer_config_uses_english_default_model() -> None:
    config = TinyTransformerConfig()

    assert config.model_name == "distilbert-base-uncased"
    assert config.epochs == 2
    assert config.batch_size == 8
```

- [x] **Step 2: Write failing test for class weights**

Add to `research/tests/test_transformer.py`:

```python
def test_compute_class_weights_gives_larger_weight_to_minor_classes() -> None:
    weights = compute_class_weights(
        labels=["positive"] * 8 + ["neutral"] * 2 + ["negative"],
        label_to_id={"negative": 0, "neutral": 1, "positive": 2},
    )

    assert weights[0] > weights[1]
    assert weights[1] > weights[2]
```

- [x] **Step 3: Run transformer tests and verify they fail**

Run:

```bash
uv run pytest research/tests/test_transformer.py::test_tiny_transformer_config_uses_english_default_model research/tests/test_transformer.py::test_compute_class_weights_gives_larger_weight_to_minor_classes -q
```

Expected: FAIL because defaults and helper are not implemented.

- [x] **Step 4: Update transformer config**

In `research/scripts/economic_news_research/transformer.py`, change:

```python
DEFAULT_TINY_TRANSFORMER_MODEL = "distilbert-base-uncased"
```

Update dataclass:

```python
@dataclass(frozen=True)
class TinyTransformerConfig:
    model_name: str = DEFAULT_TINY_TRANSFORMER_MODEL
    epochs: int = 2
    batch_size: int = 8
    learning_rate: float = 2e-5
    max_length: int = 256
    seed: int = 42
```

- [x] **Step 5: Add class-weight helper**

In `research/scripts/economic_news_research/transformer.py`, add:

```python
def compute_class_weights(
    *,
    labels: list[str],
    label_to_id: dict[str, int],
) -> list[float]:
    total = len(labels)
    class_count = len(label_to_id)
    counts = {label: labels.count(label) for label in label_to_id}
    return [
        total / (class_count * max(counts[label], 1))
        for label, _ in sorted(label_to_id.items(), key=lambda item: item[1])
    ]
```

- [x] **Step 6: Add weighted Trainer**

In `research/scripts/economic_news_research/transformer.py`, add:

```python
class WeightedTrainer:
    @staticmethod
    def build(*, class_weights: list[float], trainer_class: Any) -> type[Any]:
        import torch

        class _WeightedTrainer(trainer_class):
            def compute_loss(
                self,
                model: Any,
                inputs: dict[str, Any],
                return_outputs: bool = False,
                **kwargs: Any,
            ) -> Any:
                labels = inputs.pop("labels")
                outputs = model(**inputs)
                weights = torch.tensor(class_weights, dtype=torch.float, device=labels.device)
                loss_function = torch.nn.CrossEntropyLoss(weight=weights)
                loss = loss_function(outputs.logits, labels)
                return (loss, outputs) if return_outputs else loss

        return _WeightedTrainer
```

In `HuggingFaceTinyTransformerTrainer.fit`, after importing `Trainer`, compute:

```python
class_weights = compute_class_weights(
    labels=train_labels,
    label_to_id=self._label_to_id,
)
trainer_class = WeightedTrainer.build(
    class_weights=class_weights,
    trainer_class=Trainer,
)
```

Replace the current `self._trainer = Trainer` instantiation block with:

```python
self._trainer = trainer_class(
    model=self._model,
    args=training_args,
    train_dataset=_NewsTextDataset(
        encodings=tokenizer(
            train_texts,
            truncation=True,
            padding=True,
            max_length=self.config.max_length,
        ),
        labels=[self._label_to_id[label] for label in train_labels],
    ),
    eval_dataset=_NewsTextDataset(
        encodings=tokenizer(
            validation_texts,
            truncation=True,
            padding=True,
            max_length=self.config.max_length,
        ),
        labels=[self._label_to_id[label] for label in validation_labels],
    ),
)
```

- [x] **Step 7: Add validation evaluation by epoch**

In `TrainingArguments`, change:

```python
eval_strategy="epoch",
save_strategy="no",
logging_strategy="no",
```

Keep `report_to=[]`.

- [x] **Step 8: Stop reusing stale transformer artifacts**

In `apps/analysis-service/src/analysis_service/workers/tasks.py`, replace:

```python
if not _has_model_report_artifacts(
    artifact_path=settings.transformer_artifact_path,
):
    run_train_transformer(
        dataset_path=selected_dataset_path,
        output_dir=settings.transformer_artifact_path.parent,
        random_state=settings.ml_random_state,
        max_rows=settings.ml_transformer_max_rows,
    )
```

with:

```python
run_train_transformer(
    dataset_path=selected_dataset_path,
    output_dir=settings.transformer_artifact_path.parent,
    random_state=settings.ml_random_state,
    max_rows=settings.ml_transformer_max_rows,
)
```

Delete `_has_model_report_artifacts` if unused after the change.

- [x] **Step 9: Run transformer unit tests**

Run:

```bash
uv run pytest research/tests/test_transformer.py -q
```

Expected: PASS.

- [x] **Step 10: Run fast fake-trainer smoke test**

Run:

```bash
uv run pytest research/tests/test_cli.py::test_run_train_transformer_writes_model_artifacts -q
```

Expected: PASS.

- [x] **Step 11: Commit Task 6**

```bash
git add research/scripts/economic_news_research/transformer.py apps/analysis-service/src/analysis_service/workers/tasks.py research/tests/test_transformer.py apps/analysis-service/tests/test_ml_report_api.py
git commit -m "feat: сбалансировать обучение transformer модели"
```

---

### Task 7: Regenerate Artifacts And Compare A-B-C Metrics

**Files:**

- Modify generated artifacts only after training:
  - `artifacts/models/baseline/*`
  - `artifacts/models/embedding/*`
  - `artifacts/models/transformer/*`
  - `artifacts/models/model_comparison.csv`
  - `reports/ml/model-report.json`

- [x] **Step 1: Run classic baseline training on 20k rows**

Run:

```bash
uv run python -m economic_news_research.cli train-baseline \
  --dataset data/raw/economic_news.csv \
  --output-dir artifacts/models/baseline \
  --max-rows 20000
```

Expected output:

```text
baseline_output_dir=artifacts/models/baseline
```

- [x] **Step 2: Run embedding training on 20k rows**

Run:

```bash
uv run python -m economic_news_research.cli train-embedding \
  --dataset data/raw/economic_news.csv \
  --output-dir artifacts/models/embedding \
  --max-rows 20000
```

Expected output:

```text
embedding_output_dir=artifacts/models/embedding
```

- [x] **Step 3: Run transformer training on 5k rows**

Run:

```bash
uv run python -m economic_news_research.cli train-transformer \
  --dataset data/raw/economic_news.csv \
  --output-dir artifacts/models/transformer \
  --max-rows 5000
```

Expected output:

```text
transformer_output_dir=artifacts/models/transformer
```

- [x] **Step 4: Rebuild comparison and report**

Run:

```bash
uv run python -m economic_news_research.cli compare-models \
  --comparison artifacts/models/baseline/model_comparison.csv \
  --comparison artifacts/models/embedding/model_comparison.csv \
  --comparison artifacts/models/transformer/model_comparison.csv \
  --output-path artifacts/models/model_comparison.csv

uv run python -m economic_news_research.cli ml-report \
  --dataset data/raw/economic_news.csv \
  --comparison-path artifacts/models/model_comparison.csv \
  --model-dir artifacts/models/baseline \
  --model-dir artifacts/models/embedding \
  --model-dir artifacts/models/transformer \
  --output-path reports/ml/model-report.json
```

Expected output contains:

```text
comparison_path=artifacts/models/model_comparison.csv
model_report_path=reports/ml/model-report.json
```

- [x] **Step 5: Inspect final metrics**

Run:

```bash
cat reports/ml/model-report.json
```

Expected checks:

- `dataset.row_count` is `50000`.
- `training.classic_max_rows` is present when generated through worker, or report generation command is re-run through worker for final UI.
- `tfidf-logreg.test_macro_f1` should be compared against old baseline `0.568`.
- `tiny-transformer-classifier.test_macro_f1` should be compared against old baseline `0.275`.
- If transformer still predicts one class, keep it as a documented negative result and do not make it the best model.

- [x] **Step 6: Commit Task 7**

```bash
git add artifacts/models reports/ml/model-report.json
git commit -m "chore: обновить артефакты ML-эксперимента"
```

---

### Task 8: Final Verification

**Files:** no code changes unless verification fails.

- [x] **Step 1: Run Python tests**

Run:

```bash
uv run pytest research/tests apps/analysis-service/tests packages/contracts/tests -q
```

Expected: PASS.

- [x] **Step 2: Run frontend tests and build**

Run:

```bash
npm --prefix frontend/web test -- --run
npm --prefix frontend/web run build
```

Expected: PASS and Vite build succeeds.

- [x] **Step 3: Run lint and type checks**

Run:

```bash
uv run ruff check research apps/analysis-service packages/contracts
uv run ty check research/scripts apps/analysis-service/src packages/contracts/src
```

Expected: PASS.

- [x] **Step 4: Rebuild affected Docker image with cache**

Run:

```bash
docker compose -f deploy/compose.yaml build analysis-service analysis-worker
```

Expected: image builds; repeated build should show dependency layers as `CACHED`.

- [x] **Step 5: Commit verification fixes if needed**

If verification required small fixes:

```bash
git add research apps/analysis-service packages/contracts frontend/web
git commit -m "fix: стабилизировать ML-пайплайн"
```

If no fixes were needed, do not create an empty commit.

---

## Self-Review

- Spec coverage: A is covered by Tasks 1-3, B by Tasks 4-5, C by Task 6, regeneration and verification by Tasks 7-8.
- Placeholder scan: no forbidden placeholder patterns remain.
- Type consistency: model names stay compatible with the existing three-model UI; the public transformer model id remains `tiny-transformer-classifier`, but its implementation becomes class-balanced and English-friendly.
- Risk: full transformer training may be slow on Mac. The plan caps transformer rows at `5000` and keeps TF-IDF as the production-quality fallback.
