import pytest
from api_gateway.application.errors import DialogServiceUnavailableError
from api_gateway.infrastructure.dialog_client import ZaprosDialogClient
from economic_news_contracts.analysis import AnalysisModelName, ImpactLabel
from economic_news_contracts.dialog import (
    DialogContextNews,
    DialogImpactSummary,
    GenerateDialogRequest,
)
from zapros import Response


class FakeZaprosClient:
    def __init__(self, response: Response) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def post(self, url: str, json: dict[str, object]) -> Response:
        self.calls.append((url, json))
        return self.response


class RaisingZaprosClient:
    async def post(self, url: str, json: dict[str, object]) -> Response:
        raise OSError("connection refused")


class FakeZaprosClientContext:
    def __init__(self, response: Response) -> None:
        self._client = FakeZaprosClient(response)

    async def __aenter__(self) -> FakeZaprosClient:
        return self._client

    async def __aexit__(self, *args: object) -> None:
        return None


class RecordingClientFactory:
    def __init__(self, response: Response) -> None:
        self.timeout_seconds: float | None = None
        self.context = FakeZaprosClientContext(response)

    def __call__(self, timeout_seconds: float) -> FakeZaprosClientContext:
        self.timeout_seconds = timeout_seconds
        return self.context


def dialog_request() -> GenerateDialogRequest:
    return GenerateDialogRequest(
        question="Что значит рост ВВП?",
        context=[
            DialogContextNews(
                id="news-1",
                title="GDP grows",
                text="GDP grew by 2 percent.",
                source="demo",
                score=0.75,
            ),
        ],
        impact_summaries=[
            DialogImpactSummary(
                news_id="news-1",
                model_name=AnalysisModelName.TFIDF_LOGREG,
                impact=ImpactLabel.POSITIVE,
                confidence=0.82,
                explanation="Позитивное влияние.",
            ),
        ],
    )


def dialog_payload() -> dict[str, object]:
    return {
        "answer": "Рост ВВП выглядит позитивным фактором.",
        "used_context_ids": ["news-1"],
        "model_name": "template-dialog-generator",
        "metadata": {"context_count": 1},
    }


@pytest.mark.asyncio
async def test_zapros_dialog_client_sends_contract_payload() -> None:
    transport = FakeZaprosClient(Response(200, json=dialog_payload()))
    client = ZaprosDialogClient(
        base_url="http://dialog-service:8000/",
        timeout_seconds=3.0,
        client=transport,
    )

    response = await client.generate(dialog_request())

    assert response.answer == "Рост ВВП выглядит позитивным фактором."
    assert transport.calls[0] == (
        "http://dialog-service:8000/api/v1/dialog/generate",
        {
            "question": "Что значит рост ВВП?",
            "context": [
                {
                    "id": "news-1",
                    "title": "GDP grows",
                    "text": "GDP grew by 2 percent.",
                    "source": "demo",
                    "score": 0.75,
                    "published_at": None,
                    "metadata": {},
                },
            ],
            "impact_summaries": [
                {
                    "news_id": "news-1",
                    "model_name": "tfidf-logreg",
                    "impact": "positive",
                    "confidence": 0.82,
                    "explanation": "Позитивное влияние.",
                },
            ],
            "language": "ru",
        },
    )


@pytest.mark.asyncio
async def test_zapros_dialog_client_reads_zapros_response_json_property() -> None:
    client = ZaprosDialogClient(
        base_url="http://dialog-service:8000",
        timeout_seconds=3.0,
        client=FakeZaprosClient(Response(200, json=dialog_payload())),
    )

    response = await client.generate(dialog_request())

    assert response.used_context_ids == ["news-1"]
    assert response.model_name == "template-dialog-generator"


@pytest.mark.asyncio
async def test_zapros_dialog_client_passes_timeout_to_real_client_factory() -> None:
    factory = RecordingClientFactory(Response(200, json=dialog_payload()))
    client = ZaprosDialogClient(
        base_url="http://dialog-service:8000",
        timeout_seconds=4.5,
        client_factory=factory,
    )

    await client.generate(dialog_request())

    assert factory.timeout_seconds == 4.5


@pytest.mark.asyncio
async def test_zapros_dialog_client_maps_4xx_and_5xx_to_unavailable_error() -> None:
    for status in (400, 503):
        client = ZaprosDialogClient(
            base_url="http://dialog-service:8000",
            timeout_seconds=3.0,
            client=FakeZaprosClient(Response(status, json={"detail": "down"})),
        )

        with pytest.raises(
            DialogServiceUnavailableError,
            match="dialog-service is unavailable",
        ):
            await client.generate(dialog_request())


@pytest.mark.asyncio
async def test_zapros_dialog_client_maps_transport_error() -> None:
    client = ZaprosDialogClient(
        base_url="http://dialog-service:8000",
        timeout_seconds=3.0,
        client=RaisingZaprosClient(),
    )

    with pytest.raises(
        DialogServiceUnavailableError,
        match="dialog-service is unavailable",
    ):
        await client.generate(dialog_request())
