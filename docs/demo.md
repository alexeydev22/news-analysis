# Demo Guide

## Цель проверки

Этот документ описывает, как самостоятельно проверить приложение перед защитой.
Проверка должна подтвердить, что проект запускается, индексирует русскоязычные
экономические новости и отвечает на вопросы в диалоговом интерфейсе.

## Быстрая проверка

Обновите `dev`:

```bash
git checkout dev
git pull
```

Запустите весь стек:

```bash
just demo-up
```

Во втором терминале запустите smoke-сценарий:

```bash
just demo-smoke
```

Успешный результат:

```text
ok: api-gateway health
ok: news-service health
ok: news preview returned 5 documents
ok: indexed 5 demo documents
ok: queued index job <uuid>
ok: chat stream emitted 8 events
ok: frontend returned HTML
ok: demo smoke passed
```

После проверки остановите контейнеры:

```bash
just demo-down
```

## Ручная проверка через UI

После `just demo-up` откройте:

```text
http://localhost:5173
```

Порядок действий:

1. Нажать `Предпросмотр CSV`.
2. Убедиться, что появились русские экономические новости.
3. Нажать `Индексировать CSV`.
4. Оставить модель анализа `tfidf-logreg`.
5. Ввести вопрос:

```text
Что означает рост ВВП и снижение инфляции для рынка?
```

6. Нажать `Спросить`.
7. Проверить результат:
   - появился русский ответ;
   - блок `Ход обработки` содержит этапы обработки;
   - справа отображаются источники;
   - у источников есть релевантность;
   - влияние отображается как `позитивное`, `нейтральное` или `негативное`.

## Проверка API без UI

Healthcheck gateway:

```bash
curl http://localhost:8000/health
```

Healthcheck news-service:

```bash
curl http://localhost:8004/health
```

Предпросмотр CSV:

```bash
curl 'http://localhost:8004/api/v1/news/preview?limit=3'
```

Индексация CSV:

```bash
curl -X POST http://localhost:8004/api/v1/news/index \
  -H 'Content-Type: application/json' \
  -d '{"limit": 5}'
```

Проверка SSE-чата:

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H 'Content-Type: application/json' \
  -H 'Accept: text/event-stream' \
  -d '{"question":"Что значит рост ВВП?","analysis_model":"tfidf-logreg","limit":5}'
```

Ожидаемые SSE-события:

```text
chat_started
search_started
sources_found
analysis_started
analysis_completed
answer_started
answer_completed
done
```

## Проверка фоновой индексации

Поставить задачу:

```bash
curl -X POST http://localhost:8004/api/v1/news/index/jobs \
  -H 'Content-Type: application/json' \
  -d '{"limit": 5}'
```

Ожидаемый ответ содержит:

```json
{
  "status": "queued",
  "job_id": "...",
  "events_channel": "news.index.events"
}
```

Это подтверждает, что `news-service` связан с `news-worker`, Taskiq и Redis.

## Проверка режимов анализа

В UI доступны режимы:

| Режим | Статус для demo | Назначение |
| --- | --- | --- |
| `tfidf-logreg` | основной стабильный режим | Быстрая классификация влияния новости. |
| `embedding-logreg` | архитектурно предусмотрен | Классификация на embedding-признаках после подготовки артефакта модели. |
| `tiny-transformer-classifier` | архитектурно предусмотрен | Классификация легкой transformer-моделью после подготовки артефакта модели. |

Для защиты используйте `tfidf-logreg`: он гарантированно работает в локальном
compose-стенде.

## Проверка LLM-режима

По умолчанию `dialog-service` работает в `template`-режиме. Это сделано для
стабильного запуска без локальной языковой модели.

Чтобы проверить `llm`-режим:

1. Запустите OpenAI-compatible LLM server на порту `8080`, например:

```bash
llama-server -m models/Qwen3-0.6B-Instruct-Q8_0.gguf --host 0.0.0.0 --port 8080
```

2. Запустите compose с LLM-режимом:

```bash
DIALOG_GENERATOR_KIND=llm docker compose -f deploy/compose.yaml up --build
```

3. Проверьте UI или smoke:

```bash
uv run python tools/demo_smoke.py
```

Если LLM server не запущен, `llm`-режим ожидаемо завершится ошибкой на этапе
генерации ответа.

## Полная проверка разработки

Backend:

```bash
uv run ruff check apps packages research tools
uv run ty check apps packages research tools/demo_smoke.py
uv run pytest packages apps research/tests -q -W error
```

Frontend:

```bash
npm --prefix frontend/web test -- --run
npm --prefix frontend/web run lint
npm --prefix frontend/web run build
```

Docker Compose:

```bash
docker compose -f deploy/compose.yaml config --quiet
docker compose -f deploy/compose.yaml up -d --build
uv run python tools/demo_smoke.py
docker compose -f deploy/compose.yaml down
```

## Что делать при ошибке

- Если UI не открывается, проверить `docker compose -f deploy/compose.yaml ps`.
- Если чат не находит источники, нажать `Индексировать CSV` и повторить вопрос.
- Если `llm`-режим падает, проверить, что LLM server доступен на `localhost:8080`.
- Если `demo-smoke` падает на frontend, запустить backend-only проверку:

```bash
just demo-smoke-no-frontend
```
