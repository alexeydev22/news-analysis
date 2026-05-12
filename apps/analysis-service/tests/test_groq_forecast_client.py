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
