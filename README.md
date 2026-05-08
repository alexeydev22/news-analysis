# Economic News Dialog System

Локальная микросервисная диалоговая система для анализа экономических новостей.

## Тема курсовой работы

Разработка автоматической диалоговой системы на основе языковой модели для анализа экономических новостей.

## Архитектура

Проект строится как monorepo:

- `apps/` — backend-микросервисы;
- `packages/framework` — общий технический foundation;
- `packages/contracts` — общие DTO и event schemas;
- `frontend/web` — React UI;
- `research/` — notebooks, training scripts, reports;
- `docs/` — пояснительная записка и презентация;
- `deploy/` — Docker Compose и Dockerfiles.

## Ветки

- `master` — стабильная основная ветка;
- `dev` — ветка разработки и интеграционного тестирования;
- `feature/*` — ветки отдельных этапов.

## Commit style

Коммиты пишутся на русском языке с conventional prefix:

- `feat: добавить ...`
- `fix: исправить ...`
- `refactor: упростить ...`
- `test: добавить ...`
- `docs: описать ...`
- `chore: настроить ...`

## Локальный запуск foundation

```bash
just test
just compose-up
```

API Gateway healthcheck:

```bash
curl http://localhost:8000/health
```

Ожидаемый ответ:

```json
{"service":"api-gateway","status":"ok"}
```

Analysis Service local run:

```bash
just analysis-dev
curl http://localhost:8001/health
curl -X POST http://localhost:8001/api/v1/analyze \
  -H 'Content-Type: application/json' \
  -d '{"text":"GDP growth beat expectations","analysis_model":"tfidf-logreg"}'
```

## Chat SSE endpoint

`api-gateway` exposes pipeline-progress streaming for the chat flow:

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H 'Content-Type: application/json' \
  -H 'Accept: text/event-stream' \
  -d '{"question":"Что значит рост ВВП?","analysis_model":"tfidf-logreg","limit":5}'
```

The stream emits stage events: `chat_started`, `search_started`, `sources_found`,
`analysis_started`, `analysis_completed`, `answer_started`, `answer_completed`,
and `done`. If a downstream service fails after streaming starts, the response emits
one sanitized `error` event and closes the stream.

## News Service ingestion

`news-service` loads local CSV news and indexes them through `retrieval-service`.

Expected CSV semantic columns:

- title: `title` or `headline`
- text: `text`, `content`, `body` or `description`
- source: `source` or `publisher`

Local preview:

```bash
NEWS_SERVICE_NEWS_DATASET_PATH=research/tests/fixtures/news_impact_sample.csv \
  uv run --package economic-news-news-service granian news_service.main.app:app \
  --interface asgi --host 0.0.0.0 --port 8004

curl 'http://localhost:8004/api/v1/news/preview?limit=3'
```

Index through retrieval-service:

```bash
curl -X POST http://localhost:8004/api/v1/news/index \
  -H 'Content-Type: application/json' \
  -d '{"limit": 10}'
```

## Frontend Chat Console

The React UI is a real API client for the local backend.

Local development:

```bash
npm --prefix frontend/web install
npm --prefix frontend/web run dev -- --host 0.0.0.0 --port 5173
```

Open:

```text
http://localhost:5173
```

Expected backend services:

- `api-gateway` on `http://localhost:8000`;
- `news-service` on `http://localhost:8004`.

Vite proxies `/api-gateway/*` and `/news-service/*` to those local services.
The production nginx image uses the same relative paths inside Docker Compose.

Checks:

```bash
npm --prefix frontend/web test -- --run
npm --prefix frontend/web run lint
npm --prefix frontend/web run typecheck
npm --prefix frontend/web run build
```

## Локальный LLM сервер для Dialog Service

`dialog-service` по умолчанию запускается в режиме `template`, чтобы стек работал без
локальной модели. Для генерации через LLM поднимите OpenAI-compatible сервер, например
`llama.cpp`:

```bash
llama-server -m models/Qwen3-0.6B-Instruct-Q8_0.gguf --host 0.0.0.0 --port 8080
```

Для локального запуска сервиса задайте:

```bash
export DIALOG_GENERATOR_KIND=llm
export DIALOG_LLM_BASE_URL=http://localhost:8080
export DIALOG_LLM_MODEL=Qwen3-0.6B-Instruct-GGUF
```

В Docker Compose `dialog-service` смотрит на host runtime через
`http://host.docker.internal:8080`; сам контейнер с моделью в compose не запускается.
Режим генерации в compose по умолчанию остается `template`. Чтобы включить LLM:

```bash
DIALOG_GENERATOR_KIND=llm docker compose -f deploy/compose.yaml up dialog-service api-gateway
```
