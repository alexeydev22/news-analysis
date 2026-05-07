from collections.abc import Callable, Mapping, Sequence
from typing import Any, Protocol, cast

from zapros import AsyncClient, AsyncStdNetworkHandler

from dialog_service.domain.errors import DialogGeneratorUnavailableError
from dialog_service.domain.model import (
    DialogContextItem,
    DialogGeneration,
    DialogImpactItem,
    DialogQuestion,
)
from dialog_service.infrastructure.prompt_builder import DialogPromptBuilder

_UNAVAILABLE_MESSAGE = "dialog llm is unavailable"


class _ZaprosResponse(Protocol):
    status: int
    json: object

    async def aread(self) -> bytes: ...


def _make_zapros_client(timeout_seconds: float) -> Any:
    return AsyncClient(
        handler=AsyncStdNetworkHandler(total_timeout=timeout_seconds),
    )


class LlmDialogGenerator:
    def __init__(
        self,
        base_url: str,
        model_name: str,
        timeout_seconds: float,
        temperature: float,
        max_tokens: int,
        prompt_builder: DialogPromptBuilder | None = None,
        client: Any | None = None,
        client_factory: Callable[[float], Any] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_name = model_name
        self._timeout_seconds = timeout_seconds
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._prompt_builder = prompt_builder or DialogPromptBuilder()
        self._client = client
        self._client_factory = client_factory or _make_zapros_client

    async def generate(
        self,
        question: DialogQuestion,
        context: list[DialogContextItem],
        impact_summaries: list[DialogImpactItem],
        language: str,
    ) -> DialogGeneration:
        payload = self._build_payload(question, context, impact_summaries, language)
        response = await self._post(payload)
        if response.status >= 400:
            raise DialogGeneratorUnavailableError(_UNAVAILABLE_MESSAGE)

        try:
            await response.aread()
            content = self._parse_content(response.json)
        except DialogGeneratorUnavailableError:
            raise
        except Exception as error:
            raise DialogGeneratorUnavailableError(_UNAVAILABLE_MESSAGE) from error
        return DialogGeneration(
            answer=content,
            used_context_ids=[item.id for item in context],
            model_name=self._model_name,
            metadata={
                "generator_kind": "llm",
                "model_name": self._model_name,
                "context_count": len(context),
                "impact_summary_count": len(impact_summaries),
            },
        )

    def _build_payload(
        self,
        question: DialogQuestion,
        context: list[DialogContextItem],
        impact_summaries: list[DialogImpactItem],
        language: str,
    ) -> dict[str, object]:
        return {
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

    async def _post(self, payload: dict[str, object]) -> _ZaprosResponse:
        url = f"{self._base_url}/v1/chat/completions"
        try:
            if self._client is not None:
                return cast(_ZaprosResponse, await self._client.post(url, json=payload))
            async with self._client_factory(self._timeout_seconds) as client:
                return cast(_ZaprosResponse, await client.post(url, json=payload))
        except DialogGeneratorUnavailableError:
            raise
        except Exception as error:
            raise DialogGeneratorUnavailableError(_UNAVAILABLE_MESSAGE) from error

    def _parse_content(self, body: object) -> str:
        try:
            choices = self._field(body, "choices")
            first_choice = self._list_item(choices, 0)
            message = self._field(first_choice, "message")
            content = self._field(message, "content")
        except (IndexError, KeyError, TypeError) as error:
            raise DialogGeneratorUnavailableError(_UNAVAILABLE_MESSAGE) from error

        if not isinstance(content, str):
            raise DialogGeneratorUnavailableError(_UNAVAILABLE_MESSAGE)

        answer = content.strip()
        if not answer:
            raise DialogGeneratorUnavailableError(_UNAVAILABLE_MESSAGE)
        return answer

    def _field(self, value: object, field_name: str) -> object:
        if not isinstance(value, Mapping):
            raise TypeError
        return cast(Mapping[str, object], value)[field_name]

    def _list_item(self, value: object, index: int) -> Any:
        if not isinstance(value, Sequence):
            raise TypeError
        return value[index]
