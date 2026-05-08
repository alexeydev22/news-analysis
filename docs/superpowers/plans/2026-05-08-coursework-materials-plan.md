# Coursework Materials Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Подготовить русскоязычные материалы для пояснительной записки и презентации по курсовой работе.

**Architecture:** Это документационный срез без изменения runtime-кода. Материалы разделены на пояснительную записку и презентацию, чтобы их можно было независимо переносить в `.docx` и `.pptx`.

**Tech Stack:** Markdown, существующие документы `README.md`, `docs/architecture.md`, `docs/demo.md`.

---

### Task 1: Coursework Documents

**Files:**
- Create: `docs/coursework/structure.md`
- Create: `docs/coursework/thesis-draft.md`

- [x] **Step 1: Add coursework structure**

Создать `docs/coursework/structure.md` с оглавлением, целью, задачами, главами,
заключением, источниками и приложениями.

- [x] **Step 2: Add thesis draft**

Создать `docs/coursework/thesis-draft.md` с черновиком введения, анализа
предметной области, проектирования, реализации, проверки и заключения.

### Task 2: Presentation Documents

**Files:**
- Create: `docs/presentation/outline.md`
- Create: `docs/presentation/speaker-notes.md`

- [x] **Step 1: Add presentation outline**

Создать `docs/presentation/outline.md` с 12 слайдами, привязанными к критериям
оценки: титул, актуальность, цель и задачи, методы и результаты, заключение,
источники, оформление.

- [x] **Step 2: Add speaker notes**

Создать `docs/presentation/speaker-notes.md` с текстом выступления на 5-7 минут
и короткими ответами на возможные вопросы.

### Task 3: Navigation And Verification

**Files:**
- Modify: `README.md`

- [x] **Step 1: Link new materials from README**

Добавить ссылки на материалы курсовой и презентации в раздел подробных
материалов.

- [x] **Step 2: Verify documentation changes**

Выполнить:

```bash
git diff --check
docker compose -f deploy/compose.yaml config --quiet
```

Ожидаемый результат: обе команды завершаются без ошибок.
