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
