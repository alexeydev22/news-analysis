from typing import cast

import pytest
from dialog_service.domain.errors import DialogGeneratorUnavailableError
from dialog_service.domain.model import DialogContextItem, DialogImpactItem, DialogQuestion
from dialog_service.infrastructure.llm_generator import LlmDialogGenerator


class FakeResponse:
    def __init__(
        self,
        status: int,
        json: object,
        *,
        require_read_before_json: bool = False,
    ) -> None:
        self.status = status
        self._json = json
        self._require_read_before_json = require_read_before_json
        self.read_count = 0

    async def aread(self) -> bytes:
        self.read_count += 1
        return b""

    @property
    def json(self) -> object:
        if self._require_read_before_json and self.read_count == 0:
            raise RuntimeError("response body was not read")
        return self._json


class MalformedJsonResponse:
    status = 200

    async def aread(self) -> bytes:
        return b""

    @property
    def json(self) -> object:
        raise ValueError("invalid json")


class FakeZaprosClient:
    def __init__(self, response: FakeResponse | MalformedJsonResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def post(
        self,
        url: str,
        json: dict[str, object],
    ) -> FakeResponse | MalformedJsonResponse:
        self.calls.append((url, json))
        return self.response


class RaisingZaprosClient:
    async def post(self, url: str, json: dict[str, object]) -> FakeResponse:
        raise OSError("connection refused")


class FakeZaprosClientContext:
    def __init__(self, response: FakeResponse) -> None:
        self.client = FakeZaprosClient(response)

    async def __aenter__(self) -> FakeZaprosClient:
        return self.client

    async def __aexit__(self, *args: object) -> None:
        return None


class RecordingClientFactory:
    def __init__(self, response: FakeResponse) -> None:
        self.timeout_seconds: float | None = None
        self.context = FakeZaprosClientContext(response)

    def __call__(self, timeout_seconds: float) -> FakeZaprosClientContext:
        self.timeout_seconds = timeout_seconds
        return self.context


def dialog_context() -> list[DialogContextItem]:
    return [
        DialogContextItem(
            id="news-1",
            title="GDP grows",
            text="GDP grew by 2 percent.",
            source="demo",
            score=0.75,
        ),
    ]


def impact_summaries() -> list[DialogImpactItem]:
    return [
        DialogImpactItem(
            news_id="news-1",
            model_name="tfidf-logreg",
            impact="positive",
            confidence=0.82,
            explanation="Рост ВВП обычно поддерживает рынок.",
        ),
    ]


def llm_payload(content: str) -> dict[str, object]:
    return {
        "choices": [
            {
                "message": {
                    "content": content,
                },
            },
        ],
    }


@pytest.mark.asyncio
async def test_llm_generator_sends_openai_compatible_payload() -> None:
    transport = FakeZaprosClient(FakeResponse(200, llm_payload("Рост ВВП позитивен.")))
    generator = LlmDialogGenerator(
        base_url="http://llm.local:8080/",
        model_name="qwen3-0.6b",
        timeout_seconds=4.5,
        temperature=0.1,
        max_tokens=384,
        client=transport,
    )

    await generator.generate(
        question=DialogQuestion("Что значит рост ВВП?"),
        context=dialog_context(),
        impact_summaries=impact_summaries(),
        language="ru",
    )

    url, payload = transport.calls[0]
    assert url == "http://llm.local:8080/v1/chat/completions"
    assert payload["model"] == "qwen3-0.6b"
    assert payload["temperature"] == 0.1
    assert payload["max_tokens"] == 384
    assert payload["stream"] is False

    messages = cast(list[dict[str, str]], payload["messages"])
    assert isinstance(messages, list)
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "Вопрос пользователя" in messages[1]["content"]
    assert "GDP grew by 2 percent." in messages[1]["content"]
    assert "Рост ВВП обычно поддерживает рынок." in messages[1]["content"]


@pytest.mark.asyncio
async def test_llm_generator_parses_answer_and_metadata() -> None:
    generator = LlmDialogGenerator(
        base_url="http://llm.local:8080",
        model_name="qwen3-0.6b",
        timeout_seconds=4.5,
        temperature=0.1,
        max_tokens=384,
        client=FakeZaprosClient(FakeResponse(200, llm_payload("  Рост ВВП позитивен.  "))),
    )

    generation = await generator.generate(
        question=DialogQuestion("Что значит рост ВВП?"),
        context=dialog_context(),
        impact_summaries=impact_summaries(),
        language="ru",
    )

    assert generation.answer == "Рост ВВП позитивен."
    assert generation.used_context_ids == ["news-1"]
    assert generation.model_name == "qwen3-0.6b"
    assert generation.metadata == {
        "generator_kind": "llm",
        "model_name": "qwen3-0.6b",
        "context_count": 1,
        "impact_summary_count": 1,
    }


@pytest.mark.asyncio
async def test_llm_generator_passes_timeout_to_real_client_factory() -> None:
    factory = RecordingClientFactory(FakeResponse(200, llm_payload("Ответ.")))
    generator = LlmDialogGenerator(
        base_url="http://llm.local:8080",
        model_name="qwen3-0.6b",
        timeout_seconds=4.5,
        temperature=0.1,
        max_tokens=384,
        client_factory=factory,
    )

    await generator.generate(
        question=DialogQuestion("Что значит рост ВВП?"),
        context=dialog_context(),
        impact_summaries=[],
        language="ru",
    )

    assert factory.timeout_seconds == 4.5
    assert factory.context.client.calls


@pytest.mark.asyncio
async def test_llm_generator_reads_response_body_before_json() -> None:
    response = FakeResponse(
        200,
        llm_payload("Ответ."),
        require_read_before_json=True,
    )
    generator = LlmDialogGenerator(
        base_url="http://llm.local:8080",
        model_name="qwen3-0.6b",
        timeout_seconds=4.5,
        temperature=0.1,
        max_tokens=384,
        client=FakeZaprosClient(response),
    )

    generation = await generator.generate(
        question=DialogQuestion("Что значит рост ВВП?"),
        context=dialog_context(),
        impact_summaries=[],
        language="ru",
    )

    assert generation.answer == "Ответ."
    assert response.read_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        FakeResponse(400, {"error": "bad request"}),
        FakeResponse(503, {"error": "down"}),
        FakeResponse(200, {"choices": []}),
        FakeResponse(200, {"choices": [{"message": {}}]}),
        FakeResponse(200, {"choices": [{"message": {"content": "   "}}]}),
        FakeResponse(200, {"choices": [{"message": {"content": 123}}]}),
    ],
)
async def test_llm_generator_maps_unavailable_responses(response: FakeResponse) -> None:
    generator = LlmDialogGenerator(
        base_url="http://llm.local:8080",
        model_name="qwen3-0.6b",
        timeout_seconds=4.5,
        temperature=0.1,
        max_tokens=384,
        client=FakeZaprosClient(response),
    )

    with pytest.raises(
        DialogGeneratorUnavailableError,
        match="dialog llm is unavailable",
    ):
        await generator.generate(
            question=DialogQuestion("Что значит рост ВВП?"),
            context=dialog_context(),
            impact_summaries=impact_summaries(),
            language="ru",
        )


@pytest.mark.asyncio
async def test_llm_generator_maps_transport_error() -> None:
    generator = LlmDialogGenerator(
        base_url="http://llm.local:8080",
        model_name="qwen3-0.6b",
        timeout_seconds=4.5,
        temperature=0.1,
        max_tokens=384,
        client=RaisingZaprosClient(),
    )

    with pytest.raises(
        DialogGeneratorUnavailableError,
        match="dialog llm is unavailable",
    ):
        await generator.generate(
            question=DialogQuestion("Что значит рост ВВП?"),
            context=dialog_context(),
            impact_summaries=impact_summaries(),
            language="ru",
        )


@pytest.mark.asyncio
async def test_llm_generator_maps_malformed_json_property() -> None:
    generator = LlmDialogGenerator(
        base_url="http://llm.local:8080",
        model_name="qwen3-0.6b",
        timeout_seconds=4.5,
        temperature=0.1,
        max_tokens=384,
        client=FakeZaprosClient(MalformedJsonResponse()),
    )

    with pytest.raises(
        DialogGeneratorUnavailableError,
        match="dialog llm is unavailable",
    ):
        await generator.generate(
            question=DialogQuestion("Что значит рост ВВП?"),
            context=dialog_context(),
            impact_summaries=impact_summaries(),
            language="ru",
        )
