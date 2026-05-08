# Russian Demo Localization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Русифицировать пользовательский demo-слой приложения без переименования API-контрактов и технических identifiers.

**Architecture:** Изменение затрагивает presentation/demo boundary: React UI text, demo CSV content, human-readable model explanations, README demo instructions. API event names, enum values, service URLs and internal contracts remain stable.

**Tech Stack:** React/Vitest, FastAPI services, Pydantic contracts, Docker Compose, Taskiq/Redis/FastStream, Qdrant.

---

### Task 1: Frontend Visible Text

**Files:**
- Modify: `frontend/web/src/components/ControlsPanel.tsx`
- Modify: `frontend/web/src/components/ChatPanel.tsx`
- Modify: `frontend/web/src/components/NewsPreview.tsx`
- Modify: `frontend/web/src/components/SourcesPanel.tsx`
- Modify: `frontend/web/src/app/App.tsx`
- Test: `frontend/web/src/app/App.test.tsx`

- [ ] **Step 1: Write failing tests**

Assert Russian UI labels: title `Диалоговая система анализа экономических новостей`, buttons `Предпросмотр CSV`, `Индексировать CSV`, `Спросить`, headings `Набор данных`, `Источники`.

- [ ] **Step 2: Run frontend tests**

Run: `npm --prefix frontend/web test -- --run`

Expected before implementation: tests fail because English labels are still rendered.

- [ ] **Step 3: Localize visible labels**

Replace user-facing English strings with Russian equivalents. Keep internal event names unchanged in state and API payloads.

- [ ] **Step 4: Verify**

Run: `npm --prefix frontend/web test -- --run`.

### Task 2: Demo Dataset And Explanations

**Files:**
- Modify: `data/raw/economic_news.csv`
- Modify: `apps/analysis-service/src/analysis_service/domain/model.py`
- Test: `apps/analysis-service/tests/test_domain.py`
- Test: `apps/analysis-service/tests/test_api.py`

- [ ] **Step 1: Write failing tests**

Assert generated explanations are Russian, for example `Модель классифицировала влияние новости как positive.`.

- [ ] **Step 2: Run backend tests**

Run: `uv run pytest apps/analysis-service/tests/test_domain.py apps/analysis-service/tests/test_api.py -q -W error`.

Expected before implementation: tests fail because explanations are English.

- [ ] **Step 3: Localize dataset and explanation text**

Translate demo CSV titles, texts and source names to Russian. Keep `impact` values as enum-compatible English labels.

- [ ] **Step 4: Verify**

Run: `uv run pytest apps/analysis-service/tests/test_domain.py apps/analysis-service/tests/test_api.py -q -W error`.

### Task 3: Docs And Full Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-05-08-e2e-demo-scenario-design.md`
- Modify: `docs/superpowers/plans/2026-05-08-e2e-demo-scenario-plan.md`

- [ ] **Step 1: Localize demo documentation**

Translate demo scenario descriptions to Russian. Keep shell commands unchanged.

- [ ] **Step 2: Run checks**

Run:

```bash
uv run ruff check apps packages research tools
uv run ty check apps packages research tools/demo_smoke.py
uv run pytest packages apps research/tests -q -W error
npm --prefix frontend/web test -- --run
npm --prefix frontend/web run lint
npm --prefix frontend/web run build
docker compose -f deploy/compose.yaml up -d --build
uv run python tools/demo_smoke.py
docker compose -f deploy/compose.yaml down
```

- [ ] **Step 3: Commit**

Commit message: `feat: русифицировать demo интерфейс`
