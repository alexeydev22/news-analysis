import pytest
from api_gateway.application.errors import AnalysisServiceUnavailableError
from api_gateway.infrastructure.analysis_client import ZaprosAnalysisClient
from economic_news_contracts.analysis import (
    AnalysisModelName,
    AnalyzeNewsRequest,
    ImpactLabel,
)


class FakeResponse:
    def __init__(self, status: int, payload: dict[str, object]) -> None:
        self.status = status
        self._payload = payload

    def json(self) -> dict[str, object]:
        return self._payload


class FakeZaprosClient:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.url: str | None = None
        self.json_payload: dict[str, object] | None = None

    async def post(self, url: str, json: dict[str, object]) -> FakeResponse:
        self.url = url
        self.json_payload = json
        return self.response


class RaisingZaprosClient:
    async def post(self, url: str, json: dict[str, object]) -> FakeResponse:
        raise OSError("connection refused")


@pytest.mark.asyncio
async def test_zapros_analysis_client_sends_contract_payload() -> None:
    transport = FakeZaprosClient(
        FakeResponse(
            status=200,
            payload={
                "model_name": "tfidf-logreg",
                "impact": "positive",
                "confidence": 0.91,
                "explanation": "Позитивное влияние.",
                "metadata": {"source": "static"},
            },
        ),
    )
    client = ZaprosAnalysisClient(
        base_url="http://analysis-service:8000",
        timeout_seconds=3.0,
        client=transport,
    )
    request = AnalyzeNewsRequest(
        text="Экспорт вырос",
        analysis_model=AnalysisModelName.TFIDF_LOGREG,
    )

    response = await client.analyze(request)

    assert transport.url == "http://analysis-service:8000/api/v1/analyze"
    assert transport.json_payload == {
        "text": "Экспорт вырос",
        "analysis_model": "tfidf-logreg",
    }
    assert response.impact == ImpactLabel.POSITIVE
    assert response.confidence == 0.91


@pytest.mark.asyncio
async def test_zapros_analysis_client_maps_5xx_to_unavailable_error() -> None:
    client = ZaprosAnalysisClient(
        base_url="http://analysis-service:8000/",
        timeout_seconds=3.0,
        client=FakeZaprosClient(FakeResponse(status=503, payload={"detail": "down"})),
    )

    with pytest.raises(AnalysisServiceUnavailableError):
        await client.analyze(AnalyzeNewsRequest(text="Рынок снизился"))


@pytest.mark.asyncio
async def test_zapros_analysis_client_maps_transport_error() -> None:
    client = ZaprosAnalysisClient(
        base_url="http://analysis-service:8000",
        timeout_seconds=3.0,
        client=RaisingZaprosClient(),
    )

    with pytest.raises(AnalysisServiceUnavailableError):
        await client.analyze(AnalyzeNewsRequest(text="Рынок снизился"))
