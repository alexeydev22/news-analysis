import pytest
from analysis_service.infrastructure.gemini_forecast_client import (
    GeminiEconomicForecastGenerator,
)
from economic_news_contracts.analysis import (
    GeminiForecastRequest,
    GeminiForecastScope,
    ImpactLabel,
    TopicForecastItemResponse,
    TopicForecastNewsItemResponse,
)
from pydantic import ValidationError


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
                text="GDP expanded faster than expected while consumer prices cooled.",
                source="demo",
                impact=ImpactLabel.POSITIVE,
                score=0.91,
            ),
        ],
    )


def multi_news_topic() -> TopicForecastItemResponse:
    return TopicForecastItemResponse(
        topic_id="topic-1",
        title="Рост ВВП и снижение инфляции",
        summary="Тема объединяет новости о макроэкономических показателях.",
        overall_impact=ImpactLabel.POSITIVE,
        confidence=0.82,
        positive_count=2,
        neutral_count=0,
        negative_count=0,
        forecast="Базовый прогноз.",
        arguments=["Преобладают позитивные сигналы."],
        risks=["Прогноз зависит от полноты данных."],
        news=[
            TopicForecastNewsItemResponse(
                id="news-1",
                title="GDP grows",
                text="GDP expanded faster than expected while consumer prices cooled.",
                source="demo",
                impact=ImpactLabel.POSITIVE,
                score=0.91,
            ),
            TopicForecastNewsItemResponse(
                id="news-2",
                title="Inflation slows",
                text="Inflation slowed for the second month and bond yields declined.",
                source="demo",
                impact=ImpactLabel.POSITIVE,
                score=0.72,
            ),
        ],
    )


def generator_with(client: FakeZaprosClient) -> GeminiEconomicForecastGenerator:
    return GeminiEconomicForecastGenerator(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        api_key="test-key",
        model_name="gemini-2.5-flash",
        timeout_seconds=30.0,
        temperature=0.2,
        max_tokens=700,
        client=client,
    )


def test_gemini_news_scope_requires_news_id() -> None:
    with pytest.raises(ValidationError, match="news_id is required for news scope"):
        GeminiForecastRequest(
            scope=GeminiForecastScope.NEWS,
            model_name="tfidf-logreg",
            topic=topic(),
            news_id=None,
        )


@pytest.mark.asyncio
async def test_gemini_forecast_generator_sends_prompt_and_parses_answer() -> None:
    client = FakeZaprosClient(FakeResponse("Рынок может получить поддержку."))
    generator = generator_with(client)

    result = await generator.generate(
        request=GeminiForecastRequest(
            scope=GeminiForecastScope.TOPIC,
            model_name="tfidf-logreg",
            topic=topic(),
            news_id=None,
        )
    )

    url, payload, headers = client.calls[0]
    assert url == "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    assert headers["Authorization"] == "Bearer test-key"
    assert payload["model"] == "gemini-2.5-flash"
    assert payload["temperature"] == 0.2
    assert payload["max_tokens"] == 700
    messages = payload["messages"]
    assert isinstance(messages, list)
    system_message = messages[0]
    user_message = messages[1]
    assert isinstance(system_message, dict)
    assert isinstance(user_message, dict)
    assert "экономический аналитик" in str(system_message["content"])
    assert "Верни только итоговый прогноз" in str(system_message["content"])
    assert "не используй <think>" in str(system_message["content"])
    assert "служебные предупреждения" in str(system_message["content"])
    assert "Область прогноза: topic" in str(user_message["content"])
    assert "GDP expanded faster than expected while consumer prices cooled." in str(
        user_message["content"],
    )
    assert "Опирайся только на факты из текстов новостей" in str(user_message["content"])
    assert result.provider == "gemini"
    assert result.model_name == "gemini-2.5-flash"
    assert result.scope == GeminiForecastScope.TOPIC
    assert result.prediction == "Рынок может получить поддержку."


@pytest.mark.asyncio
async def test_topic_scope_uses_topic_target_even_when_news_id_is_present() -> None:
    client = FakeZaprosClient(FakeResponse("Тема сохраняет умеренно позитивный сценарий."))
    generator = generator_with(client)

    result = await generator.generate(
        request=GeminiForecastRequest(
            scope=GeminiForecastScope.TOPIC,
            model_name="tfidf-logreg",
            topic=topic(),
            news_id="news-1",
        )
    )

    assert result.target_id == "topic-1"


@pytest.mark.asyncio
async def test_news_scope_filters_prompt_to_selected_news_and_counts_it() -> None:
    client = FakeZaprosClient(FakeResponse("Выбранная новость поддерживает прогноз."))
    generator = generator_with(client)

    result = await generator.generate(
        request=GeminiForecastRequest(
            scope=GeminiForecastScope.NEWS,
            model_name="tfidf-logreg",
            topic=multi_news_topic(),
            news_id="news-2",
        )
    )

    _, payload, _ = client.calls[0]
    messages = payload["messages"]
    assert isinstance(messages, list)
    user_message = messages[1]
    assert isinstance(user_message, dict)
    user_prompt = str(user_message["content"])
    assert "Inflation slows" in user_prompt
    assert "Inflation slowed for the second month and bond yields declined." in user_prompt
    assert "GDP grows" not in user_prompt
    assert "GDP expanded faster than expected while consumer prices cooled." not in user_prompt
    assert result.target_id == "news-2"
    assert result.metadata["news_count"] == 1


@pytest.mark.asyncio
async def test_gemini_forecast_generator_removes_qwen_thinking_blocks() -> None:
    client = FakeZaprosClient(
        FakeResponse(
            "<think>Скрытое рассуждение не должно попасть в интерфейс.</think>\n"
            "Прогноз: рост ВВП и снижение инфляции поддерживают умеренно позитивный сценарий.",
        ),
    )
    generator = generator_with(client)

    result = await generator.generate(
        request=GeminiForecastRequest(
            scope=GeminiForecastScope.TOPIC,
            model_name="tfidf-logreg",
            topic=topic(),
            news_id=None,
        ),
    )

    assert "<think>" not in result.prediction
    assert "Скрытое рассуждение" not in result.prediction
    assert result.prediction == (
        "Прогноз: рост ВВП и снижение инфляции поддерживают умеренно позитивный сценарий."
    )
