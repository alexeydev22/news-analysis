# Runtime Config And ML Quality Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Убрать неиспользуемый PostgreSQL, восстановить передачу Gemini API key в контейнеры, переименовать кнопки прогноза и улучшить ML-метрики на FNSPID.

**Architecture:** Инфраструктурная правка остается в Docker Compose: `.env.example` задает публичные defaults, локальный `.env` переопределяет секреты. ML-правка остается в слое подготовки данных: FNSPID адаптируется в обучающий текст `title + text`, чтобы модель видела тот же сигнал, по которому формируется weak-label.

**Tech Stack:** Docker Compose, FastAPI services, Taskiq workers, React/Vitest, pandas/scikit-learn research pipeline.

---

### Task 1: Compose и env

**Files:**
- Modify: `deploy/compose.yaml`
- Modify: `.env.example`

- [x] **Step 1: Убрать PostgreSQL из docker compose**

Удалить сервис `postgres`, volume `postgres_data` и зависимость `api-gateway` от `postgres`.

- [x] **Step 2: Подключить локальный `.env` как override**

Для сервисов с `env_file` использовать `../.env.example` и опциональный `../.env`.

- [x] **Step 3: Не перетирать секреты пустой интерполяцией**

Убрать явные `ANALYSIS_GEMINI_API_KEY: "${ANALYSIS_GEMINI_API_KEY:-}"` и `DIALOG_GEMINI_API_KEY: "${DIALOG_GEMINI_API_KEY:-}"`, чтобы значения брались из `env_file`.

- [x] **Step 4: Не перетирать локальные лимиты обучения**

Убрать явные `ANALYSIS_ML_TRAIN_MAX_ROWS` и `ANALYSIS_ML_TRANSFORMER_MAX_ROWS` из `environment`, чтобы локальный `.env` мог снижать нагрузку на Mac без изменения кода.

- [x] **Step 5: Разрешить runtime-загрузку transformer cache**

Поставить default `HF_HUB_OFFLINE=0` и `TRANSFORMERS_OFFLINE=0`, чтобы ML-отчет мог один раз скачать отсутствующую HuggingFace-модель в общий `artifacts/hf-cache`.

### Task 2: UI прогнозов

**Files:**
- Modify: `frontend/web/src/components/TopicForecastPanel.tsx`
- Modify: `frontend/web/src/app/App.test.tsx`
- Modify: `frontend/web/src/api/analysis.ts`

- [x] **Step 1: Переименовать пользовательские кнопки**

`Gemini-прогноз темы` заменить на `Прогноз темы`, `Gemini-прогноз новости` заменить на `Прогноз новости`.

- [x] **Step 2: Обновить тестовые ожидания**

Vitest должен искать новые пользовательские названия кнопок.

### Task 3: FNSPID training text

**Files:**
- Modify: `research/scripts/economic_news_research/data.py`
- Modify: `research/tests/test_data.py`

- [x] **Step 1: Согласовать weak-label и признаки**

В адаптере FNSPID формировать `text` как нормализованный `title + text`, а weak-label считать по этому же объединенному тексту.

- [x] **Step 2: Обновить тесты подготовки данных**

Тесты фиксируют, что заголовок попадает в обучающий текст и влияет на weak-label metadata.

### Task 4: Verification and runtime refresh

**Files:**
- Runtime only.

- [ ] **Step 1: Запустить backend/frontend тесты**

Run:
`uv run pytest research/tests apps/analysis-service/tests packages/contracts/tests -q`
`npm --prefix frontend/web test -- --run`

- [ ] **Step 2: Проверить compose config**

Run:
`docker compose -f deploy/compose.yaml config`

- [ ] **Step 3: Пересобрать и пересоздать контейнеры**

Run:
`docker compose -f deploy/compose.yaml up -d --build --remove-orphans`

- [ ] **Step 4: Проверить env в контейнерах**

Run:
`docker compose -f deploy/compose.yaml exec -T analysis-service sh -lc 'test -n "$ANALYSIS_GEMINI_API_KEY" && echo set'`
`docker compose -f deploy/compose.yaml exec -T dialog-service sh -lc 'test -n "$DIALOG_GEMINI_API_KEY" && echo set'`

- [ ] **Step 5: Сформировать свежие отчеты через UI или API**

ML-отчет и прогноз должны запускаться заново после пересоздания контейнеров. Старый `reports/topic-forecast/latest.json` на 500 документов не является результатом новой сборки.
