# Диалоговая система анализа экономических новостей

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

Подробные материалы:

- [Архитектура проекта](docs/architecture.md);
- [Demo guide и чеклист проверки](docs/demo.md);
- [Структура курсовой работы](docs/coursework/structure.md);
- [Черновик пояснительной записки](docs/coursework/thesis-draft.md);
- [Структура презентации](docs/presentation/outline.md);
- [Заметки докладчика](docs/presentation/speaker-notes.md).

## Ветки

- `master` — стабильная основная ветка;
- `dev` — ветка разработки и интеграционного тестирования;
- `feature/*` — ветки отдельных этапов.

## Стиль коммитов

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

Локальный запуск Analysis Service:

```bash
just analysis-dev
curl http://localhost:8001/health
curl -X POST http://localhost:8001/api/v1/analyze \
  -H 'Content-Type: application/json' \
  -d '{"text":"ВВП вырос быстрее ожиданий","analysis_model":"tfidf-logreg"}'
```

## Chat SSE endpoint

`api-gateway` отдает поток событий выполнения диалогового сценария:

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H 'Content-Type: application/json' \
  -H 'Accept: text/event-stream' \
  -d '{"question":"Что значит рост ВВП?","analysis_model":"tfidf-logreg","limit":5}'
```

Поток отправляет технические события этапов: `chat_started`, `search_started`,
`sources_found`, `analysis_started`, `analysis_completed`, `answer_started`,
`answer_completed` и `done`. Если нижестоящий сервис падает после старта
streaming-ответа, gateway отправляет одно безопасное событие `error` и закрывает поток.

## Загрузка новостей в News Service

`news-service` загружает локальные CSV-новости и индексирует их через
`retrieval-service`.

Ожидаемые смысловые колонки CSV:

- title: `title` or `headline`
- text: `text`, `content`, `body` or `description`
- source: `source` or `publisher`

Локальный предпросмотр:

```bash
NEWS_SERVICE_NEWS_DATASET_PATH=research/tests/fixtures/news_impact_sample.csv \
  uv run --package economic-news-news-service granian news_service.main.app:app \
  --interface asgi --host 0.0.0.0 --port 8004

curl 'http://localhost:8004/api/v1/news/preview?limit=3'
```

Индексация через `retrieval-service`:

```bash
curl -X POST http://localhost:8004/api/v1/news/index \
  -H 'Content-Type: application/json' \
  -d '{"limit": 10}'
```

Постановка той же индексации в фоновую задачу:

```bash
curl -X POST http://localhost:8004/api/v1/news/index/jobs \
  -H 'Content-Type: application/json' \
  -d '{"limit": 10}'
```

Задача выполняется `news-worker` через Taskiq и Redis. Статусные события
публикуются через FastStream в Redis-канал из `NEWS_SERVICE_INDEX_EVENTS_CHANNEL`.

## Демо-сценарий для защиты курсовой

В репозитории есть небольшой русскоязычный набор экономических новостей:
`data/raw/economic_news.csv`. Он нужен для локальной демонстрации и делает
сценарий защиты воспроизводимым.

Запуск всего стека:

```bash
just demo-up
```

Во втором терминале запустите smoke-проверку:

```bash
just demo-smoke
```

Smoke-проверка подтверждает:

- health endpoints `api-gateway` и `news-service`;
- предпросмотр CSV через `news-service`;
- детерминированную индексацию через `news-service`;
- создание фоновой задачи индексации через Taskiq/Redis;
- SSE-поток диалога из `api-gateway`;
- доступность frontend HTML.

Проверка только backend-части:

```bash
just demo-smoke-no-frontend
```

Остановка стека:

```bash
just demo-down
```

## Frontend-чат

React UI является реальным API-клиентом локального backend.

Локальная разработка:

```bash
npm --prefix frontend/web install
npm --prefix frontend/web run dev -- --host 0.0.0.0 --port 5173
```

Открыть:

```text
http://localhost:5173
```

Ожидаемые backend-сервисы:

- `api-gateway` on `http://localhost:8000`;
- `news-service` on `http://localhost:8004`.

Vite проксирует `/api-gateway/*` и `/news-service/*` в локальные сервисы.
Production nginx image использует те же относительные пути внутри Docker Compose.

В левой панели UI доступны две фоновые аналитические операции:

- `Сформировать ML-отчет` — переобучает и сравнивает классификаторы через
  `analysis-worker`, сохраняет отчет в `reports/ml/model-report.json`;
- `Сформировать прогноз по темам` — берет проиндексированные новости из
  `retrieval-service`, объединяет похожие новости через Qdrant-neighborhood,
  агрегирует impact-сигналы и сохраняет осторожный прогноз в
  `reports/topic-forecast/latest.json`.

Для прогноза сначала нужно загрузить и проиндексировать новости через UI или
`news-service`; без индекса панель вернет пустой отчет.

Проверки:

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
