# Design: dialog-service and gateway chat orchestration

Дата: 2026-04-29

## 1. Цель

Следующий этап проекта добавляет первый полноценный диалоговый сценарий по теме курсовой: пользователь задает вопрос об экономической новости или событии, а система ищет релевантные новости, оценивает их экономическое влияние и формирует связный ответ.

В рамках этого этапа реализуются:

- новый микросервис `dialog-service`;
- typed contracts для генерации диалогового ответа;
- orchestration endpoint в `api-gateway`;
- Docker Compose wiring для `dialog-service`.

SSE streaming, React UI и реальный `llama.cpp` adapter остаются следующими этапами. В этом PR нужен стабильный вертикальный срез без лишнего кода.

## 2. Scope

### In scope

- `packages/contracts`: диалоговые DTO и gateway chat DTO.
- `apps/dialog-service`: DDD/layered сервис с FastAPI, Dishka, Granian и тестами.
- `api-gateway`: HTTP client для `dialog-service` через Zapros, chat use case и route.
- `deploy`: Dockerfile и compose service для `dialog-service`.
- Тесты на contracts, use cases, HTTP clients, routes, DI и compose build.

### Out of scope

- SSE streaming.
- React UI.
- Реальный запуск локальной LLM через `llama.cpp`.
- Хранение истории диалогов в PostgreSQL.
- Taskiq/FastStream фоновые задачи.
- Авторизация.

## 3. Contracts

Добавляются DTO в `packages/contracts/src/economic_news_contracts/dialog.py`.

`DialogContextNews` описывает найденную новость:

- `id`;
- `title`;
- `text`;
- `source`;
- `score`;
- `published_at`;
- `metadata`.

`DialogImpactSummary` описывает результат анализа новости:

- `news_id`;
- `model_name`;
- `impact`;
- `confidence`;
- `explanation`.

`GenerateDialogRequest` содержит:

- `question`;
- `context`;
- `impact_summaries`;
- `language`, default `"ru"`.

`GenerateDialogResponse` содержит:

- `answer`;
- `used_context_ids`;
- `model_name`;
- `metadata`.

Для gateway chat добавляется `packages/contracts/src/economic_news_contracts/chat.py`.

`ChatRequest` содержит:

- `question`;
- `analysis_model`;
- `limit`;
- `source`.

`ChatResponse` содержит:

- `answer`;
- `sources`;
- `impact_summaries`;
- `analysis_model`;
- `metadata`.

`question` валидируется как непустая строка. `limit` ограничивается теми же рамками, что и `SearchNewsRequest`, чтобы gateway не запрашивал чрезмерный контекст.

## 4. Dialog Service

Структура сервиса следует текущему шаблону:

```text
apps/dialog-service/
  src/dialog_service/
    domain/
    application/
    infrastructure/
    presentation/
    main/
  tests/
```

### Domain

Минимальный domain слой содержит:

- `DialogQuestion`;
- `DialogContextItem`;
- `DialogGeneration`.

Domain отвечает только за нормализацию и инварианты: непустой вопрос, непустой ответ, immutable metadata. Экономический анализ не дублируется в domain, потому что его делает `analysis-service`.

### Application

Application слой содержит:

- `DialogGenerator` Protocol;
- `GenerateDialogAnswer` use case.

Use case принимает `GenerateDialogRequest`, преобразует contracts в domain values, вызывает `DialogGenerator` и возвращает `GenerateDialogResponse`.

### Infrastructure

На этом этапе используется `TemplateDialogGenerator`.

Он не имитирует интеллект LLM как отдельную бизнес-логику, а выполняет роль deterministic локального генератора:

- кратко отвечает на вопрос;
- перечисляет ключевые выводы по найденным новостям;
- учитывает `impact_summaries`;
- возвращает `model_name="template-dialog-generator"`;
- добавляет metadata с количеством использованных источников.

Такой adapter нужен, чтобы быстро получить надежный end-to-end сценарий. Позже его можно заменить на `LlamaCppDialogGenerator`, не меняя contracts и use case.

### Presentation

FastAPI route:

- `POST /api/v1/dialog/generate`;
- request: `GenerateDialogRequest`;
- response: `GenerateDialogResponse`.

Ошибки domain validation отдаются как `422`. Ошибки генератора отдаются как `503` с public detail `"dialog-service is unavailable"`.

## 5. Gateway Chat Orchestration

`api-gateway` получает новый endpoint:

- `POST /api/v1/chat`;
- request: `ChatRequest`;
- response: `ChatResponse`.

Data flow:

1. Gateway принимает вопрос пользователя.
2. Gateway вызывает `retrieval-service` через существующий `RetrievalClient.search`.
3. Для каждой найденной новости gateway вызывает `analysis-service` через существующий `AnalysisClient.analyze`.
4. Gateway вызывает `dialog-service` через новый `DialogClient.generate`.
5. Gateway возвращает ответ, источники, summaries анализа и metadata.

Gateway остается thin facade, но orchestration живет в application use case, а не в router.

Новые application элементы:

- `DialogClient` Protocol;
- `ChatUseCase`;
- `DialogServiceUnavailableError`.

Новая infrastructure реализация:

- `ZaprosDialogClient`.

Новый route ловит:

- `AnalysisServiceUnavailableError`;
- `RetrievalServiceUnavailableError`;
- `DialogServiceUnavailableError`.

Все они мапятся в `503`, но с разным public detail, чтобы на демо было понятно, какой микросервис недоступен.

## 6. Prompt Strategy

Prompt builder остается внутри `dialog-service` infrastructure рядом с `TemplateDialogGenerator`, потому что сейчас это часть генератора, а не самостоятельная domain policy.

Ответ должен быть на русском языке по умолчанию и иметь структуру:

1. короткий прямой ответ;
2. список факторов влияния;
3. осторожная оговорка, что это аналитическая оценка на основе доступных новостей, а не финансовая рекомендация.

В тексте ответа нельзя утверждать, что модель знает больше, чем передано в контексте.

## 7. Settings and DI

`dialog-service` получает settings:

- `service_name="dialog-service"`;
- `version="0.1.0"`;
- `generator_name="template-dialog-generator"`.

`api-gateway` получает settings:

- `dialog_service_url: AnyHttpUrl = AnyHttpUrl("http://dialog-service:8000")`;
- `dialog_service_timeout_seconds: float = 5.0`.

Environment variables:

- `API_GATEWAY_DIALOG_SERVICE_URL`;
- `API_GATEWAY_DIALOG_SERVICE_TIMEOUT_SECONDS`.

Dishka providers создаются по тем же паттернам, что для analysis/retrieval.

## 8. Docker Compose

Добавляется `deploy/docker/dialog-service.Dockerfile`.

Compose получает service:

```yaml
dialog-service:
  build:
    context: ..
    dockerfile: deploy/docker/dialog-service.Dockerfile
  env_file:
    - ../.env.example
  ports:
    - "8003:8000"
```

`api-gateway` получает:

- `API_GATEWAY_DIALOG_SERVICE_URL: "http://dialog-service:8000"`;
- `depends_on: dialog-service`.

## 9. Error Handling

`dialog-service`:

- validation errors: standard FastAPI `422`;
- generator unavailable: `503 {"detail": "dialog-service is unavailable"}`.

`api-gateway`:

- retrieval unavailable: existing `503 {"detail": "retrieval-service is unavailable"}`;
- analysis unavailable: existing `503 {"detail": "analysis-service is unavailable"}`;
- dialog unavailable: new `503 {"detail": "dialog-service is unavailable"}`.

Gateway не раскрывает transport details downstream-сервисов.

## 10. Testing

Минимальный test plan:

- contracts tests for dialog/chat DTO validation and serialization;
- dialog domain tests;
- dialog use case tests;
- `TemplateDialogGenerator` tests;
- dialog API tests;
- dialog container/settings tests;
- gateway `ZaprosDialogClient` tests;
- gateway `ChatUseCase` tests with fake clients;
- gateway route tests for success and each 503 path;
- compose config and Docker build for `dialog-service` and `api-gateway`.

Full verification:

```bash
uv run ruff check apps packages research
uv run ty check apps packages research
uv run pytest packages apps research/tests -v -W error
docker compose -f deploy/compose.yaml config
docker compose -f deploy/compose.yaml build dialog-service api-gateway
```

## 11. Success Criteria

- `dialog-service` can generate deterministic Russian dialog answers from context and impact summaries.
- `api-gateway` exposes `POST /api/v1/chat`.
- Chat flow uses existing analysis and retrieval service clients instead of duplicating their logic.
- All new boundaries use `typing.Protocol` in application layer.
- The implementation follows the existing DDD/layered structure without generic abstractions added only for future use.
- The feature can be run locally through Docker Compose.
