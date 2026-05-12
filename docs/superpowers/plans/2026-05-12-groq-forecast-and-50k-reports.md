# Groq Forecast And 50k Reports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Подключить Groq `qwen/qwen3-32b` как качественный LLM-режим, добавить генерацию Groq-прогноза по кнопке для темы или отдельной новости и запустить ML-отчет/тематический прогноз на локальных 50 000 новостях.

**Architecture:** `dialog-service` остается владельцем чат-ответов и получает новый provider kind `groq` поверх OpenAI-compatible Chat Completions через `zapros`. `analysis-service` остается владельцем экономического анализа и получает отдельный use case для LLM-прогноза по уже сформированной теме/новости, чтобы Groq вызывался только по кнопке и не расходовал лимиты при каждом построении отчета. React UI вызывает новый endpoint и показывает результат прямо в карточке темы или новости.

**Tech Stack:** Python 3.12, FastAPI, Dishka, Pydantic Settings, zapros, taskiq, Redis, React, TypeScript, Vitest, Docker Compose, Groq OpenAI-compatible API.

---

## File Structure

- Modify: `apps/dialog-service/src/dialog_service/infrastructure/llm_generator.py`
  - Add optional bearer auth headers and configurable `generator_kind` metadata.
- Modify: `apps/dialog-service/src/dialog_service/main/settings.py`
  - Add `DialogGeneratorKind.GROQ`, `groq_base_url`, `groq_model`, `groq_api_key`.
- Modify: `apps/dialog-service/src/dialog_service/main/container.py`
  - Resolve Groq mode to `LlmDialogGenerator`.
- Modify: `apps/dialog-service/tests/test_llm_generator.py`
  - Cover auth header and Groq metadata.
- Modify: `apps/dialog-service/tests/test_dialog_container.py`
  - Cover Groq settings and container resolution.
- Modify: `packages/contracts/src/economic_news_contracts/analysis.py`
  - Add request/response DTOs for LLM forecast generation.
- Create: `apps/analysis-service/src/analysis_service/infrastructure/groq_forecast_client.py`
  - Groq client adapter through `zapros`.
- Modify: `apps/analysis-service/src/analysis_service/application/ports.py`
  - Add `EconomicForecastGenerator` Protocol.
- Modify: `apps/analysis-service/src/analysis_service/application/use_cases.py`
  - Add use case that builds Groq forecast from latest topic forecast.
- Modify: `apps/analysis-service/src/analysis_service/main/settings.py`
  - Add Groq endpoint, model, API key and generation parameters.
- Modify: `apps/analysis-service/src/analysis_service/main/container.py`
  - Provide forecast generator and use case through Dishka.
- Modify: `apps/analysis-service/src/analysis_service/presentation/router.py`
  - Add `POST /api/v1/topic-forecast/groq-predictions`.
- Test: `apps/analysis-service/tests/test_groq_forecast_client.py`
- Test: `apps/analysis-service/tests/test_groq_forecast_api.py`
- Modify: `frontend/web/src/app/types.ts`
  - Add Groq forecast request/response types.
- Modify: `frontend/web/src/api/analysis.ts`
  - Add API function for Groq forecast generation.
- Modify: `frontend/web/src/components/TopicForecastPanel.tsx`
  - Add buttons and result panels for every topic and every news item.
- Modify: `frontend/web/src/app/App.tsx`
  - Own Groq forecast state and pass callbacks to the panel.
- Modify: `frontend/web/src/app/App.module.css`
  - Style compact forecast actions/results.
- Modify: `frontend/web/src/api/analysis.test.ts`
  - Cover new API call.
- Modify: `frontend/web/src/app/App.test.tsx`
  - Cover topic/news Groq buttons.
- Modify: `deploy/compose.yaml`
  - Set 50k report dataset path and Groq env passthrough.
- Modify: `.env.example`
  - Document Groq variables and 50k dataset/report defaults.

---

### Task 1: Dialog Groq Mode

**Files:**
- Modify: `apps/dialog-service/src/dialog_service/infrastructure/llm_generator.py`
- Modify: `apps/dialog-service/src/dialog_service/main/settings.py`
- Modify: `apps/dialog-service/src/dialog_service/main/container.py`
- Test: `apps/dialog-service/tests/test_llm_generator.py`
- Test: `apps/dialog-service/tests/test_dialog_container.py`

- [ ] **Step 1: Write failing LLM generator test for bearer auth and Groq metadata**

Append to `apps/dialog-service/tests/test_llm_generator.py`:

```python
@pytest.mark.asyncio
async def test_llm_generator_sends_bearer_token_and_provider_metadata() -> None:
    transport = FakeZaprosClient(FakeResponse(200, llm_payload("Прогноз сформирован.")))
    generator = LlmDialogGenerator(
        base_url="https://api.groq.com/openai",
        model_name="qwen/qwen3-32b",
        timeout_seconds=30.0,
        temperature=0.2,
        max_tokens=512,
        api_key="test-groq-key",
        generator_kind="groq",
        client=transport,
    )

    generation = await generator.generate(
        question=DialogQuestion("Что будет с рынком?"),
        context=dialog_context(),
        impact_summaries=impact_summaries(),
        language="ru",
    )

    url, payload, headers = transport.calls[0]
    assert url == "https://api.groq.com/openai/v1/chat/completions"
    assert payload["model"] == "qwen/qwen3-32b"
    assert headers == {
        "Authorization": "Bearer test-groq-key",
        "Content-Type": "application/json",
    }
    assert generation.metadata["generator_kind"] == "groq"
    assert generation.metadata["model_name"] == "qwen/qwen3-32b"
```

Update the fake client in the same file so the test can inspect headers:

```python
class FakeZaprosClient:
    def __init__(self, response: FakeResponse | MalformedJsonResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, object], dict[str, str] | None]] = []

    async def post(
        self,
        url: str,
        json: dict[str, object],
        headers: dict[str, str] | None = None,
    ) -> FakeResponse | MalformedJsonResponse:
        self.calls.append((url, json, headers))
        return self.response
```

Adjust existing assertions that unpack calls:

```python
url, payload, _headers = transport.calls[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest apps/dialog-service/tests/test_llm_generator.py::test_llm_generator_sends_bearer_token_and_provider_metadata -v
```

Expected: FAIL because `LlmDialogGenerator.__init__` does not accept `api_key` and `generator_kind`.

- [ ] **Step 3: Implement minimal authenticated OpenAI-compatible generator support**

Modify `apps/dialog-service/src/dialog_service/infrastructure/llm_generator.py` constructor:

```python
        api_key: str | None = None,
        generator_kind: str = "llm",
        prompt_builder: DialogPromptBuilder | None = None,
```

Store the values:

```python
        self._api_key = api_key
        self._generator_kind = generator_kind
```

Change metadata in `generate`:

```python
                "generator_kind": self._generator_kind,
```

Add helper:

```python
    def _headers(self) -> dict[str, str] | None:
        if self._api_key is None:
            return None
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
```

Use headers in `_post`:

```python
        headers = self._headers()
        try:
            if self._client is not None:
                return cast(_ZaprosResponse, await self._client.post(url, json=payload, headers=headers))
            async with self._client_factory(self._timeout_seconds) as client:
                return cast(_ZaprosResponse, await client.post(url, json=payload, headers=headers))
```

- [ ] **Step 4: Write failing settings/container tests for Groq mode**

Append `DIALOG_GROQ_BASE_URL`, `DIALOG_GROQ_MODEL`, `DIALOG_GROQ_API_KEY` to `_DIALOG_ENV_KEYS` in `apps/dialog-service/tests/test_dialog_container.py`.

Append tests:

```python
def test_dialog_settings_include_groq_defaults(isolate_dialog_settings: None) -> None:
    settings = DialogServiceSettings()

    assert str(settings.groq_base_url) == "https://api.groq.com/openai/"
    assert settings.groq_model == "qwen/qwen3-32b"
    assert settings.groq_api_key is None


def test_dialog_settings_read_prefixed_groq_env(
    isolate_dialog_settings: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DIALOG_GENERATOR_KIND", "groq")
    monkeypatch.setenv("DIALOG_GROQ_BASE_URL", "https://api.groq.com/openai")
    monkeypatch.setenv("DIALOG_GROQ_MODEL", "qwen/qwen3-32b")
    monkeypatch.setenv("DIALOG_GROQ_API_KEY", "secret-key")

    settings = DialogServiceSettings()

    assert settings.generator_kind == DialogGeneratorKind.GROQ
    assert str(settings.groq_base_url) == "https://api.groq.com/openai/"
    assert settings.groq_model == "qwen/qwen3-32b"
    assert settings.groq_api_key is not None
    assert settings.groq_api_key.get_secret_value() == "secret-key"


@pytest.mark.asyncio
async def test_container_resolves_llm_generator_for_groq_mode(
    isolate_dialog_settings: None,
) -> None:
    settings = DialogServiceSettings(
        generator_kind=DialogGeneratorKind.GROQ,
        groq_api_key="secret-key",
    )
    container: AsyncContainer = create_container(settings)

    try:
        generator = await container.get(DialogGenerator)
    finally:
        await container.close()

    assert isinstance(generator, LlmDialogGenerator)
```

- [ ] **Step 5: Run settings/container tests to verify failure**

Run:

```bash
uv run pytest apps/dialog-service/tests/test_dialog_container.py::test_dialog_settings_include_groq_defaults apps/dialog-service/tests/test_dialog_container.py::test_dialog_settings_read_prefixed_groq_env apps/dialog-service/tests/test_dialog_container.py::test_container_resolves_llm_generator_for_groq_mode -v
```

Expected: FAIL because settings and enum do not define Groq.

- [ ] **Step 6: Implement Groq settings and container wiring**

Modify `apps/dialog-service/src/dialog_service/main/settings.py`:

```python
from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
```

Add enum value:

```python
class DialogGeneratorKind(StrEnum):
    TEMPLATE = "template"
    LLM = "llm"
    GROQ = "groq"
```

Add settings:

```python
    groq_base_url: AnyHttpUrl = AnyHttpUrl("https://api.groq.com/openai")
    groq_model: str = Field(default="qwen/qwen3-32b", min_length=1)
    groq_api_key: SecretStr | None = None
```

Replace the model validator with:

```python
    @field_validator("llm_model", "groq_model")
    @classmethod
    def validate_model_name(cls, value: str) -> str:
        stripped_value = value.strip()
        if not stripped_value:
            msg = "model name must not be blank"
            raise ValueError(msg)
        return stripped_value
```

Modify `apps/dialog-service/src/dialog_service/main/container.py`:

```python
        if settings.generator_kind == DialogGeneratorKind.GROQ:
            return LlmDialogGenerator(
                base_url=str(settings.groq_base_url),
                model_name=settings.groq_model,
                timeout_seconds=settings.llm_timeout_seconds,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                api_key=settings.groq_api_key.get_secret_value() if settings.groq_api_key else None,
                generator_kind="groq",
                prompt_builder=prompt_builder,
            )
```

- [ ] **Step 7: Run dialog tests**

Run:

```bash
uv run pytest apps/dialog-service/tests/test_llm_generator.py apps/dialog-service/tests/test_dialog_container.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit dialog Groq mode**

Run:

```bash
git add apps/dialog-service/src/dialog_service/infrastructure/llm_generator.py apps/dialog-service/src/dialog_service/main/settings.py apps/dialog-service/src/dialog_service/main/container.py apps/dialog-service/tests/test_llm_generator.py apps/dialog-service/tests/test_dialog_container.py
git commit -m "feat: добавить groq режим диалога"
```

---

### Task 2: Analysis Groq Forecast Contracts And Client

**Files:**
- Modify: `packages/contracts/src/economic_news_contracts/analysis.py`
- Create: `apps/analysis-service/src/analysis_service/infrastructure/groq_forecast_client.py`
- Modify: `apps/analysis-service/src/analysis_service/application/ports.py`
- Modify: `apps/analysis-service/src/analysis_service/main/settings.py`
- Test: `apps/analysis-service/tests/test_groq_forecast_client.py`

- [ ] **Step 1: Write failing contract tests**

Create `apps/analysis-service/tests/test_groq_forecast_client.py`:

```python
import pytest
from analysis_service.infrastructure.groq_forecast_client import GroqEconomicForecastGenerator
from economic_news_contracts.analysis import (
    GroqForecastRequest,
    GroqForecastScope,
    ImpactLabel,
    TopicForecastItemResponse,
    TopicForecastNewsItemResponse,
)


class FakeResponse:
    status = 200

    def __init__(self, content: str) -> None:
        self.json = {"choices": [{"message": {"content": content}}]}
        self.read_count = 0

    async def aread(self) -> bytes:
        self.read_count += 1
        return b""


class FakeZaprosClient:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, object], dict[str, str]]] = []

    async def post(
        self,
        url: str,
        json: dict[str, object],
        headers: dict[str, str],
    ) -> FakeResponse:
        self.calls.append((url, json, headers))
        return self.response


def topic() -> TopicForecastItemResponse:
    return TopicForecastItemResponse(
        topic_id="topic-1",
        title="Рост ВВП и снижение инфляции",
        summary="Тема объединяет новости о росте ВВП и снижении инфляции.",
        overall_impact=ImpactLabel.POSITIVE,
        confidence=0.82,
        positive_count=2,
        neutral_count=1,
        negative_count=0,
        forecast="Базовый прогноз.",
        arguments=["Преобладают позитивные сигналы."],
        risks=["Прогноз зависит от полноты данных."],
        news=[
            TopicForecastNewsItemResponse(
                id="news-1",
                title="GDP grows",
                source="demo",
                impact=ImpactLabel.POSITIVE,
                score=0.91,
            ),
        ],
    )


@pytest.mark.asyncio
async def test_groq_forecast_generator_sends_prompt_and_parses_answer() -> None:
    client = FakeZaprosClient(FakeResponse("Рынок может получить поддержку."))
    generator = GroqEconomicForecastGenerator(
        base_url="https://api.groq.com/openai",
        api_key="test-key",
        model_name="qwen/qwen3-32b",
        timeout_seconds=30.0,
        temperature=0.2,
        max_tokens=700,
        client=client,
    )

    result = await generator.generate(
        request=GroqForecastRequest(
            scope=GroqForecastScope.TOPIC,
            model_name="tfidf-logreg",
            topic=topic(),
            news_id=None,
        )
    )

    url, payload, headers = client.calls[0]
    assert url == "https://api.groq.com/openai/v1/chat/completions"
    assert headers["Authorization"] == "Bearer test-key"
    assert payload["model"] == "qwen/qwen3-32b"
    assert payload["temperature"] == 0.2
    assert payload["max_tokens"] == 700
    assert result.provider == "groq"
    assert result.model_name == "qwen/qwen3-32b"
    assert result.scope == GroqForecastScope.TOPIC
    assert result.prediction == "Рынок может получить поддержку."
    assert "не финансовая рекомендация" in result.disclaimer
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest apps/analysis-service/tests/test_groq_forecast_client.py -v
```

Expected: FAIL because DTOs and client do not exist.

- [ ] **Step 3: Add Groq forecast DTOs**

Modify `packages/contracts/src/economic_news_contracts/analysis.py`:

```python
class GroqForecastScope(StrEnum):
    TOPIC = "topic"
    NEWS = "news"


class GroqForecastRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: GroqForecastScope
    model_name: str = Field(min_length=1)
    topic: TopicForecastItemResponse
    news_id: str | None = None


class GroqForecastResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    scope: GroqForecastScope
    target_id: str = Field(min_length=1)
    prediction: str = Field(min_length=1)
    disclaimer: str = Field(default="Это аналитический сценарий, а не финансовая рекомендация.")
    metadata: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 4: Add application Protocol**

Modify `apps/analysis-service/src/analysis_service/application/ports.py`:

```python
from economic_news_contracts.analysis import GroqForecastRequest, GroqForecastResponse
```

Add:

```python
class EconomicForecastGenerator(Protocol):
    async def generate(self, request: GroqForecastRequest) -> GroqForecastResponse:
        """Generate an LLM-based economic forecast for a topic or one news item."""
```

- [ ] **Step 5: Implement Groq client**

Create `apps/analysis-service/src/analysis_service/infrastructure/groq_forecast_client.py`:

```python
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Protocol, cast

from economic_news_contracts.analysis import (
    GroqForecastRequest,
    GroqForecastResponse,
    GroqForecastScope,
    TopicForecastNewsItemResponse,
)
from zapros import AsyncClient, AsyncStdNetworkHandler


class GroqForecastGenerationError(RuntimeError):
    """Raised when Groq forecast generation fails."""


class _ZaprosResponse(Protocol):
    status: int
    json: object

    async def aread(self) -> bytes: ...


def _make_zapros_client(timeout_seconds: float) -> Any:
    return AsyncClient(handler=AsyncStdNetworkHandler(total_timeout=timeout_seconds))


class GroqEconomicForecastGenerator:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str | None,
        model_name: str,
        timeout_seconds: float,
        temperature: float,
        max_tokens: int,
        client: Any | None = None,
        client_factory: Callable[[float], Any] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model_name = model_name
        self._timeout_seconds = timeout_seconds
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._client = client
        self._client_factory = client_factory or _make_zapros_client

    async def generate(self, request: GroqForecastRequest) -> GroqForecastResponse:
        if not self._api_key:
            raise GroqForecastGenerationError("GROQ API key is not configured")

        payload = self._build_payload(request)
        response = await self._post(payload)
        if response.status >= 400:
            raise GroqForecastGenerationError("Groq forecast request failed")

        await response.aread()
        prediction = self._parse_content(response.json)
        return GroqForecastResponse(
            provider="groq",
            model_name=self._model_name,
            scope=request.scope,
            target_id=request.news_id if request.scope == GroqForecastScope.NEWS and request.news_id else request.topic.topic_id,
            prediction=prediction,
            metadata={
                "source_model": request.model_name,
                "topic_id": request.topic.topic_id,
                "news_count": len(request.topic.news),
            },
        )

    def _build_payload(self, request: GroqForecastRequest) -> dict[str, object]:
        return {
            "model": self._model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Ты экономический аналитик. Сформируй осторожный сценарный прогноз "
                        "на русском языке. Не давай инвестиционных рекомендаций."
                    ),
                },
                {"role": "user", "content": self._build_prompt(request)},
            ],
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "stream": False,
        }

    def _build_prompt(self, request: GroqForecastRequest) -> str:
        news_items = self._selected_news(request)
        news_lines = "\n".join(
            f"- {item.title}; source={item.source}; impact={item.impact}; score={item.score}"
            for item in news_items
        )
        return (
            f"Режим: {request.scope.value}\n"
            f"Модель классификации: {request.model_name}\n"
            f"Тема: {request.topic.title}\n"
            f"Сводка: {request.topic.summary}\n"
            f"Общее влияние: {request.topic.overall_impact}\n"
            f"Уверенность: {request.topic.confidence}\n"
            f"Базовый прогноз: {request.topic.forecast}\n"
            f"Новости:\n{news_lines}\n\n"
            "Верни 3 коротких абзаца: прогноз, почему это важно, ключевые риски."
        )

    def _selected_news(self, request: GroqForecastRequest) -> list[TopicForecastNewsItemResponse]:
        if request.scope == GroqForecastScope.NEWS and request.news_id:
            return [item for item in request.topic.news if item.id == request.news_id]
        return request.topic.news

    async def _post(self, payload: dict[str, object]) -> _ZaprosResponse:
        url = f"{self._base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            if self._client is not None:
                return cast(_ZaprosResponse, await self._client.post(url, json=payload, headers=headers))
            async with self._client_factory(self._timeout_seconds) as client:
                return cast(_ZaprosResponse, await client.post(url, json=payload, headers=headers))
        except Exception as error:
            raise GroqForecastGenerationError("Groq forecast request failed") from error

    def _parse_content(self, body: object) -> str:
        try:
            choices = self._field(body, "choices")
            first_choice = self._list_item(choices, 0)
            message = self._field(first_choice, "message")
            content = self._field(message, "content")
        except (IndexError, KeyError, TypeError) as error:
            raise GroqForecastGenerationError("Groq forecast response is invalid") from error

        if not isinstance(content, str) or not content.strip():
            raise GroqForecastGenerationError("Groq forecast response is empty")
        return content.strip()

    def _field(self, value: object, field_name: str) -> object:
        if not isinstance(value, Mapping):
            raise TypeError
        return cast(Mapping[str, object], value)[field_name]

    def _list_item(self, value: object, index: int) -> Any:
        if not isinstance(value, Sequence):
            raise TypeError
        return value[index]
```

- [ ] **Step 6: Add analysis Groq settings**

Modify `apps/analysis-service/src/analysis_service/main/settings.py`:

```python
from pydantic import AnyHttpUrl, Field, RedisDsn, SecretStr
```

Add:

```python
    groq_base_url: AnyHttpUrl = AnyHttpUrl("https://api.groq.com/openai")
    groq_model: str = Field(default="qwen/qwen3-32b", min_length=1)
    groq_api_key: SecretStr | None = None
    groq_timeout_seconds: float = Field(default=45.0, gt=0.0)
    groq_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    groq_max_tokens: int = Field(default=700, ge=1, le=4096)
```

- [ ] **Step 7: Run client tests**

Run:

```bash
uv run pytest apps/analysis-service/tests/test_groq_forecast_client.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit contracts and client**

Run:

```bash
git add packages/contracts/src/economic_news_contracts/analysis.py apps/analysis-service/src/analysis_service/application/ports.py apps/analysis-service/src/analysis_service/infrastructure/groq_forecast_client.py apps/analysis-service/src/analysis_service/main/settings.py apps/analysis-service/tests/test_groq_forecast_client.py
git commit -m "feat: добавить groq клиент экономического прогноза"
```

---

### Task 3: Analysis API For Per-Topic And Per-News Groq Prediction

**Files:**
- Modify: `apps/analysis-service/src/analysis_service/application/use_cases.py`
- Modify: `apps/analysis-service/src/analysis_service/main/container.py`
- Modify: `apps/analysis-service/src/analysis_service/presentation/router.py`
- Test: `apps/analysis-service/tests/test_groq_forecast_api.py`

- [ ] **Step 1: Write failing API test**

Create `apps/analysis-service/tests/test_groq_forecast_api.py`:

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from analysis_service.application.use_cases import GenerateGroqTopicForecast
from analysis_service.main.settings import AnalysisServiceSettings
from analysis_service.presentation.errors import register_error_handlers
from analysis_service.presentation.router import router
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider, setup_dishka
from economic_news_contracts.analysis import (
    GroqForecastRequest,
    GroqForecastResponse,
    GroqForecastScope,
)
from economic_news_framework.apps import create_service_app
from fastapi.testclient import TestClient


class StubGenerateGroqTopicForecast(GenerateGroqTopicForecast):
    def __init__(self) -> None:
        pass

    async def execute(self, request: GroqForecastRequest) -> GroqForecastResponse:
        return GroqForecastResponse(
            provider="groq",
            model_name="qwen/qwen3-32b",
            scope=request.scope,
            target_id=request.news_id or request.topic.topic_id,
            prediction="Сценарный прогноз сформирован.",
            metadata={"source_model": request.model_name},
        )


class GroqForecastProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> AnalysisServiceSettings:
        return AnalysisServiceSettings(use_static_classifier=True)

    @provide(scope=Scope.APP)
    def generate_groq_topic_forecast(self) -> GenerateGroqTopicForecast:
        return StubGenerateGroqTopicForecast()


def make_client() -> TestClient:
    app = create_service_app(service_name="analysis-service", routers=(router,))
    container = make_async_container(GroqForecastProvider(), FastapiProvider())
    setup_dishka(container=container, app=app)
    register_error_handlers(app)

    @asynccontextmanager
    async def close_container(_: object) -> AsyncIterator[None]:
        yield
        await container.close()

    app.router.lifespan_context = close_container
    return TestClient(app)


def test_post_groq_topic_prediction_returns_forecast() -> None:
    payload = {
        "scope": "topic",
        "model_name": "tfidf-logreg",
        "topic": {
            "topic_id": "topic-1",
            "title": "GDP grows",
            "summary": "GDP grows",
            "overall_impact": "positive",
            "confidence": 0.8,
            "positive_count": 1,
            "neutral_count": 0,
            "negative_count": 0,
            "forecast": "Базовый прогноз.",
            "arguments": ["Рост ВВП поддерживает ожидания."],
            "risks": [],
            "news": [
                {
                    "id": "news-1",
                    "title": "GDP grows",
                    "source": "demo",
                    "impact": "positive",
                    "score": None,
                }
            ],
        },
        "news_id": None,
    }

    with make_client() as client:
        response = client.post("/api/v1/topic-forecast/groq-predictions", json=payload)

    assert response.status_code == 200
    assert response.json()["provider"] == "groq"
    assert response.json()["model_name"] == "qwen/qwen3-32b"
    assert response.json()["target_id"] == "topic-1"
```

- [ ] **Step 2: Run API test to verify it fails**

Run:

```bash
uv run pytest apps/analysis-service/tests/test_groq_forecast_api.py -v
```

Expected: FAIL because use case and route do not exist.

- [ ] **Step 3: Add use case**

Modify `apps/analysis-service/src/analysis_service/application/use_cases.py` imports:

```python
from economic_news_contracts.analysis import (
    ...
    GroqForecastRequest,
    GroqForecastResponse,
)
```

Add `EconomicForecastGenerator` to imported ports and class:

```python
class GenerateGroqTopicForecast:
    def __init__(self, generator: EconomicForecastGenerator) -> None:
        self._generator = generator

    async def execute(self, request: GroqForecastRequest) -> GroqForecastResponse:
        return await self._generator.generate(request)
```

- [ ] **Step 4: Add container provider**

Modify `apps/analysis-service/src/analysis_service/main/container.py` imports:

```python
from analysis_service.application.ports import EconomicForecastGenerator
from analysis_service.application.use_cases import GenerateGroqTopicForecast
from analysis_service.infrastructure.groq_forecast_client import GroqEconomicForecastGenerator
```

Add providers:

```python
    @provide(scope=Scope.APP, provides=EconomicForecastGenerator)
    def economic_forecast_generator(self, settings: AnalysisServiceSettings) -> EconomicForecastGenerator:
        return GroqEconomicForecastGenerator(
            base_url=str(settings.groq_base_url),
            api_key=settings.groq_api_key.get_secret_value() if settings.groq_api_key else None,
            model_name=settings.groq_model,
            timeout_seconds=settings.groq_timeout_seconds,
            temperature=settings.groq_temperature,
            max_tokens=settings.groq_max_tokens,
        )

    @provide(scope=Scope.APP)
    def generate_groq_topic_forecast(
        self,
        generator: EconomicForecastGenerator,
    ) -> GenerateGroqTopicForecast:
        return GenerateGroqTopicForecast(generator)
```

- [ ] **Step 5: Add router endpoint**

Modify `apps/analysis-service/src/analysis_service/presentation/router.py` imports:

```python
from economic_news_contracts.analysis import GroqForecastRequest, GroqForecastResponse
from analysis_service.application.use_cases import GenerateGroqTopicForecast
```

Add route:

```python
@router.post("/topic-forecast/groq-predictions", response_model=GroqForecastResponse)
async def generate_groq_topic_prediction(
    request: GroqForecastRequest,
    use_case: FromDishka[GenerateGroqTopicForecast],
) -> GroqForecastResponse:
    return await use_case.execute(request)
```

- [ ] **Step 6: Run analysis Groq API tests**

Run:

```bash
uv run pytest apps/analysis-service/tests/test_groq_forecast_api.py apps/analysis-service/tests/test_groq_forecast_client.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit analysis API**

Run:

```bash
git add apps/analysis-service/src/analysis_service/application/use_cases.py apps/analysis-service/src/analysis_service/main/container.py apps/analysis-service/src/analysis_service/presentation/router.py apps/analysis-service/tests/test_groq_forecast_api.py
git commit -m "feat: добавить api groq прогноза по темам"
```

---

### Task 4: Frontend API And UI Buttons

**Files:**
- Modify: `frontend/web/src/app/types.ts`
- Modify: `frontend/web/src/api/analysis.ts`
- Modify: `frontend/web/src/components/TopicForecastPanel.tsx`
- Modify: `frontend/web/src/app/App.tsx`
- Modify: `frontend/web/src/app/App.module.css`
- Test: `frontend/web/src/api/analysis.test.ts`
- Test: `frontend/web/src/app/App.test.tsx`

- [ ] **Step 1: Write failing API test**

Append to `frontend/web/src/api/analysis.test.ts`:

```typescript
  it("generates a groq prediction for a topic", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      Response.json({
        provider: "groq",
        model_name: "qwen/qwen3-32b",
        scope: "topic",
        target_id: "topic-1",
        prediction: "Сценарный прогноз.",
        disclaimer: "Это аналитический сценарий, а не финансовая рекомендация.",
        metadata: {},
      }),
    );

    const response = await generateGroqForecast(
      {
        scope: "topic",
        model_name: "tfidf-logreg",
        topic: topicForecastFixture.model_reports![0].topics[0],
        news_id: null,
      },
      { baseUrl: "http://localhost:8010", fetcher: fetchMock },
    );

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8010/api/v1/topic-forecast/groq-predictions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: expect.stringContaining("\"scope\":\"topic\""),
    });
    expect(response.model_name).toBe("qwen/qwen3-32b");
  });
```

Add import:

```typescript
import { generateGroqForecast } from "./analysis";
```

- [ ] **Step 2: Run API test to verify it fails**

Run:

```bash
npm --prefix frontend/web test -- analysis.test.ts
```

Expected: FAIL because `generateGroqForecast` does not exist.

- [ ] **Step 3: Add frontend types and API call**

Modify `frontend/web/src/app/types.ts`:

```typescript
export type GroqForecastScope = "topic" | "news";

export type GroqForecastRequest = {
  scope: GroqForecastScope;
  model_name: string;
  topic: TopicForecastTopic;
  news_id: string | null;
};

export type GroqForecastResponse = {
  provider: string;
  model_name: string;
  scope: GroqForecastScope;
  target_id: string;
  prediction: string;
  disclaimer: string;
  metadata: Record<string, unknown>;
};
```

Modify `frontend/web/src/api/analysis.ts` imports:

```typescript
  GroqForecastRequest,
  GroqForecastResponse,
```

Add function:

```typescript
export async function generateGroqForecast(
  request: GroqForecastRequest,
  options: ApiOptions = {},
): Promise<GroqForecastResponse> {
  const fetcher = options.fetcher ?? fetch;

  let response: Response;
  try {
    response = await fetcher(`${normalizeBaseUrl(options.baseUrl ?? ANALYSIS_SERVICE_URL)}/api/v1/topic-forecast/groq-predictions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
  } catch {
    throw connectionError();
  }

  if (!response.ok) {
    throw await errorFromResponse(response, "Не удалось сформировать Groq-прогноз");
  }

  return (await response.json()) as GroqForecastResponse;
}
```

- [ ] **Step 4: Write failing UI test**

Append to `frontend/web/src/app/App.test.tsx`:

```typescript
  it("generates groq prediction from topic forecast card", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/ml-report/latest")) {
        return Response.json(null);
      }
      if (url.includes("/api/v1/topic-forecast/latest")) {
        return Response.json(topicForecastFixture);
      }
      if (url.includes("/api/v1/topic-forecast/groq-predictions")) {
        return Response.json({
          provider: "groq",
          model_name: "qwen/qwen3-32b",
          scope: "topic",
          target_id: "topic-1",
          prediction: "Groq видит умеренно позитивный сценарий.",
          disclaimer: "Это аналитический сценарий, а не финансовая рекомендация.",
          metadata: {},
        });
      }
      return Response.json({});
    });

    render(<App fetcher={fetchMock as typeof fetch} />);

    await userEvent.click(await screen.findByRole("button", { name: "Прогноз" }));
    await userEvent.click(await screen.findByRole("button", { name: /Groq-прогноз темы/i }));

    expect(await screen.findByText("Groq видит умеренно позитивный сценарий.")).toBeInTheDocument();
  });
```

- [ ] **Step 5: Run UI test to verify it fails**

Run:

```bash
npm --prefix frontend/web test -- App.test.tsx
```

Expected: FAIL because buttons and state do not exist.

- [ ] **Step 6: Implement App state and callback**

Modify `frontend/web/src/app/App.tsx` imports:

```typescript
import { generateGroqForecast, ... } from "../api/analysis";
import type { GroqForecastRequest, GroqForecastResponse } from "./types";
```

Add state:

```typescript
  const [groqForecasts, setGroqForecasts] = useState<Record<string, GroqForecastResponse>>({});
  const [groqForecastLoadingKey, setGroqForecastLoadingKey] = useState<string | null>(null);
  const [groqForecastError, setGroqForecastError] = useState<string | null>(null);
```

Add handler:

```typescript
  async function handleGenerateGroqForecast(request: GroqForecastRequest): Promise<void> {
    const targetKey = `${request.model_name}:${request.scope}:${request.news_id ?? request.topic.topic_id}`;
    setGroqForecastLoadingKey(targetKey);
    setGroqForecastError(null);
    try {
      const response = await generateGroqForecast(request, { fetcher });
      setGroqForecasts((current) => ({ ...current, [targetKey]: response }));
    } catch (forecastError) {
      setGroqForecastError(messageFromError(forecastError));
    } finally {
      setGroqForecastLoadingKey(null);
    }
  }
```

Pass props to `TopicForecastPanel`:

```tsx
            groqForecasts={groqForecasts}
            groqForecastLoadingKey={groqForecastLoadingKey}
            groqForecastError={groqForecastError}
            onGenerateGroqForecast={handleGenerateGroqForecast}
```

- [ ] **Step 7: Implement panel buttons/results**

Modify `frontend/web/src/components/TopicForecastPanel.tsx` props:

```typescript
  groqForecasts: Record<string, GroqForecastResponse>;
  groqForecastLoadingKey: string | null;
  groqForecastError: string | null;
  onGenerateGroqForecast: (request: GroqForecastRequest) => void;
```

Add imports:

```typescript
import type {
  GroqForecastRequest,
  GroqForecastResponse,
  ImpactLabel,
  TopicForecast,
  TopicForecastJobStatus,
  TopicForecastNewsItem,
  TopicForecastTopic,
} from "../app/types";
```

Add helpers:

```typescript
function groqKey(modelName: string, scope: "topic" | "news", topic: TopicForecastTopic, newsId: string | null): string {
  return `${modelName}:${scope}:${newsId ?? topic.topic_id}`;
}

function renderGroqForecast(response: GroqForecastResponse | undefined) {
  if (!response) {
    return null;
  }
  return (
    <div className={styles.groqForecastResult}>
      <strong>{response.model_name}</strong>
      <p>{response.prediction}</p>
      <span>{response.disclaimer}</span>
    </div>
  );
}
```

Inside each topic card, before the static forecast section, add:

```tsx
                    <div className={styles.forecastActions}>
                      <button
                        type="button"
                        onClick={() =>
                          onGenerateGroqForecast({
                            scope: "topic",
                            model_name: modelReport.model_name,
                            topic,
                            news_id: null,
                          })
                        }
                        disabled={groqForecastLoadingKey === groqKey(modelReport.model_name, "topic", topic, null)}
                      >
                        {groqForecastLoadingKey === groqKey(modelReport.model_name, "topic", topic, null)
                          ? "Groq формирует прогноз"
                          : "Groq-прогноз темы"}
                      </button>
                    </div>
                    {renderGroqForecast(groqForecasts[groqKey(modelReport.model_name, "topic", topic, null)])}
                    {groqForecastError ? <p className={styles.errorText}>{groqForecastError}</p> : null}
```

Inside each news list item, after `<span>{renderNewsMeta(news)}</span>`, add:

```tsx
                              <button
                                type="button"
                                onClick={() =>
                                  onGenerateGroqForecast({
                                    scope: "news",
                                    model_name: modelReport.model_name,
                                    topic,
                                    news_id: news.id,
                                  })
                                }
                                disabled={groqForecastLoadingKey === groqKey(modelReport.model_name, "news", topic, news.id)}
                              >
                                {groqForecastLoadingKey === groqKey(modelReport.model_name, "news", topic, news.id)
                                  ? "Groq анализирует"
                                  : "Groq-прогноз новости"}
                              </button>
                              {renderGroqForecast(groqForecasts[groqKey(modelReport.model_name, "news", topic, news.id)])}
```

- [ ] **Step 8: Add CSS**

Modify `frontend/web/src/app/App.module.css`:

```css
.forecastActions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 12px 0;
}

.groqForecastResult {
  border-left: 3px solid #0f5132;
  background: #f3faf6;
  padding: 10px 12px;
  margin: 10px 0;
}

.groqForecastResult p {
  margin: 6px 0;
}

.groqForecastResult span {
  color: #4a5a52;
  font-size: 0.9rem;
}

.newsList button {
  margin-top: 8px;
  width: fit-content;
}
```

- [ ] **Step 9: Run frontend tests**

Run:

```bash
npm --prefix frontend/web test -- analysis.test.ts App.test.tsx
```

Expected: PASS.

- [ ] **Step 10: Commit frontend Groq UI**

Run:

```bash
git add frontend/web/src/app/types.ts frontend/web/src/api/analysis.ts frontend/web/src/components/TopicForecastPanel.tsx frontend/web/src/app/App.tsx frontend/web/src/app/App.module.css frontend/web/src/api/analysis.test.ts frontend/web/src/app/App.test.tsx
git commit -m "feat: добавить groq прогноз на фронтенде"
```

---

### Task 5: Docker And Dataset Runtime Defaults

**Files:**
- Modify: `deploy/compose.yaml`
- Modify: `.env.example`

- [ ] **Step 1: Check current local dataset**

Run:

```bash
wc -l data/raw/economic_news.csv
```

Expected: approximately `50001` lines including header.

- [ ] **Step 2: Configure compose for 50k dataset and Groq env passthrough**

Modify both `analysis-service` and `analysis-worker` environment blocks in `deploy/compose.yaml`:

```yaml
      ANALYSIS_ML_DATASET_PATH: "${ANALYSIS_ML_DATASET_PATH:-data/raw/economic_news.csv}"
      ANALYSIS_TOPIC_FORECAST_DOCUMENT_LIMIT: "${ANALYSIS_TOPIC_FORECAST_DOCUMENT_LIMIT:-500}"
      ANALYSIS_GROQ_BASE_URL: "${ANALYSIS_GROQ_BASE_URL:-https://api.groq.com/openai}"
      ANALYSIS_GROQ_MODEL: "${ANALYSIS_GROQ_MODEL:-qwen/qwen3-32b}"
      ANALYSIS_GROQ_API_KEY: "${ANALYSIS_GROQ_API_KEY:-}"
```

Modify `dialog-service` environment block:

```yaml
      DIALOG_GENERATOR_KIND: "${DIALOG_GENERATOR_KIND:-groq}"
      DIALOG_GROQ_BASE_URL: "${DIALOG_GROQ_BASE_URL:-https://api.groq.com/openai}"
      DIALOG_GROQ_MODEL: "${DIALOG_GROQ_MODEL:-qwen/qwen3-32b}"
      DIALOG_GROQ_API_KEY: "${DIALOG_GROQ_API_KEY:-}"
      DIALOG_LLM_BASE_URL: "${DIALOG_LLM_BASE_URL:-http://host.docker.internal:8080}"
      DIALOG_LLM_MODEL: "${DIALOG_LLM_MODEL:-Qwen3-0.6B-Instruct-GGUF}"
```

- [ ] **Step 3: Document environment variables**

Append to `.env.example`:

```dotenv
# Groq LLM generation
DIALOG_GENERATOR_KIND=groq
DIALOG_GROQ_BASE_URL=https://api.groq.com/openai
DIALOG_GROQ_MODEL=qwen/qwen3-32b
DIALOG_GROQ_API_KEY=

# Groq forecast generation in analysis-service
ANALYSIS_GROQ_BASE_URL=https://api.groq.com/openai
ANALYSIS_GROQ_MODEL=qwen/qwen3-32b
ANALYSIS_GROQ_API_KEY=

# Local 50k FNSPID-derived dataset
ANALYSIS_ML_DATASET_PATH=data/raw/economic_news.csv
ANALYSIS_TOPIC_FORECAST_DOCUMENT_LIMIT=500
NEWS_SERVICE_NEWS_DATASET_PATH=data/raw/economic_news.csv
NEWS_SERVICE_DEFAULT_INDEX_LIMIT=50000
```

- [ ] **Step 4: Run config validation tests**

Run:

```bash
uv run pytest apps/dialog-service/tests/test_dialog_container.py apps/analysis-service/tests/test_container.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit runtime config**

Run:

```bash
git add deploy/compose.yaml .env.example
git commit -m "chore: настроить groq и датасет 50k"
```

---

### Task 6: Full Verification Before Running Jobs

**Files:** No source edits.

- [ ] **Step 1: Run backend targeted tests**

Run:

```bash
uv run pytest apps/dialog-service/tests/test_llm_generator.py apps/dialog-service/tests/test_dialog_container.py apps/analysis-service/tests/test_groq_forecast_client.py apps/analysis-service/tests/test_groq_forecast_api.py apps/analysis-service/tests/test_topic_forecast_api.py apps/analysis-service/tests/test_topic_forecast_core.py -q
```

Expected: PASS.

- [ ] **Step 2: Run frontend targeted tests**

Run:

```bash
npm --prefix frontend/web test -- analysis.test.ts App.test.tsx
```

Expected: PASS.

- [ ] **Step 3: Run lint**

Run:

```bash
uv run ruff check apps/dialog-service/src apps/dialog-service/tests apps/analysis-service/src apps/analysis-service/tests packages/contracts/src
```

Expected: PASS.

- [ ] **Step 4: Build Docker services**

Run:

```bash
docker compose -f deploy/compose.yaml build dialog-service analysis-service analysis-worker frontend-web
```

Expected: build succeeds.

- [ ] **Step 5: Start Docker stack**

Run:

```bash
docker compose -f deploy/compose.yaml up -d
```

Expected: all services start.

- [ ] **Step 6: Check service status**

Run:

```bash
docker compose -f deploy/compose.yaml ps
```

Expected: `api-gateway`, `analysis-service`, `analysis-worker`, `dialog-service`, `retrieval-service`, `news-service`, `news-worker`, `frontend-web`, `redis`, `qdrant`, `postgres`, `mlflow` are running.

---

### Task 7: Start 50k Index, ML Report, And Topic Forecast Jobs

**Files:** No source edits. Do not commit `data/raw/economic_news.csv`.

- [ ] **Step 1: Verify 50k dataset is present and remains untracked**

Run:

```bash
git status --short data/raw/economic_news.csv
wc -l data/raw/economic_news.csv
```

Expected: file is modified/untracked locally and has around 50 001 lines. Do not stage it.

- [ ] **Step 2: Ensure Groq key is configured for live LLM calls**

Run:

```bash
grep -n "GROQ_API_KEY" .env.example
```

Expected: variables are documented. For live run, user must put the real key in `.env` or export `DIALOG_GROQ_API_KEY` and `ANALYSIS_GROQ_API_KEY` before `docker compose up`.

- [ ] **Step 3: Index 50k news through existing UI/API**

Run:

```bash
curl -s -X POST http://localhost:8004/api/v1/news/index -H "Content-Type: application/json" -d '{"limit":50000}'
```

Expected: response contains `indexed_count` close to `50000`. If the existing API uses a different route, inspect `apps/news-service/src/news_service/presentation/router.py` and use the current index endpoint.

- [ ] **Step 4: Start ML report job on `data/raw/economic_news.csv`**

Run:

```bash
curl -s -X POST http://localhost:8001/api/v1/ml-report/jobs -H "Content-Type: application/json" -d '{}'
```

Expected: response contains `job_id` and `status` equals `queued`.

- [ ] **Step 5: Poll ML report job**

Run repeatedly with the returned id:

```bash
curl -s http://localhost:8001/api/v1/ml-report/jobs/<job_id>
```

Expected: status moves from `queued` to `started` to `succeeded`; `report_path` equals `reports/ml/model-report.json`.

- [ ] **Step 6: Confirm ML report uses 50k dataset**

Run:

```bash
curl -s http://localhost:8001/api/v1/ml-report/latest
```

Expected: JSON has `dataset.row_count` close to `50000`.

- [ ] **Step 7: Start topic forecast job**

Run:

```bash
curl -s -X POST http://localhost:8001/api/v1/topic-forecast/jobs -H "Content-Type: application/json" -d '{}'
```

Expected: response contains `job_id` and `status` equals `queued`.

- [ ] **Step 8: Poll topic forecast job**

Run repeatedly with the returned id:

```bash
curl -s http://localhost:8001/api/v1/topic-forecast/jobs/<job_id>
```

Expected: status moves to `succeeded`; `report_path` equals `reports/topic-forecast/latest.json`.

- [ ] **Step 9: Confirm forecast model reports are present**

Run:

```bash
curl -s http://localhost:8001/api/v1/topic-forecast/latest
```

Expected: JSON contains `model_reports` for `tfidf-logreg`, `embedding-logreg`, and `tiny-transformer-classifier`.

---

### Task 8: Browser Smoke Test And Final Commit/Push

**Files:** No source edits unless smoke test exposes a bug.

- [ ] **Step 1: Open frontend**

Open:

```text
http://localhost:5173
```

Expected: app loads without console-visible fatal error.

- [ ] **Step 2: Verify ML report UI**

In frontend:

1. Open `ML-отчет`.
2. Click `Сформировать ML-отчет` if latest report is absent.
3. Confirm row count shows around `50000`.
4. Confirm model metrics table is visible.

- [ ] **Step 3: Verify topic forecast UI**

In frontend:

1. Open `Прогноз`.
2. Click `Сформировать прогноз по темам` if latest forecast is absent.
3. Confirm model sections for all three classifiers are visible.
4. Confirm topic cards show impact counts and news lists.

- [ ] **Step 4: Verify Groq buttons**

In frontend:

1. Click `Groq-прогноз темы`.
2. Confirm generated text appears under the topic card.
3. Click `Groq-прогноз новости` for one news item.
4. Confirm generated text appears under that news item.

If no real key is configured, expected result is a visible Russian error from API. Configure `ANALYSIS_GROQ_API_KEY` and restart `analysis-service`/`analysis-worker` for live verification.

- [ ] **Step 5: Check git status**

Run:

```bash
git status --short
```

Expected: only intended source/config files are changed. `data/raw/economic_news.csv` may remain modified and must not be staged.

- [ ] **Step 6: Commit any smoke-test fix**

If frontend/API smoke test required a fix, run:

```bash
git add <fixed-source-files>
git commit -m "fix: исправить groq прогноз в интерфейсе"
```

Expected: commit succeeds.

- [ ] **Step 7: Push branch**

Run:

```bash
git push -u origin feature/frontend-analytics-console
```

Expected: push succeeds.

---

## Self-Review

- Spec coverage: Groq `qwen/qwen3-32b` mode is covered in Task 1 and Task 5. ML report on 50k data is covered in Task 5 and Task 7. Topic forecast on indexed 50k data is covered in Task 5 and Task 7. Per-topic/per-news Groq prediction buttons are covered in Tasks 2-4 and Task 8.
- Placeholder scan: no TBD/TODO placeholders are present. Runtime commands include exact endpoints and expected outputs; the news index endpoint has an explicit inspection fallback because it must match the existing router.
- Type consistency: DTO names `GroqForecastRequest`, `GroqForecastResponse`, `GroqForecastScope`, frontend types, API endpoint path, and use case names match across tasks.
- Scope check: the plan avoids a new microservice and keeps all Groq forecast behavior inside existing dialog/analysis boundaries.
