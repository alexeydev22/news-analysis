import re
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
_MAX_ATTEMPTS = 2


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
        api_key: str | None = None,
        generator_kind: str = "llm",
        prompt_builder: DialogPromptBuilder | None = None,
        client: Any | None = None,
        client_factory: Callable[[float], Any] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_name = model_name
        self._timeout_seconds = timeout_seconds
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._api_key = api_key
        self._generator_kind = generator_kind
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
        content = await self._generate_content(payload)
        return DialogGeneration(
            answer=content,
            used_context_ids=[item.id for item in context],
            model_name=self._model_name,
            metadata={
                "generator_kind": self._generator_kind,
                "model_name": self._model_name,
                "context_count": len(context),
                "impact_summary_count": len(impact_summaries),
            },
        )

    async def _generate_content(self, payload: dict[str, object]) -> str:
        last_error: Exception | None = None
        for attempt_number in range(_MAX_ATTEMPTS):
            try:
                response = await self._post(payload)
                if response.status >= 400:
                    if self._can_retry_status(response.status, attempt_number):
                        continue
                    raise DialogGeneratorUnavailableError(_UNAVAILABLE_MESSAGE)

                await response.aread()
                return self._parse_content(response.json)
            except DialogGeneratorUnavailableError as error:
                last_error = error
                if attempt_number + 1 >= _MAX_ATTEMPTS:
                    raise
            except Exception as error:
                last_error = error
                if attempt_number + 1 >= _MAX_ATTEMPTS:
                    raise DialogGeneratorUnavailableError(_UNAVAILABLE_MESSAGE) from error

        raise DialogGeneratorUnavailableError(_UNAVAILABLE_MESSAGE) from last_error

    def _can_retry_status(self, status: int, attempt_number: int) -> bool:
        return attempt_number + 1 < _MAX_ATTEMPTS and (
            status == 429 or 500 <= status < 600
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
        url = self._chat_completions_url()
        headers = self._headers()
        try:
            if self._client is not None:
                return cast(
                    _ZaprosResponse,
                    await self._client.post(url, json=payload, headers=headers),
                )
            async with self._client_factory(self._timeout_seconds) as client:
                return cast(
                    _ZaprosResponse,
                    await client.post(url, json=payload, headers=headers),
                )
        except DialogGeneratorUnavailableError:
            raise
        except Exception as error:
            raise DialogGeneratorUnavailableError(_UNAVAILABLE_MESSAGE) from error

    def _chat_completions_url(self) -> str:
        if self._base_url.endswith("/openai"):
            return f"{self._base_url}/chat/completions"
        return f"{self._base_url}/v1/chat/completions"

    def _headers(self) -> dict[str, str] | None:
        if self._api_key is None:
            return None
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

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

        answer = self._remove_thinking_blocks(content).strip()
        if not answer:
            raise DialogGeneratorUnavailableError(_UNAVAILABLE_MESSAGE)
        return answer

    def _remove_thinking_blocks(self, content: str) -> str:
        without_closed_blocks = re.sub(
            r"<think>.*?</think>",
            "",
            content,
            flags=re.DOTALL | re.IGNORECASE,
        )
        return re.sub(
            r"<think>.*$",
            "",
            without_closed_blocks,
            flags=re.DOTALL | re.IGNORECASE,
        )

    def _field(self, value: object, field_name: str) -> object:
        if not isinstance(value, Mapping):
            raise TypeError
        return cast(Mapping[str, object], value)[field_name]

    def _list_item(self, value: object, index: int) -> Any:
        if not isinstance(value, Sequence):
            raise TypeError
        return value[index]
