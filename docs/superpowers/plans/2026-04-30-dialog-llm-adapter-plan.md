# Dialog LLM Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a configurable OpenAI-compatible LLM generator to `dialog-service` while keeping the current template generator as the default fallback.

**Architecture:** Keep `domain` and `application` free of transport DTOs and LLM payloads. Put prompt construction and OpenAI-compatible parsing in `infrastructure`, wire the chosen generator in `main/container.py`, and preserve existing `api-gateway` contracts.

**Tech Stack:** Python 3.12, FastAPI, Granian, Dishka, Pydantic v2, Zapros, pytest, Docker Compose.

---

## File Structure

- Modify `apps/dialog-service/pyproject.toml`: add `zapros>=0.10`.
- Modify `apps/dialog-service/src/dialog_service/main/settings.py`: generator kind enum and LLM settings.
- Modify `apps/dialog-service/src/dialog_service/main/container.py`: select template or LLM generator.
- Create `apps/dialog-service/src/dialog_service/infrastructure/prompt_builder.py`: build system/user prompts from domain values.
- Create `apps/dialog-service/src/dialog_service/infrastructure/llm_generator.py`: OpenAI-compatible HTTP adapter.
- Modify `apps/dialog-service/src/dialog_service/infrastructure/template_generator.py`: align metadata with generator-kind acceptance criteria.
- Modify `apps/dialog-service/tests/test_dialog_container.py`: settings/container coverage for both generator modes.
- Create `apps/dialog-service/tests/test_prompt_builder.py`: prompt content and no-context behavior.
- Create `apps/dialog-service/tests/test_llm_generator.py`: payload, success parsing and error mapping.
- Modify `apps/dialog-service/tests/test_template_generator.py`: metadata assertions.
- Modify `deploy/compose.yaml`: dialog-service env for generator mode and local LLM URL.
- Modify `.env.example`: document dialog-service LLM settings.
- Modify `README.md`: add local llama.cpp-compatible server example.
- Modify `uv.lock`: regenerate with `uv lock`.

## Task 1: Dialog Generator Settings

**Files:**
- Modify: `apps/dialog-service/src/dialog_service/main/settings.py`
- Modify: `apps/dialog-service/tests/test_dialog_container.py`

- [ ] **Step 1: Write failing settings tests**

Append these tests to `apps/dialog-service/tests/test_dialog_container.py`:

```python
from dialog_service.main.settings import DialogGeneratorKind


def test_dialog_settings_include_llm_defaults() -> None:
    settings = DialogServiceSettings()

    assert settings.generator_kind == DialogGeneratorKind.TEMPLATE
    assert settings.generator_name == "template-dialog-generator"
    assert str(settings.llm_base_url) == "http://localhost:8080/"
    assert settings.llm_model == "Qwen3-0.6B-Instruct-GGUF"
    assert settings.llm_timeout_seconds == 30.0
    assert settings.llm_temperature == 0.2
    assert settings.llm_max_tokens == 512


def test_dialog_settings_read_prefixed_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DIALOG_GENERATOR_KIND", "llm")
    monkeypatch.setenv("DIALOG_GENERATOR_NAME", "local-qwen")
    monkeypatch.setenv("DIALOG_LLM_BASE_URL", "http://llm.local:8080")
    monkeypatch.setenv("DIALOG_LLM_MODEL", "qwen3-0.6b")
    monkeypatch.setenv("DIALOG_LLM_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("DIALOG_LLM_TEMPERATURE", "0.1")
    monkeypatch.setenv("DIALOG_LLM_MAX_TOKENS", "384")

    settings = DialogServiceSettings()

    assert settings.generator_kind == DialogGeneratorKind.LLM
    assert settings.generator_name == "local-qwen"
    assert str(settings.llm_base_url) == "http://llm.local:8080/"
    assert settings.llm_model == "qwen3-0.6b"
    assert settings.llm_timeout_seconds == 45.0
    assert settings.llm_temperature == 0.1
    assert settings.llm_max_tokens == 384
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run pytest apps/dialog-service/tests/test_dialog_container.py -v
```

Expected: fail because `DialogGeneratorKind` and LLM settings do not exist.

- [ ] **Step 3: Implement settings**

Replace `apps/dialog-service/src/dialog_service/main/settings.py` with:

```python
from enum import StrEnum

from economic_news_framework.settings import BaseServiceSettings
from pydantic import AnyHttpUrl, Field
from pydantic_settings import SettingsConfigDict


class DialogGeneratorKind(StrEnum):
    TEMPLATE = "template"
    LLM = "llm"


class DialogServiceSettings(BaseServiceSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="DIALOG_",
        extra="ignore",
    )

    service_name: str = "dialog-service"
    version: str = "0.1.0"
    generator_kind: DialogGeneratorKind = DialogGeneratorKind.TEMPLATE
    generator_name: str = "template-dialog-generator"
    llm_base_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8080")
    llm_model: str = Field(default="Qwen3-0.6B-Instruct-GGUF", min_length=1)
    llm_timeout_seconds: float = Field(default=30.0, gt=0.0)
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=512, ge=1, le=4096)
```

- [ ] **Step 4: Run settings tests**

Run:

```bash
uv run pytest apps/dialog-service/tests/test_dialog_container.py -v
```

Expected: all tests in the file pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add apps/dialog-service/src/dialog_service/main/settings.py apps/dialog-service/tests/test_dialog_container.py
git commit -m "feat: добавить настройки llm генератора"
```

## Task 2: Prompt Builder

**Files:**
- Create: `apps/dialog-service/src/dialog_service/infrastructure/prompt_builder.py`
- Create: `apps/dialog-service/tests/test_prompt_builder.py`

- [ ] **Step 1: Write failing prompt builder tests**

Create `apps/dialog-service/tests/test_prompt_builder.py`:

```python
from dialog_service.domain.model import DialogContextItem, DialogImpactItem, DialogQuestion
from dialog_service.infrastructure.prompt_builder import DialogPromptBuilder


def test_prompt_builder_includes_question_context_impacts_and_constraints() -> None:
    builder = DialogPromptBuilder()

    messages = builder.build_messages(
        question=DialogQuestion("Что значит рост ВВП?"),
        context=[
            DialogContextItem(
                id="news-1",
                title="GDP grows",
                text="GDP grew by 2 percent.",
                source="demo",
                score=0.75,
            ),
        ],
        impact_summaries=[
            DialogImpactItem(
                news_id="news-1",
                model_name="tfidf-logreg",
                impact="positive",
                confidence=0.82,
                explanation="Рост ВВП обычно поддерживает рынок.",
            ),
        ],
        language="ru",
    )

    assert messages[0] == {
        "role": "system",
        "content": (
            "Ты аналитическая диалоговая система для экономических новостей. "
            "Отвечай на русском языке. Используй только переданный контекст, "
            "не выдумывай источники и факты, не обещай точные прогнозы рынка. "
            "Ответ не должен быть финансовой рекомендацией."
        ),
    }
    user_prompt = messages[1]["content"]
    assert messages[1]["role"] == "user"
    assert "Вопрос пользователя: Что значит рост ВВП?" in user_prompt
    assert "id: news-1" in user_prompt
    assert "title: GDP grows" in user_prompt
    assert "source: demo" in user_prompt
    assert "score: 0.75" in user_prompt
    assert "text: GDP grew by 2 percent." in user_prompt
    assert "impact: positive" in user_prompt
    assert "confidence: 0.82" in user_prompt
    assert "Рост ВВП обычно поддерживает рынок." in user_prompt
    assert "Короткий вывод" in user_prompt
    assert "Факторы влияния" in user_prompt
    assert "не финансовая рекомендация" in user_prompt


def test_prompt_builder_tells_model_when_context_is_empty() -> None:
    builder = DialogPromptBuilder()

    messages = builder.build_messages(
        question=DialogQuestion("Что с рынком?"),
        context=[],
        impact_summaries=[],
        language="ru",
    )

    user_prompt = messages[1]["content"]
    assert "Релевантные новости не найдены" in user_prompt
    assert "не отвечай из общих знаний" in user_prompt
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run pytest apps/dialog-service/tests/test_prompt_builder.py -v
```

Expected: fail because `dialog_service.infrastructure.prompt_builder` does not exist.

- [ ] **Step 3: Implement prompt builder**

Create `apps/dialog-service/src/dialog_service/infrastructure/prompt_builder.py`:

```python
from dialog_service.domain.model import DialogContextItem, DialogImpactItem, DialogQuestion


class DialogPromptBuilder:
    def build_messages(
        self,
        question: DialogQuestion,
        context: list[DialogContextItem],
        impact_summaries: list[DialogImpactItem],
        language: str,
    ) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self._build_system_prompt(language)},
            {
                "role": "user",
                "content": self._build_user_prompt(question, context, impact_summaries),
            },
        ]

    def _build_system_prompt(self, language: str) -> str:
        language_instruction = (
            "Отвечай на русском языке."
            if language == "ru"
            else f"Отвечай на языке с кодом {language}."
        )
        return (
            "Ты аналитическая диалоговая система для экономических новостей. "
            f"{language_instruction} Используй только переданный контекст, "
            "не выдумывай источники и факты, не обещай точные прогнозы рынка. "
            "Ответ не должен быть финансовой рекомендацией."
        )

    def _build_user_prompt(
        self,
        question: DialogQuestion,
        context: list[DialogContextItem],
        impact_summaries: list[DialogImpactItem],
    ) -> str:
        lines = [
            f"Вопрос пользователя: {question.value}",
            "",
            "Найденные новости:",
        ]
        if not context:
            lines.append(
                "Релевантные новости не найдены; не отвечай из общих знаний.",
            )
        else:
            for item in context:
                lines.extend(
                    [
                        f"- id: {item.id}",
                        f"  title: {item.title}",
                        f"  source: {item.source}",
                        f"  score: {item.score:.2f}",
                        f"  text: {item.text}",
                    ],
                )
        lines.extend(["", "Результаты анализа экономического влияния:"])
        if not impact_summaries:
            lines.append("- Нет результатов анализа.")
        else:
            for summary in impact_summaries:
                confidence = (
                    "нет оценки"
                    if summary.confidence is None
                    else f"{summary.confidence:.2f}"
                )
                lines.extend(
                    [
                        f"- news_id: {summary.news_id}",
                        f"  model_name: {summary.model_name}",
                        f"  impact: {summary.impact}",
                        f"  confidence: {confidence}",
                        f"  explanation: {summary.explanation}",
                    ],
                )
        lines.extend(
            [
                "",
                "Сформируй ответ в формате:",
                "1. Короткий вывод.",
                "2. Факторы влияния.",
                "3. Оговорка: это аналитическая оценка на основе найденных новостей, "
                "а не финансовая рекомендация.",
            ],
        )
        return "\n".join(lines)
```

- [ ] **Step 4: Run prompt tests**

Run:

```bash
uv run pytest apps/dialog-service/tests/test_prompt_builder.py -v
```

Expected: pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add apps/dialog-service/src/dialog_service/infrastructure/prompt_builder.py apps/dialog-service/tests/test_prompt_builder.py
git commit -m "feat: добавить prompt builder для dialog llm"
```

## Task 3: OpenAI-Compatible LLM Generator

**Files:**
- Modify: `apps/dialog-service/pyproject.toml`
- Create: `apps/dialog-service/src/dialog_service/infrastructure/llm_generator.py`
- Create: `apps/dialog-service/tests/test_llm_generator.py`
- Modify: `uv.lock`

- [ ] **Step 1: Write failing LLM generator tests**

Create `apps/dialog-service/tests/test_llm_generator.py`:

```python
import pytest

from dialog_service.domain.errors import DialogGeneratorUnavailableError
from dialog_service.domain.model import DialogContextItem, DialogImpactItem, DialogQuestion
from dialog_service.infrastructure.llm_generator import LlmDialogGenerator
from dialog_service.infrastructure.prompt_builder import DialogPromptBuilder


class FakeResponse:
    def __init__(self, status: int, json_data: object) -> None:
        self.status = status
        self.json = json_data


class FakeClient:
    def __init__(self, response: FakeResponse | None = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.url: str | None = None
        self.payload: dict[str, object] | None = None

    async def post(self, url: str, json: dict[str, object]) -> FakeResponse:
        self.url = url
        self.payload = json
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


def make_generator(client: FakeClient) -> LlmDialogGenerator:
    return LlmDialogGenerator(
        base_url="http://localhost:8080",
        model_name="qwen3-0.6b",
        timeout_seconds=30.0,
        temperature=0.2,
        max_tokens=512,
        prompt_builder=DialogPromptBuilder(),
        client=client,
    )


@pytest.mark.asyncio
async def test_llm_generator_sends_openai_compatible_payload() -> None:
    client = FakeClient(
        FakeResponse(
            status=200,
            json_data={
                "choices": [
                    {"message": {"content": "Рост ВВП выглядит позитивным фактором."}},
                ],
            },
        ),
    )
    generator = make_generator(client)

    result = await generator.generate(
        question=DialogQuestion("Что значит рост ВВП?"),
        context=[
            DialogContextItem(
                id="news-1",
                title="GDP grows",
                text="GDP grew by 2 percent.",
                source="demo",
                score=0.75,
            ),
        ],
        impact_summaries=[
            DialogImpactItem(
                news_id="news-1",
                model_name="tfidf-logreg",
                impact="positive",
                confidence=0.82,
                explanation="Рост ВВП обычно поддерживает рынок.",
            ),
        ],
        language="ru",
    )

    assert client.url == "http://localhost:8080/v1/chat/completions"
    assert client.payload is not None
    assert client.payload["model"] == "qwen3-0.6b"
    assert client.payload["temperature"] == 0.2
    assert client.payload["max_tokens"] == 512
    assert client.payload["stream"] is False
    assert result.answer == "Рост ВВП выглядит позитивным фактором."
    assert result.used_context_ids == ["news-1"]
    assert result.model_name == "qwen3-0.6b"
    assert result.metadata == {
        "generator_kind": "llm",
        "model_name": "qwen3-0.6b",
        "context_count": 1,
        "impact_summary_count": 1,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response_json",
    [
        {},
        {"choices": []},
        {"choices": [{"message": {}}]},
        {"choices": [{"message": {"content": "   "}}]},
    ],
)
async def test_llm_generator_maps_malformed_response(response_json: object) -> None:
    generator = make_generator(FakeClient(FakeResponse(status=200, json_data=response_json)))

    with pytest.raises(DialogGeneratorUnavailableError, match="dialog llm is unavailable"):
        await generator.generate(
            question=DialogQuestion("Что с рынком?"),
            context=[],
            impact_summaries=[],
            language="ru",
        )


@pytest.mark.asyncio
async def test_llm_generator_maps_http_error() -> None:
    generator = make_generator(FakeClient(FakeResponse(status=500, json_data={"error": "boom"})))

    with pytest.raises(DialogGeneratorUnavailableError, match="dialog llm is unavailable"):
        await generator.generate(
            question=DialogQuestion("Что с рынком?"),
            context=[],
            impact_summaries=[],
            language="ru",
        )


@pytest.mark.asyncio
async def test_llm_generator_maps_transport_error() -> None:
    generator = make_generator(FakeClient(error=OSError("connection refused")))

    with pytest.raises(DialogGeneratorUnavailableError, match="dialog llm is unavailable"):
        await generator.generate(
            question=DialogQuestion("Что с рынком?"),
            context=[],
            impact_summaries=[],
            language="ru",
        )
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run pytest apps/dialog-service/tests/test_llm_generator.py -v
```

Expected: fail because `dialog_service.infrastructure.llm_generator` does not exist.

- [ ] **Step 3: Add dependency**

In `apps/dialog-service/pyproject.toml`, add `zapros>=0.10` to `dependencies`:

```toml
dependencies = [
  "dishka>=1.4",
  "economic-news-contracts",
  "economic-news-framework",
  "fastapi>=0.115",
  "granian>=1.7",
  "pydantic>=2.10",
  "pydantic-settings>=2.7",
  "zapros>=0.10",
]
```

Run:

```bash
uv lock
```

Expected: `uv.lock` is updated.

- [ ] **Step 4: Implement LLM generator**

Create `apps/dialog-service/src/dialog_service/infrastructure/llm_generator.py`:

```python
from collections.abc import Callable
from typing import Any

from zapros import AsyncClient, AsyncStdNetworkHandler

from dialog_service.domain.errors import DialogGeneratorUnavailableError
from dialog_service.domain.model import (
    DialogContextItem,
    DialogGeneration,
    DialogImpactItem,
    DialogQuestion,
)
from dialog_service.infrastructure.prompt_builder import DialogPromptBuilder


def _make_zapros_client(timeout_seconds: float) -> AsyncClient:
    return AsyncClient(handler=AsyncStdNetworkHandler(total_timeout=timeout_seconds))


class LlmDialogGenerator:
    def __init__(
        self,
        base_url: str,
        model_name: str,
        timeout_seconds: float,
        temperature: float,
        max_tokens: int,
        prompt_builder: DialogPromptBuilder,
        client: Any | None = None,
        client_factory: Callable[[float], Any] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_name = model_name
        self._timeout_seconds = timeout_seconds
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._prompt_builder = prompt_builder
        self._client = client
        self._client_factory = client_factory or _make_zapros_client

    async def generate(
        self,
        question: DialogQuestion,
        context: list[DialogContextItem],
        impact_summaries: list[DialogImpactItem],
        language: str,
    ) -> DialogGeneration:
        payload = {
            "model": self._model_name,
            "messages": self._prompt_builder.build_messages(
                question=question,
                context=context,
                impact_summaries=impact_summaries,
                language=language,
            ),
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "stream": False,
        }
        response = await self._post(payload)
        if response.status >= 400:
            raise DialogGeneratorUnavailableError("dialog llm is unavailable")
        answer = self._extract_answer(response.json)
        return DialogGeneration(
            answer=answer,
            used_context_ids=[item.id for item in context],
            model_name=self._model_name,
            metadata={
                "generator_kind": "llm",
                "model_name": self._model_name,
                "context_count": len(context),
                "impact_summary_count": len(impact_summaries),
            },
        )

    async def _post(self, payload: dict[str, Any]) -> Any:
        url = f"{self._base_url}/v1/chat/completions"
        try:
            if self._client is not None:
                return await self._client.post(url, json=payload)
            async with self._client_factory(self._timeout_seconds) as client:
                return await client.post(url, json=payload)
        except Exception as error:
            raise DialogGeneratorUnavailableError("dialog llm is unavailable") from error

    def _extract_answer(self, response_json: Any) -> str:
        try:
            answer = response_json["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise DialogGeneratorUnavailableError("dialog llm is unavailable") from error
        if not isinstance(answer, str) or not answer.strip():
            raise DialogGeneratorUnavailableError("dialog llm is unavailable")
        return answer.strip()
```

- [ ] **Step 5: Run LLM tests**

Run:

```bash
uv run pytest apps/dialog-service/tests/test_llm_generator.py -v
```

Expected: pass.

- [ ] **Step 6: Run lint/typecheck for dialog service**

Run:

```bash
uv run ruff check apps/dialog-service
uv run ty check apps/dialog-service
```

Expected: both pass.

- [ ] **Step 7: Commit**

Run:

```bash
git add apps/dialog-service/pyproject.toml apps/dialog-service/src/dialog_service/infrastructure/llm_generator.py apps/dialog-service/tests/test_llm_generator.py uv.lock
git commit -m "feat: добавить llm generator для dialog service"
```

## Task 4: DI, Compose and Documentation

**Files:**
- Modify: `apps/dialog-service/src/dialog_service/main/container.py`
- Modify: `apps/dialog-service/src/dialog_service/infrastructure/template_generator.py`
- Modify: `apps/dialog-service/tests/test_dialog_container.py`
- Modify: `apps/dialog-service/tests/test_template_generator.py`
- Modify: `deploy/compose.yaml`
- Modify: `.env.example`
- Modify: `README.md`

- [ ] **Step 1: Write failing container and template metadata tests**

Extend `apps/dialog-service/tests/test_dialog_container.py` with:

```python
from dialog_service.infrastructure.llm_generator import LlmDialogGenerator
from dialog_service.infrastructure.template_generator import TemplateDialogGenerator


@pytest.mark.asyncio
async def test_container_resolves_template_generator_by_default() -> None:
    container = create_container(DialogServiceSettings(generator_kind=DialogGeneratorKind.TEMPLATE))

    try:
        generator = await container.get(DialogGenerator)
    finally:
        await container.close()

    assert isinstance(generator, TemplateDialogGenerator)


@pytest.mark.asyncio
async def test_container_resolves_llm_generator_when_enabled() -> None:
    container = create_container(DialogServiceSettings(generator_kind=DialogGeneratorKind.LLM))

    try:
        generator = await container.get(DialogGenerator)
    finally:
        await container.close()

    assert isinstance(generator, LlmDialogGenerator)
```

Update `apps/dialog-service/tests/test_template_generator.py` metadata assertion in `test_template_generator_builds_russian_answer_from_context_and_impacts`:

```python
assert result.metadata == {
    "generator_kind": "template",
    "model_name": "template-dialog-generator",
    "context_count": 1,
    "impact_summary_count": 1,
    "language": "ru",
}
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run pytest apps/dialog-service/tests/test_dialog_container.py apps/dialog-service/tests/test_template_generator.py -v
```

Expected: fail because container always returns template and template metadata lacks `generator_kind`/`model_name`.

- [ ] **Step 3: Update template metadata**

In `apps/dialog-service/src/dialog_service/infrastructure/template_generator.py`, update `metadata`:

```python
metadata={
    "generator_kind": "template",
    "model_name": self._model_name,
    "context_count": len(context),
    "impact_summary_count": len(impact_summaries),
    "language": language,
},
```

- [ ] **Step 4: Wire DI selection**

Replace `dialog_generator` provider in `apps/dialog-service/src/dialog_service/main/container.py` with:

```python
from dialog_service.infrastructure.llm_generator import LlmDialogGenerator
from dialog_service.infrastructure.prompt_builder import DialogPromptBuilder
from dialog_service.main.settings import DialogGeneratorKind, DialogServiceSettings
```

and:

```python
    @provide(scope=Scope.APP)
    def prompt_builder(self) -> DialogPromptBuilder:
        return DialogPromptBuilder()

    @provide(scope=Scope.APP, provides=DialogGenerator)
    def dialog_generator(
        self,
        settings: DialogServiceSettings,
        prompt_builder: DialogPromptBuilder,
    ) -> DialogGenerator:
        if settings.generator_kind == DialogGeneratorKind.LLM:
            return LlmDialogGenerator(
                base_url=str(settings.llm_base_url),
                model_name=settings.llm_model,
                timeout_seconds=settings.llm_timeout_seconds,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                prompt_builder=prompt_builder,
            )
        return TemplateDialogGenerator(model_name=settings.generator_name)
```

- [ ] **Step 5: Update compose env**

In `deploy/compose.yaml`, add to `dialog-service.environment`:

```yaml
      DIALOG_GENERATOR_KIND: "template"
      DIALOG_LLM_BASE_URL: "http://host.docker.internal:8080"
      DIALOG_LLM_MODEL: "Qwen3-0.6B-Instruct-GGUF"
```

- [ ] **Step 6: Update `.env.example`**

Append:

```dotenv
DIALOG_GENERATOR_KIND=template
DIALOG_GENERATOR_NAME=template-dialog-generator
DIALOG_LLM_BASE_URL=http://localhost:8080
DIALOG_LLM_MODEL=Qwen3-0.6B-Instruct-GGUF
DIALOG_LLM_TIMEOUT_SECONDS=30
DIALOG_LLM_TEMPERATURE=0.2
DIALOG_LLM_MAX_TOKENS=512
```

- [ ] **Step 7: Update README**

Add a section to `README.md`:

````markdown
## Local LLM for dialog-service

By default `dialog-service` uses the deterministic template generator so the stack works
without downloading a model. To use a local OpenAI-compatible llama.cpp server:

```bash
llama-server -m models/Qwen3-0.6B-Instruct-Q8_0.gguf --host 0.0.0.0 --port 8080
DIALOG_GENERATOR_KIND=llm uv run --package economic-news-dialog-service granian dialog_service.main.app:app --interface asgi --host 0.0.0.0 --port 8003
```

For Docker Compose, keep the LLM server on the host and set:

```dotenv
DIALOG_GENERATOR_KIND=llm
DIALOG_LLM_BASE_URL=http://host.docker.internal:8080
```
````

- [ ] **Step 8: Run targeted tests**

Run:

```bash
uv run pytest apps/dialog-service/tests -v
```

Expected: all dialog-service tests pass.

- [ ] **Step 9: Run full verification**

Run:

```bash
uv run ruff check apps packages research
uv run ty check apps packages research
uv run pytest packages apps research/tests -v -W error
docker compose -f deploy/compose.yaml config
docker compose -f deploy/compose.yaml build dialog-service
```

Expected:

- ruff passes;
- ty passes;
- pytest passes;
- compose config passes;
- dialog-service Docker image builds.

- [ ] **Step 10: Commit**

Run:

```bash
git add apps/dialog-service/src/dialog_service/main/container.py apps/dialog-service/src/dialog_service/infrastructure/template_generator.py apps/dialog-service/tests/test_dialog_container.py apps/dialog-service/tests/test_template_generator.py deploy/compose.yaml .env.example README.md
git commit -m "feat: подключить llm generator в dialog service"
```

## Final Review and PR

- [ ] **Step 1: Run final code review**

Dispatch a final reviewer for the complete feature branch. Ask them to check:

- generator mode settings and env prefix;
- OpenAI-compatible payload shape;
- prompt safety constraints;
- DDD boundaries;
- downstream error detail hiding;
- Docker/compose correctness.

- [ ] **Step 2: Fix any review findings**

Use TDD for behavioral fixes. Commit fixes with `fix:` or `refactor:` Russian conventional messages.

- [ ] **Step 3: Push branch**

Run:

```bash
git push -u origin feature/dialog-llm-adapter
```

- [ ] **Step 4: Open PR**

Run:

```bash
gh pr create --base dev --head feature/dialog-llm-adapter --title "feat: добавить llm adapter для dialog service" --body "## Что сделано
- добавлен OpenAI-compatible LLM generator для dialog-service
- добавлен prompt builder для экономических новостей
- добавлен выбор generator mode через DIALOG_GENERATOR_KIND
- template generator сохранен как fallback
- обновлены compose/env/docs

## Проверка
- uv run ruff check apps packages research
- uv run ty check apps packages research
- uv run pytest packages apps research/tests -v -W error
- docker compose -f deploy/compose.yaml config
- docker compose -f deploy/compose.yaml build dialog-service"
```
