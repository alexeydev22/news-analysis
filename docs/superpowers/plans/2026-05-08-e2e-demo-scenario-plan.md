# План реализации E2E demo-сценария

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить воспроизводимый локальный demo-сценарий для защиты курсовой.

**Architecture:** Demo-артефакты находятся вне внутренней логики сервисов. Python smoke-скрипт на стандартной библиотеке вызывает существующие HTTP endpoints и парсит SSE-события. Just-команды и README связывают flow для локального запуска.

**Tech Stack:** Python standard library, pytest, Docker Compose, Just, существующие FastAPI/SSE endpoints, React frontend.

---

### Task 1: Demo Dataset

**Files:**
- Create: `data/raw/economic_news.csv`

- [ ] **Step 1: Добавить небольшой стабильный CSV dataset**

Использовать колонки, которые принимает `news-service`: `title`, `text`, `source`, `published_at`, `impact`.

- [ ] **Step 2: Проверить, что preview парсит dataset через существующие тесты или smoke-скрипт**

Запустить focused news-service tests после появления скрипта.

### Task 2: Smoke Script

**Files:**
- Create: `tools/demo_smoke.py`
- Test: `packages/framework/tests/test_demo_smoke.py`

- [ ] **Step 1: Написать failing tests для сборки URL и SSE parsing**

Тесты должны импортировать скрипт по path и проверять helper behavior без Docker.

- [ ] **Step 2: Реализовать минимальные helpers и CLI**

Скрипт должен проверять health, preview, enqueue indexing, chat stream и optional frontend HTML.

- [ ] **Step 3: Запустить focused tests**

Run `uv run pytest packages/framework/tests/test_demo_smoke.py -q -W error`.

### Task 3: Команды и документация

**Files:**
- Modify: `justfile`
- Modify: `README.md`

- [ ] **Step 1: Добавить demo commands**

Добавить `demo-up`, `demo-smoke` и `demo-down`.

- [ ] **Step 2: Описать demo flow для защиты**

Добавить команды и ожидаемое поведение в README.

### Task 4: Проверка и PR

**Files:**
- Только repository-wide checks.

- [ ] **Step 1: Запустить полную проверку**

Запустить backend tests, frontend tests/build, compose config и relevant Docker builds.

- [ ] **Step 2: Создать commit, push и открыть PR**

Использовать русский conventional commit message.
