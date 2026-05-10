# План реализации real trained analysis modes

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Цель:** сделать так, чтобы приложение запускалось с тремя реальными обученными моделями анализа, а не только со static demo classifier.

**Архитектура:** обученные артефакты остаются локально в `artifacts/models`, потому что model files намеренно не коммитятся в git. Репозиторий должен давать воспроизводимые команды для подготовки training CSV, обучения трех моделей и smoke-проверки trained-стека через публичный analysis API.

**Tech Stack:** pandas, scikit-learn, sentence-transformers, HuggingFace transformers, joblib, MLflow, FastAPI, Docker Compose, Justfile.

---

## File Map

- Create or overwrite local ignored file `data/raw/news_impact.csv` from `data/raw/economic_news.csv`.
- Create ignored artifacts under `artifacts/models/baseline`, `artifacts/models/embedding`, and `artifacts/models/transformer`.
- Modify `justfile` to add `train-models`, `trained-smoke`, and optional helper recipes.
- Create `tools/trained_smoke.py` to verify all three analysis models through HTTP.
- Modify `docs/deployment/model-modes-and-large-datasets.md` and `docs/demo.md` to describe the real trained flow.

## Task 1: Подготовить локальный training dataset

**Files:**
- Runtime output: `data/raw/news_impact.csv`

- [x] **Step 1: Generate the training CSV**

Run:

```bash
just prepare-demo-training
```

Expected: `data/raw/news_impact.csv` exists and contains:

```text
article_id,text,impact,source,published_at
```

- [x] **Step 2: Validate the training CSV**

Run:

```bash
uv run --project research python -m economic_news_research.cli validate --dataset data/raw/news_impact.csv
```

Expected output includes:

```text
validated_rows=10
```

## Task 2: Обучить три real модели

**Files:**
- Runtime output: `artifacts/models/baseline/tfidf-logreg.joblib`
- Runtime output: `artifacts/models/embedding/embedding-logreg.joblib`
- Runtime output: `artifacts/models/transformer/tiny-transformer-classifier.joblib`

- [x] **Step 1: Train baseline TF-IDF classifier**

Run:

```bash
just train-baseline
```

Expected: `artifacts/models/baseline/tfidf-logreg.joblib` exists.

- [x] **Step 2: Train embedding classifier**

Run:

```bash
just train-embedding
```

Expected: `artifacts/models/embedding/embedding-logreg.joblib` exists. First run may download the sentence-transformers model.

- [x] **Step 3: Train tiny transformer classifier**

Run:

```bash
just train-transformer
```

Expected: `artifacts/models/transformer/tiny-transformer-classifier.joblib` exists. First run may download the HuggingFace transformer model.

- [x] **Step 4: Compare trained models**

Run:

```bash
just compare-models
```

Expected: `artifacts/models/model_comparison.csv` exists and includes all three model names.

## Task 3: Добавить trained smoke check

**Files:**
- Create: `tools/trained_smoke.py`
- Modify: `justfile`

- [x] **Step 1: Create HTTP smoke script**

Create `tools/trained_smoke.py` that:

```python
import httpx

MODELS = ["tfidf-logreg", "embedding-logreg", "tiny-transformer-classifier"]

def main() -> None:
    for model in MODELS:
        response = httpx.post(
            "http://localhost:8001/api/v1/analyze",
            json={
                "text": "ВВП вырос быстрее ожиданий, а инфляция замедлилась.",
                "analysis_model": model,
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        assert payload["model_name"] == model
        assert payload["impact"] in {"positive", "neutral", "negative"}
        print(f"ok: {model} -> {payload['impact']} confidence={payload['confidence']}")

if __name__ == "__main__":
    main()
```

- [x] **Step 2: Add Justfile recipes**

Add:

```make
train-models:
    just train-baseline
    just train-embedding
    just train-transformer
    just compare-models

trained-smoke:
    uv run python tools/trained_smoke.py
```

- [x] **Step 3: Run script unit syntax check**

Run:

```bash
uv run python -m py_compile tools/trained_smoke.py
```

Expected: exit code 0.

## Task 4: Проверить runtime trained stack

**Files:**
- No code files expected.

- [x] **Step 1: Start trained analysis service**

Run:

```bash
ANALYSIS_USE_STATIC_CLASSIFIER=false HF_HOME=artifacts/hf-cache HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --package economic-news-analysis-service granian analysis_service.main.app:app --interface asgi --host 127.0.0.1 --port 8001
```

Expected: `analysis-service` starts and does not log unavailable artifacts.

- [x] **Step 2: Smoke-test all three models**

In another terminal or after starting compose in background, run:

```bash
just trained-smoke
```

Expected output includes:

```text
ok: tfidf-logreg
ok: embedding-logreg
ok: tiny-transformer-classifier
```

- [x] **Step 3: Verify UI/API flow**

Open `http://localhost:5173`, select each of the three analysis models, ask:

```text
Что означает рост ВВП и снижение инфляции для рынка?
```

Expected: no `503`; sources and impact summaries render for all three models.
Automated verification covered frontend availability through `just demo-smoke`
and all three analysis modes through `just trained-smoke`.

## Task 5: Документация и коммит

**Files:**
- Modify: `docs/deployment/model-modes-and-large-datasets.md`
- Modify: `docs/demo.md`
- Modify: `justfile`
- Create: `tools/trained_smoke.py`

- [x] **Step 1: Update docs**

Docs must state:

- artifacts are local and gitignored;
- first training may download HuggingFace models;
- `just prepare-demo-training`;
- `just train-models`;
- `just demo-up-trained`;
- `just trained-smoke`;
- UI can switch all three models only after artifacts exist.

- [ ] **Step 2: Run verification**

Run:

```bash
uv run pytest tests/test_prepare_dataset.py apps/analysis-service/tests/test_infrastructure.py apps/analysis-service/tests/test_api.py -v
npm --prefix frontend/web test -- --run
docker compose -f deploy/compose.yaml config --quiet
git diff --check
```

Expected: all pass.

- [ ] **Step 3: Commit**

Run:

```bash
git add docs/superpowers/plans/2026-05-10-real-trained-analysis-modes.md tools/trained_smoke.py justfile docs/deployment/model-modes-and-large-datasets.md docs/demo.md
git commit -m "feat: добавить реальный trained-режим анализа"
```

## Self-Review

Spec coverage:

- Real three-model runtime is covered by training and smoke tasks.
- Artifacts remain local because `.gitignore` intentionally excludes model files.
- The plan includes verification through the running `analysis-service` API, not only local training commands.
- The transformer path remains a real HuggingFace training path; it is not replaced by a fake third sklearn model.
