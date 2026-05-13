# Coursework Materials Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the coursework defense materials so the presentation, explanatory note, project explanation, speech text, and Q&A match the current economic news analysis system and the grading criteria.

**Architecture:** Keep generated final artifacts under `docs/final` and keep source content/builders in `docs/*` and `tools/*`. Use the existing generator pattern for `.pptx` and `.docx`, and add focused source documents for the speech and defense Q&A.

**Tech Stack:** Node.js + `pptxgenjs` for presentation generation, Python + `python-docx` for Word documents, existing app screenshots, Markdown source files, bundled document rendering QA.

---

## File Structure

- Modify: `tools/build_final_coursework_pptx.mjs`  
  Responsible for generating the final defense presentation from structured slide content and real screenshots.

- Modify: `tools/build_final_coursework_docx.py`  
  Responsible for generating the refreshed explanatory note.

- Create: `tools/build_project_explanation_docx.py`  
  Responsible for generating the separate 15-20 page human-readable project explanation.

- Create or update: `docs/final/source/coursework-speech.md`  
  Responsible for the 5-minute speech text mapped to presentation slides.

- Create or update: `docs/final/source/coursework-defense-qa.md`  
  Responsible for likely defense questions and concise answers.

- Create or update: `docs/final/source/materials-facts.json`  
  Responsible for reusable project facts: student info, dataset size, model names, current metrics, source list, artifact paths.

- Create or update: `docs/final/assets/chat-page.png`  
  Real screenshot of the Chat page.

- Create or update: `docs/final/assets/ml-report-page.png`  
  Real screenshot of the ML report page.

- Create or update: `docs/final/assets/topic-forecast-page.png`  
  Real screenshot of the Forecast page.

- Create or update: `docs/final/assets/architecture-diagram.png`  
  Microservice architecture diagram.

- Create or update: `docs/final/assets/rag-pipeline-diagram.png`  
  ML/RAG pipeline diagram.

- Regenerate: `docs/final/coursework-defense-presentation.pptx`  
  Final editable presentation.

- Regenerate: `docs/final/coursework-explanatory-note.docx`  
  Final editable explanatory note.

- Create: `docs/final/coursework-project-explanation.docx`  
  Final editable project explanation document.

- Update: `docs/final/README.md`  
  Final artifact index.

---

### Task 1: Prepare Shared Facts and Current Artifact Inputs

**Files:**
- Create or update: `docs/final/source/materials-facts.json`
- Read: `docs/superpowers/specs/2026-05-13-coursework-materials-refresh-design.md`
- Read: current ML report and forecast outputs from the running app or stored generated artifacts

- [ ] **Step 1: Create source directory if needed**

Run:

```bash
mkdir -p docs/final/source docs/final/assets
```

Expected: directories exist.

- [ ] **Step 2: Write shared facts file**

Create `docs/final/source/materials-facts.json` with this structure and current values:

```json
{
  "student": {
    "name": "Прудиев Алексей Сергеевич",
    "group": "ПМ23-4",
    "university": "Финансовый университет при Правительстве РФ",
    "department": "Кафедра искусственного интеллекта",
    "city": "Москва",
    "year": "2026"
  },
  "coursework": {
    "topic": "Разработка автоматической диалоговой системы на основе языковой модели для анализа экономических новостей",
    "discipline": "Машинное обучение в семантическом и сетевом анализе"
  },
  "dataset": {
    "name": "FNSPID",
    "rows": 50000,
    "classes": ["negative", "neutral", "positive"]
  },
  "models": [
    {
      "name": "tfidf-logreg",
      "description": "TF-IDF + Logistic Regression",
      "test_accuracy": 0.78475,
      "test_macro_f1": 0.71676,
      "role": "best baseline model"
    },
    {
      "name": "embedding-logreg",
      "description": "Sentence embeddings + Logistic Regression",
      "test_accuracy": 0.594,
      "test_macro_f1": 0.51538,
      "role": "semantic feature baseline"
    },
    {
      "name": "tiny-transformer-classifier",
      "description": "Lightweight transformer classifier",
      "test_accuracy": 0.488,
      "test_macro_f1": 0.35185,
      "role": "light neural baseline"
    }
  ],
  "forecast": {
    "documents": 10000,
    "topics": 2716,
    "model_reports": 3
  },
  "sources": [
    "Методические указания по выполнению курсовых работ по дисциплине «Машинное обучение в семантическом и сетевом анализе»",
    "FNSPID dataset",
    "scikit-learn documentation",
    "PyTorch documentation",
    "Hugging Face Transformers documentation",
    "Qdrant documentation",
    "FastAPI documentation",
    "MLflow documentation",
    "Docker Compose documentation"
  ]
}
```

- [ ] **Step 3: Verify JSON validity**

Run:

```bash
python -m json.tool docs/final/source/materials-facts.json >/tmp/materials-facts.json
```

Expected: command exits with code 0.

- [ ] **Step 4: Commit**

```bash
git add docs/final/source/materials-facts.json
git commit -m "docs: добавить факты для материалов курсовой"
```

Expected: commit contains only `materials-facts.json`.

---

### Task 2: Capture Real Application Screenshots

**Files:**
- Create or update: `docs/final/assets/chat-page.png`
- Create or update: `docs/final/assets/ml-report-page.png`
- Create or update: `docs/final/assets/topic-forecast-page.png`

- [ ] **Step 1: Confirm the frontend is available**

Run:

```bash
curl -s http://localhost:5173 | head
```

Expected: HTML response from the frontend.

- [ ] **Step 2: Capture the Chat page**

Use the Browser or Playwright skill to navigate to the Chat page, ask a representative economic question, wait for the answer, and save the screenshot:

```bash
/Users/a.prudiev/.codex/skills/playwright/scripts/playwright_cli.sh screenshot http://localhost:5173 docs/final/assets/chat-page.png
```

Expected: `docs/final/assets/chat-page.png` shows the Chat page with an answer and source cards.

- [ ] **Step 3: Capture the ML report page**

Use Browser or Playwright to navigate to the ML report page and save:

```bash
/Users/a.prudiev/.codex/skills/playwright/scripts/playwright_cli.sh screenshot http://localhost:5173 docs/final/assets/ml-report-page.png
```

Expected: `docs/final/assets/ml-report-page.png` shows model metrics, dataset size, and top features.

- [ ] **Step 4: Capture the Forecast page**

Use Browser or Playwright to navigate to the Forecast page and save:

```bash
/Users/a.prudiev/.codex/skills/playwright/scripts/playwright_cli.sh screenshot http://localhost:5173 docs/final/assets/topic-forecast-page.png
```

Expected: `docs/final/assets/topic-forecast-page.png` shows topic forecast results based on at least 10 000 documents.

- [ ] **Step 5: Inspect image dimensions**

Run:

```bash
file docs/final/assets/chat-page.png docs/final/assets/ml-report-page.png docs/final/assets/topic-forecast-page.png
```

Expected: three PNG images with readable desktop dimensions.

- [ ] **Step 6: Commit**

```bash
git add docs/final/assets/chat-page.png docs/final/assets/ml-report-page.png docs/final/assets/topic-forecast-page.png
git commit -m "docs: добавить скриншоты приложения для защиты"
```

Expected: commit contains only the three screenshot files.

---

### Task 3: Build Presentation Source and Final PPTX

**Files:**
- Modify: `tools/build_final_coursework_pptx.mjs`
- Read: `PrezaFin_shablon-arial_itog.pptx`
- Read: `docs/final/source/materials-facts.json`
- Read: `docs/final/assets/chat-page.png`
- Read: `docs/final/assets/ml-report-page.png`
- Read: `docs/final/assets/topic-forecast-page.png`
- Regenerate: `docs/final/coursework-defense-presentation.pptx`

- [ ] **Step 1: Update presentation builder to read shared facts**

Modify `tools/build_final_coursework_pptx.mjs` so it loads facts:

```js
const facts = JSON.parse(
  fs.readFileSync(path.join(finalDir, "source", "materials-facts.json"), "utf8")
);
```

Expected: student name, topic, dataset rows, metrics, forecast counts, and sources come from `materials-facts.json`.

- [ ] **Step 2: Replace old slide outline with grading-based outline**

Implement 11 slides:

```text
1. Титульный слайд
2. Актуальность
3. Цель и задачи
4. Данные и постановка задачи
5. Методы анализа
6. ML/RAG-пайплайн
7. Архитектура приложения
8. Результаты моделей
9. Работа приложения
10. Заключение
11. Источники
```

Expected: slide titles match the approved design.

- [ ] **Step 3: Add three screenshots to the application slide**

On slide 9, place:

```js
slide.addImage({ path: path.join(assetsDir, "chat-page.png"), x: 0.55, y: 1.35, w: 3.95, h: 2.4 });
slide.addImage({ path: path.join(assetsDir, "ml-report-page.png"), x: 4.7, y: 1.35, w: 3.95, h: 2.4 });
slide.addImage({ path: path.join(assetsDir, "topic-forecast-page.png"), x: 8.85, y: 1.35, w: 3.95, h: 2.4 });
```

Add short labels: `Чат`, `ML-отчет`, `Прогноз`.

Expected: all three pages are visible on one slide.

- [ ] **Step 4: Add results table from facts**

On slide 8, create a table with:

```text
Модель | Test accuracy | Test macro F1 | Роль
tfidf-logreg | 0.785 | 0.717 | лучшая baseline-модель
embedding-logreg | 0.594 | 0.515 | semantic baseline
tiny-transformer-classifier | 0.488 | 0.352 | light neural baseline
```

Expected: TF-IDF row is visually highlighted.

- [ ] **Step 5: Generate presentation**

Run:

```bash
node tools/build_final_coursework_pptx.mjs
```

Expected: `docs/final/coursework-defense-presentation.pptx` is generated successfully.

- [ ] **Step 6: Smoke-check PPTX package**

Run:

```bash
unzip -t docs/final/coursework-defense-presentation.pptx >/tmp/pptx-check.txt
```

Expected: output includes `No errors detected`.

- [ ] **Step 7: Commit**

```bash
git add tools/build_final_coursework_pptx.mjs docs/final/coursework-defense-presentation.pptx
git commit -m "docs: обновить презентацию курсовой"
```

Expected: commit contains the presentation builder and generated PPTX.

---

### Task 4: Rebuild the Explanatory Note

**Files:**
- Modify: `tools/build_final_coursework_docx.py`
- Read: `docs/final/source/materials-facts.json`
- Read: screenshot and diagram assets under `docs/final/assets`
- Regenerate: `docs/final/coursework-explanatory-note.docx`

- [ ] **Step 1: Update document builder to read shared facts**

Add a helper near the top of `tools/build_final_coursework_docx.py`:

```python
def load_materials_facts() -> dict:
    facts_path = ROOT / "docs" / "final" / "source" / "materials-facts.json"
    return json.loads(facts_path.read_text(encoding="utf-8"))
```

Expected: document content uses one source of truth for student data, dataset rows, metrics, and sources.

- [ ] **Step 2: Replace or rewrite document sections**

The generated document must contain:

```text
Титульный лист
Содержание
Введение
1 Теоретические основы анализа экономических новостей
2 Данные и постановка ML-задачи
3 Методы и модели
4 Архитектура программной системы
5 Реализация и пользовательский сценарий
6 Эксперимент и результаты
7 Направления улучшения
Заключение
Список использованных источников
Приложения
```

Expected: backend architecture is present but compact.

- [ ] **Step 3: Add screenshots to the implementation section**

Insert three figures:

```text
Рисунок 1 - Страница чата
Рисунок 2 - Страница ML-отчета
Рисунок 3 - Страница прогноза
```

Expected: each screenshot is readable and has a caption.

- [ ] **Step 4: Add model results table**

Insert a table with:

```text
Модель | Test accuracy | Test macro F1 | Интерпретация
tfidf-logreg | 0.785 | 0.717 | лучшая baseline-модель
embedding-logreg | 0.594 | 0.515 | уступает TF-IDF на текущей разметке
tiny-transformer-classifier | 0.488 | 0.352 | ограничен размером и режимом обучения
```

Expected: text explains why macro F1 is important under class imbalance.

- [ ] **Step 5: Generate explanatory note**

Run:

```bash
uv run python tools/build_final_coursework_docx.py
```

Expected: `docs/final/coursework-explanatory-note.docx` is generated.

- [ ] **Step 6: Render-check the DOCX**

Run:

```bash
env TMPDIR=/private/tmp /Users/a.prudiev/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 /Users/a.prudiev/.codex/plugins/cache/openai-primary-runtime/documents/26.506.11943/skills/documents/render_docx.py docs/final/coursework-explanatory-note.docx --output_dir docs/final/qa/docx-render --emit_pdf
```

Expected: rendered pages are produced under `docs/final/qa/docx-render`.

- [ ] **Step 7: Commit**

```bash
git add tools/build_final_coursework_docx.py docs/final/coursework-explanatory-note.docx docs/final/qa/docx-render
git commit -m "docs: обновить пояснительную записку"
```

Expected: commit contains the builder, generated DOCX, and render QA outputs.

---

### Task 5: Create Project Explanation DOCX

**Files:**
- Create: `tools/build_project_explanation_docx.py`
- Read: `docs/final/source/materials-facts.json`
- Create: `docs/final/coursework-project-explanation.docx`

- [ ] **Step 1: Create a focused DOCX builder**

Create `tools/build_project_explanation_docx.py` with:

```python
from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.shared import Pt

ROOT = Path(__file__).resolve().parents[1]
FINAL_DIR = ROOT / "docs" / "final"


def add_paragraph(document: Document, text: str) -> None:
    paragraph = document.add_paragraph(text)
    paragraph.paragraph_format.space_after = Pt(6)


def main() -> None:
    facts = json.loads((FINAL_DIR / "source" / "materials-facts.json").read_text(encoding="utf-8"))
    document = Document()
    document.add_heading("Подробное описание проекта", level=0)
    add_paragraph(document, facts["coursework"]["topic"])
    document.add_heading("1. Суть проекта простыми словами", level=1)
    add_paragraph(document, "Система принимает вопрос по экономическим новостям, ищет релевантные материалы, оценивает влияние новостей, формирует ответ и аналитический прогноз.")
    document.add_heading("2. Какая задача решается", level=1)
    add_paragraph(document, "Проект является диалоговой аналитической системой на основе машинного обучения, поиска по новостям и языковой модели.")
    document.add_heading("3. Как устроены данные", level=1)
    add_paragraph(document, f"Используется датасет {facts['dataset']['name']} объемом {facts['dataset']['rows']} новостей с классами влияния: negative, neutral, positive.")
    document.add_heading("4. Как работает ML-часть", level=1)
    add_paragraph(document, "Сравниваются три подхода: TF-IDF + Logistic Regression, embedding-logreg и tiny-transformer-classifier.")
    document.add_heading("5. Метрики и их смысл", level=1)
    add_paragraph(document, "Accuracy показывает долю правильных ответов, macro F1 учитывает качество по каждому классу и важен при дисбалансе классов, inference time показывает скорость применения модели.")
    document.add_heading("6. Как работает поиск источников и RAG", level=1)
    add_paragraph(document, "Вопрос пользователя используется для поиска похожих новостей. Найденные источники становятся контекстом для ответа.")
    document.add_heading("7. Как используется языковая модель", level=1)
    add_paragraph(document, "К системе можно подключить модель через API. Найденные новости передаются в модель, а модель формирует аналитический прогноз, основанный на фактах из текста.")
    document.add_heading("8. Как устроена архитектура без лишних деталей", level=1)
    add_paragraph(document, "Frontend обращается к API Gateway, а отдельные сервисы отвечают за новости, поиск, анализ и диалог. Redis используется для фоновых задач, Qdrant - для векторного поиска.")
    document.add_heading("9. Что показывать на защите", level=1)
    add_paragraph(document, "Нужно показать три страницы: Чат, ML-отчет и Прогноз.")
    document.add_heading("10. Ограничения проекта", level=1)
    add_paragraph(document, "Ключевые ограничения: шумная разметка, дисбаланс классов, легкие модели и отсутствие финансовой валидации фактического влияния.")
    document.add_heading("11. Как улучшить проект", level=1)
    add_paragraph(document, "Направления улучшения: балансировка классов, очистка разметки, подбор гиперпараметров, дообучение transformer, тематическая кластеризация и контроль качества прогнозов.")
    document.add_heading("12. Вероятные вопросы комиссии и ответы", level=1)
    add_paragraph(document, "Подробные ответы вынесены в отдельный Q&A-файл.")
    document.save(FINAL_DIR / "coursework-project-explanation.docx")


if __name__ == "__main__":
    main()
```

Expected: script creates the first complete version of the explanation document.

- [ ] **Step 2: Expand each section to 15-20 pages total**

Expand the document text in the builder with explanatory paragraphs. Keep no launch instructions. Include metric interpretation and improvement ideas.

Expected: generated DOCX is readable as a standalone explanation.

- [ ] **Step 3: Generate project explanation**

Run:

```bash
uv run python tools/build_project_explanation_docx.py
```

Expected: `docs/final/coursework-project-explanation.docx` exists.

- [ ] **Step 4: Render-check project explanation**

Run:

```bash
env TMPDIR=/private/tmp /Users/a.prudiev/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 /Users/a.prudiev/.codex/plugins/cache/openai-primary-runtime/documents/26.506.11943/skills/documents/render_docx.py docs/final/coursework-project-explanation.docx --output_dir docs/final/qa/project-explanation-render --emit_pdf
```

Expected: rendered pages are produced under `docs/final/qa/project-explanation-render`.

- [ ] **Step 5: Commit**

```bash
git add tools/build_project_explanation_docx.py docs/final/coursework-project-explanation.docx docs/final/qa/project-explanation-render
git commit -m "docs: добавить подробное описание проекта"
```

Expected: commit contains the explanation builder, generated DOCX, and render QA outputs.

---

### Task 6: Write Speech Text

**Files:**
- Create or update: `docs/final/source/coursework-speech.md`

- [ ] **Step 1: Draft 5-minute speech by slide**

Create `docs/final/source/coursework-speech.md` with sections:

```markdown
# Текст доклада

## Слайд 1. Титульный слайд

Здравствуйте. Тема моей курсовой работы - «Разработка автоматической диалоговой системы на основе языковой модели для анализа экономических новостей».

## Слайд 2. Актуальность

Поток экономических новостей постоянно растет, и пользователю сложно вручную быстро понять, какие сообщения относятся к его вопросу и какое влияние они могут иметь.
```

Expected: one section per presentation slide.

- [ ] **Step 2: Add time budget**

Add approximate timings:

```markdown
| Слайд | Время |
|---|---:|
| 1 | 15 сек |
| 2 | 30 сек |
| 3 | 35 сек |
| 4 | 35 сек |
| 5 | 40 сек |
| 6 | 35 сек |
| 7 | 35 сек |
| 8 | 45 сек |
| 9 | 40 сек |
| 10 | 35 сек |
| 11 | 20 сек |
```

Expected: total is about 5 minutes.

- [ ] **Step 3: Verify speech length**

Run:

```bash
wc -w docs/final/source/coursework-speech.md
```

Expected: approximately 650-850 Russian words.

- [ ] **Step 4: Commit**

```bash
git add docs/final/source/coursework-speech.md
git commit -m "docs: добавить текст доклада"
```

Expected: commit contains only the speech file.

---

### Task 7: Write Defense Q&A

**Files:**
- Create or update: `docs/final/source/coursework-defense-qa.md`

- [ ] **Step 1: Create Q&A categories**

Create `docs/final/source/coursework-defense-qa.md` with:

```markdown
# Вопросы и ответы для защиты

## Тема и актуальность

## Данные

## Модели и метрики

## RAG и языковая модель

## Архитектура

## Ограничения и улучшения
```

Expected: all likely defense areas are covered.

- [ ] **Step 2: Add at least 25 questions**

Include questions such as:

```markdown
### Почему выбрана именно такая тема?

Тема актуальна, потому что поток экономических новостей большой, а пользователю нужен быстрый способ найти релевантные сообщения, оценить их влияние и получить краткий аналитический вывод.

### Почему macro F1 важнее одной accuracy?

Macro F1 считает качество по каждому классу отдельно и затем усредняет результат. Это важно при дисбалансе классов, потому что высокая accuracy может скрывать плохое качество на редких классах.
```

Expected: answers are concise enough for oral defense.

- [ ] **Step 3: Check for banned specificity**

Run:

```bash
rg -n "Gemini|Groq|финансовая рекомендация|запустить|docker compose" docs/final/source/coursework-defense-qa.md
```

Expected: no matches, unless a term is intentionally used only as an optional provider example.

- [ ] **Step 4: Commit**

```bash
git add docs/final/source/coursework-defense-qa.md
git commit -m "docs: добавить вопросы и ответы для защиты"
```

Expected: commit contains only the Q&A file.

---

### Task 8: Update Final README and Run Material QA

**Files:**
- Modify: `docs/final/README.md`
- Read: all final artifacts under `docs/final`

- [ ] **Step 1: Update artifact index**

Update `docs/final/README.md` to list:

```markdown
- `coursework-defense-presentation.pptx` - презентация для защиты;
- `coursework-explanatory-note.docx` - пояснительная записка;
- `coursework-project-explanation.docx` - подробное описание проекта;
- `source/coursework-speech.md` - текст доклада;
- `source/coursework-defense-qa.md` - вопросы и ответы для защиты.
```

Expected: README matches the final five-file set.

- [ ] **Step 2: Verify required files exist**

Run:

```bash
ls -lh docs/final/coursework-defense-presentation.pptx docs/final/coursework-explanatory-note.docx docs/final/coursework-project-explanation.docx docs/final/source/coursework-speech.md docs/final/source/coursework-defense-qa.md
```

Expected: all five files exist.

- [ ] **Step 3: Verify PPTX and DOCX packages**

Run:

```bash
unzip -t docs/final/coursework-defense-presentation.pptx >/tmp/pptx-check.txt
unzip -t docs/final/coursework-explanatory-note.docx >/tmp/note-check.txt
unzip -t docs/final/coursework-project-explanation.docx >/tmp/explanation-check.txt
```

Expected: each check reports no package errors.

- [ ] **Step 4: Check criteria coverage**

Run:

```bash
rg -n "Титул|Актуальность|Цель|задач|Методы|результат|Заключение|Источники|Чат|ML-отчет|Прогноз" docs/final/source docs/final/README.md
```

Expected: output shows coverage of grading criteria and the three required screenshots/pages.

- [ ] **Step 5: Commit final README and QA updates**

```bash
git add docs/final/README.md docs/final/qa
git commit -m "docs: обновить индекс финальных материалов"
```

Expected: commit contains README and QA updates.

---

## Self-Review Checklist

- [ ] Presentation follows the grading criteria explicitly.
- [ ] Presentation uses the Financial University template and strict academic style.
- [ ] Presentation includes screenshots of Chat, ML report, and Forecast pages.
- [ ] Explanatory note follows the methodical structure.
- [ ] Explanatory note is approximately 28 pages after rendering.
- [ ] Project explanation does not include launch instructions.
- [ ] Project explanation explains metrics, limitations, and improvement paths.
- [ ] Speech text fits about 5 minutes.
- [ ] Q&A covers likely commission questions.
- [ ] LLM provider is described neutrally as an external LLM API unless implementation-specific wording is unavoidable.
- [ ] Backend architecture is present but does not dominate the materials.
