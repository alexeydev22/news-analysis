import pytest
from analysis_service.infrastructure.groq_forecast_client import (
    GroqEconomicForecastGenerator,
)
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
                source="demo",
                impact=ImpactLabel.POSITIVE,
                score=0.91,
            ),
            TopicForecastNewsItemResponse(
                id="news-2",
                title="Inflation slows",
                source="demo",
                impact=ImpactLabel.POSITIVE,
                score=0.72,
            ),
        ],
    )


def generator_with(client: FakeZaprosClient) -> GroqEconomicForecastGenerator:
    return GroqEconomicForecastGenerator(
        base_url="https://api.groq.com/openai",
        api_key="test-key",
        model_name="qwen/qwen3-32b",
        timeout_seconds=30.0,
        temperature=0.2,
        max_tokens=700,
        client=client,
    )


@pytest.mark.asyncio
async def test_groq_forecast_generator_sends_prompt_and_parses_answer() -> None:
    client = FakeZaprosClient(FakeResponse("Рынок может получить поддержку."))
    generator = generator_with(client)

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
    messages = payload["messages"]
    assert isinstance(messages, list)
    system_message = messages[0]
    user_message = messages[1]
    assert isinstance(system_message, dict)
    assert isinstance(user_message, dict)
    assert "экономический аналитик" in str(system_message["content"])
    assert "осторожный сценарный прогноз" in str(system_message["content"])
    assert "финансовой рекомендации" in str(system_message["content"])
    assert "Область прогноза: topic" in str(user_message["content"])
    assert "Сделай краткий сценарный прогноз" in str(user_message["content"])
    assert result.provider == "groq"
    assert result.model_name == "qwen/qwen3-32b"
    assert result.scope == GroqForecastScope.TOPIC
    assert result.prediction == "Рынок может получить поддержку."
    assert "не финансовая рекомендация" in result.disclaimer


@pytest.mark.asyncio
async def test_topic_scope_uses_topic_target_even_when_news_id_is_present() -> None:
    client = FakeZaprosClient(FakeResponse("Тема сохраняет умеренно позитивный сценарий."))
    generator = generator_with(client)

    result = await generator.generate(
        request=GroqForecastRequest(
            scope=GroqForecastScope.TOPIC,
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
        request=GroqForecastRequest(
            scope=GroqForecastScope.NEWS,
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
    assert "GDP grows" not in user_prompt
    assert result.target_id == "news-2"
    assert result.metadata["news_count"] == 1
