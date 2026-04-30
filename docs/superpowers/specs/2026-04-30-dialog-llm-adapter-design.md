# Design: LLM adapter for dialog-service

Дата: 2026-04-30

## 1. Цель

Следующий этап делает `dialog-service` настоящим сервисом генерации ответа на основе языковой модели, а не только deterministic template generator.

Нужно добавить configurable adapter к локальному OpenAI-compatible LLM endpoint, который можно поднять через `llama.cpp` server или совместимый локальный runtime. При этом `TemplateDialogGenerator` остается fallback-режимом для тестов, CI и демонстрации на машине без модели.

Этап закрывает важную часть темы курсовой: автоматическая диалоговая система должна формировать ответ через языковую модель, используя RAG-контекст и результаты классификации экономического влияния.

## 2. Scope

### In scope

- Новый `LlmDialogGenerator` в `apps/dialog-service`.
- Prompt builder для экономического анализа новостей.
- HTTP client к OpenAI-compatible `/v1/chat/completions`.
- Settings для выбора generator kind и LLM endpoint.
- DI wiring в Dishka container.
- Тесты prompt builder, LLM adapter, settings/container и API integration.
- Docker Compose env для `dialog-service`.
- Документация запуска локальной модели.

### Out of scope

- SSE streaming.
- React UI.
- Автоматическое скачивание GGUF модели.
- Запуск отдельного model service в compose.
- История диалогов в PostgreSQL.
- Retry/backoff policy сверх простого timeout/error mapping.

## 3. Generator modes

`dialog-service` получает два режима генерации:

- `template`: текущий deterministic generator, default для CI и локального запуска без LLM.
- `llm`: новый adapter к локальному OpenAI-compatible endpoint.

Settings:

- `DIALOG_GENERATOR_KIND`, default `"template"`, values: `"template" | "llm"`;
- `DIALOG_GENERATOR_NAME`, default `"template-dialog-generator"`;
- `DIALOG_LLM_BASE_URL`, default `"http://localhost:8080"`;
- `DIALOG_LLM_MODEL`, default `"Qwen3-0.6B-Instruct-GGUF"`;
- `DIALOG_LLM_TIMEOUT_SECONDS`, default `30.0`;
- `DIALOG_LLM_TEMPERATURE`, default `0.2`;
- `DIALOG_LLM_MAX_TOKENS`, default `512`.

Для Docker Compose можно переопределить:

```yaml
DIALOG_GENERATOR_KIND: "template"
DIALOG_LLM_BASE_URL: "http://host.docker.internal:8080"
```

Compose по умолчанию остается легким и не запускает LLM container, чтобы не раздувать стек и не требовать скачивания модели.

## 4. LLM HTTP adapter

Новый infrastructure component:

```text
apps/dialog-service/src/dialog_service/infrastructure/
  llm_generator.py
```

`LlmDialogGenerator` реализует `DialogGenerator` Protocol:

```python
async def generate(
    question: DialogQuestion,
    context: list[DialogContextItem],
    impact_summaries: list[DialogImpactItem],
    language: str,
) -> DialogGeneration
```

Adapter вызывает:

```http
POST {DIALOG_LLM_BASE_URL}/v1/chat/completions
```

Payload:

```json
{
  "model": "Qwen3-0.6B-Instruct-GGUF",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "temperature": 0.2,
  "max_tokens": 512,
  "stream": false
}
```

Response parser берет `choices[0].message.content`. Пустой или malformed response мапится в `DialogGeneratorUnavailableError`.

Для HTTP использовать `zapros`, чтобы не вводить второй стиль async HTTP clients. `dialog-service` получает dependency `zapros>=0.10`.

## 5. Prompt strategy

Prompt builder остается infrastructure-level, потому что это деталь генератора, а не domain policy.

System prompt:

- отвечает на русском языке, если `language="ru"`;
- использует только переданный контекст;
- не выдумывает источники и факты;
- разделяет экономическое влияние и финансовую рекомендацию;
- не обещает точные прогнозы рынка.

User prompt включает:

- вопрос пользователя;
- список найденных новостей с `id`, `title`, `source`, `score`, `text`;
- summaries анализа по `news_id`: `impact`, `confidence`, `explanation`;
- требуемый формат ответа:
  1. короткий вывод;
  2. факторы влияния;
  3. оговорка о том, что это аналитическая оценка, а не финансовая рекомендация.

Если контекста нет, LLM получает явную инструкцию сказать, что релевантные новости не найдены, без попытки ответить из общих знаний.

## 6. Domain and boundaries

Domain/application слой не зависит от HTTP DTO и LLM payload.

Разрешенные зависимости:

- `domain`: only value objects/errors;
- `application`: only `DialogGenerator` Protocol and domain values;
- `infrastructure`: prompt builder, Zapros client, OpenAI-compatible DTO parsing;
- `presentation`: existing API contracts mapping.

`TemplateDialogGenerator` и `LlmDialogGenerator` оба используют `DialogImpactItem`, а не shared contract DTO.

## 7. Error handling

LLM adapter должен мапить в `DialogGeneratorUnavailableError`:

- network/timeout errors;
- HTTP status `>= 400`;
- malformed JSON;
- missing `choices[0].message.content`;
- blank generated answer.

Public API behavior остается прежним:

```json
503 {"detail": "dialog-service is unavailable"}
```

Internal transport details не должны попадать в response.

## 8. Testing

Минимальные тесты:

- settings defaults and env overrides;
- container resolves `TemplateDialogGenerator` for `template`;
- container resolves `LlmDialogGenerator` for `llm`;
- prompt builder includes question, news context, impact summaries and disclaimer constraints;
- LLM adapter sends OpenAI-compatible payload;
- LLM adapter parses successful response into `DialogGeneration`;
- LLM adapter maps HTTP/transport/malformed/blank answer errors;
- API route still works in template mode;
- full suite: `ruff`, `ty`, `pytest`, `docker compose config`, Docker build for `dialog-service`.

## 9. Acceptance criteria

- `DIALOG_GENERATOR_KIND=template` keeps current behavior and all existing tests pass.
- `DIALOG_GENERATOR_KIND=llm` makes `dialog-service` call the configured local LLM endpoint.
- Generated `DialogGeneration.metadata` includes:
  - `generator_kind`;
  - `model_name`;
  - `context_count`;
  - `impact_summary_count`.
- Gateway `/api/v1/chat` does not need contract changes.
- Docker image for `dialog-service` builds with the new dependency.
- README or docs contain a minimal command example for local llama.cpp-compatible server.

## 10. Implementation notes

Recommended local model command, documented but not automated:

```bash
llama-server -m models/Qwen3-0.6B-Instruct-Q8_0.gguf --host 0.0.0.0 --port 8080
```

If the selected quantization is too heavy for a local machine, the same adapter can point to a smaller GGUF quantization without code changes.
