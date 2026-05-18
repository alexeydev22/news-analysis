import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Protocol, cast

from economic_news_contracts.analysis import (
    GeminiForecastRequest,
    GeminiForecastResponse,
    GeminiForecastScope,
    TopicForecastNewsItemResponse,
)
from zapros import AsyncClient, AsyncStdNetworkHandler

_UNAVAILABLE_MESSAGE = "gemini forecast generation is unavailable"


class GeminiForecastGenerationError(RuntimeError):
    """Ошибка генерации экономического прогноза через Gemini."""


class _ZaprosResponse(Protocol):
    status: int
    json: object

    async def aread(self) -> bytes: ...


def _make_zapros_client(timeout_seconds: float) -> AsyncClient:
    return AsyncClient(
        handler=AsyncStdNetworkHandler(total_timeout=timeout_seconds),
    )


class GeminiEconomicForecastGenerator:
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

    async def generate(self, request: GeminiForecastRequest) -> GeminiForecastResponse:
        if not self._api_key:
            raise GeminiForecastGenerationError("GEMINI API key is not configured")

        news_items = self._select_news_items(request)
        payload = self._build_payload(request, news_items)
        response = await self._post(payload)
        if response.status >= 400:
            raise GeminiForecastGenerationError(_UNAVAILABLE_MESSAGE)

        try:
            await response.aread()
            prediction = self._parse_content(response.json)
        except GeminiForecastGenerationError:
            raise
        except Exception as error:
            raise GeminiForecastGenerationError(_UNAVAILABLE_MESSAGE) from error

        return GeminiForecastResponse(
            provider="gemini",
            model_name=self._model_name,
            scope=request.scope,
            target_id=self._target_id(request),
            prediction=prediction,
            metadata={
                "source_model": request.model_name,
                "topic_id": request.topic.topic_id,
                "news_count": len(news_items),
            },
        )

    def _build_payload(
        self,
        request: GeminiForecastRequest,
        news_items: list[TopicForecastNewsItemResponse],
    ) -> dict[str, object]:
        return {
            "model": self._model_name,
            "messages": [
                {
                    "role": "system",
                    "content": self._build_system_prompt(),
                },
                {
                    "role": "user",
                    "content": self._build_user_prompt(request, news_items),
                },
            ],
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "stream": False,
        }

    def _build_system_prompt(self) -> str:
        return (
            "Ты экономический аналитик. Верни только итоговый прогноз на русском языке. "
            "Не показывай ход рассуждений, не используй <think>, не добавляй заголовки "
            "и не добавляй служебные предупреждения. Прогноз должен опираться только "
            "на факты из переданных текстов новостей."
        )

    def _build_user_prompt(
        self,
        request: GeminiForecastRequest,
        news_items: list[TopicForecastNewsItemResponse],
    ) -> str:
        topic = request.topic
        news_block = "\n".join(self._format_news_item(item) for item in news_items)
        return (
            f"Область прогноза: {request.scope.value}\n"
            f"Модель исходной классификации: {request.model_name}\n"
            f"Тема: {topic.title}\n"
            f"Краткое описание темы: {topic.summary}\n"
            f"Базовый прогноз модели: {topic.forecast}\n"
            f"Общий эффект: {topic.overall_impact.value}\n"
            f"Уверенность: {topic.confidence}\n"
            f"Аргументы: {'; '.join(topic.arguments) or 'нет'}\n"
            f"Риски: {'; '.join(topic.risks) or 'нет'}\n"
            f"Новости:\n{news_block or 'Нет новостей для детализации.'}\n\n"
            "Сделай один краткий прогноз в 3-6 предложениях. Опирайся только на факты "
            "из текстов новостей: назови факты, которые поддерживают вывод, и осторожно "
            "укажи, что может изменить сценарий. Не выводи рассуждения, списки "
            "и служебные пометки."
        )

    def _target_id(self, request: GeminiForecastRequest) -> str:
        if request.scope == GeminiForecastScope.TOPIC:
            return request.topic.topic_id
        return request.news_id or request.topic.topic_id

    def _select_news_items(
        self,
        request: GeminiForecastRequest,
    ) -> list[TopicForecastNewsItemResponse]:
        if request.scope != GeminiForecastScope.NEWS or request.news_id is None:
            return request.topic.news

        selected_news = [item for item in request.topic.news if item.id == request.news_id]
        if not selected_news:
            raise GeminiForecastGenerationError(_UNAVAILABLE_MESSAGE)
        return selected_news

    def _format_news_item(self, item: TopicForecastNewsItemResponse) -> str:
        return (
            f"- id={item.id}; title={item.title}; source={item.source}; "
            f"impact={item.impact.value}; score={item.score}; text={item.text}"
        )

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
        except GeminiForecastGenerationError:
            raise
        except Exception as error:
            raise GeminiForecastGenerationError(_UNAVAILABLE_MESSAGE) from error

    def _chat_completions_url(self) -> str:
        if self._base_url.endswith("/openai"):
            return f"{self._base_url}/chat/completions"
        return f"{self._base_url}/v1/chat/completions"

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise GeminiForecastGenerationError("GEMINI API key is not configured")
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
            raise GeminiForecastGenerationError(_UNAVAILABLE_MESSAGE) from error

        if not isinstance(content, str):
            raise GeminiForecastGenerationError(_UNAVAILABLE_MESSAGE)

        prediction = self._remove_thinking_blocks(content).strip()
        if not prediction:
            raise GeminiForecastGenerationError(_UNAVAILABLE_MESSAGE)
        return prediction

    def _remove_thinking_blocks(self, content: str) -> str:
        return re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL | re.IGNORECASE)

    def _field(self, value: object, field_name: str) -> object:
        if not isinstance(value, Mapping):
            raise TypeError
        return cast(Mapping[str, object], value)[field_name]

    def _list_item(self, value: object, index: int) -> Any:
        if not isinstance(value, Sequence):
            raise TypeError
        return value[index]
