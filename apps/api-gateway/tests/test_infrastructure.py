import asyncio
from typing import Any, cast

import pytest
from api_gateway.application.errors import AnalysisServiceUnavailableError
from api_gateway.infrastructure.analysis_client import (
    ZaprosAnalysisClient,
    _make_zapros_client,
)
from economic_news_contracts.analysis import (
    AnalysisModelName,
    AnalyzeNewsRequest,
    ImpactLabel,
)
from zapros import Response


class FakeResponse:
    def __init__(self, status: int, payload: dict[str, object]) -> None:
        self.status = status
        self._payload = payload

    @property
    def json(self) -> dict[str, object]:
        return self._payload


class FakeZaprosClient:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.url: str | None = None
        self.json_payload: dict[str, object] | None = None

    async def post(self, url: str, json: dict[str, object]) -> Any:
        self.url = url
        self.json_payload = json
        return self.response


class RaisingZaprosClient:
    async def post(self, url: str, json: dict[str, object]) -> FakeResponse:
        raise OSError("connection refused")


class SlowZaprosClient:
    async def post(self, url: str, json: dict[str, object]) -> FakeResponse:
        await asyncio.sleep(0.05)
        return FakeResponse(status=200, payload=analysis_payload())


class FakeZaprosClientContext:
    def __init__(self, response: FakeResponse) -> None:
        self._client = FakeZaprosClient(response)

    async def __aenter__(self) -> FakeZaprosClient:
        return self._client

    async def __aexit__(self, *args: object) -> None:
        return None


class RecordingClientFactory:
    def __init__(self, response: FakeResponse) -> None:
        self.timeout_seconds: float | None = None
        self.context = FakeZaprosClientContext(response)

    def __call__(self, timeout_seconds: float) -> FakeZaprosClientContext:
        self.timeout_seconds = timeout_seconds
        return self.context


def analysis_payload() -> dict[str, Any]:
    return {
        "model_name": "tfidf-logreg",
        "impact": "positive",
        "confidence": 0.91,
        "explanation": "Позитивное влияние.",
        "metadata": {"source": "static"},
    }


def test_zapros_analysis_client_keeps_std_handler_timeout_disabled() -> None:
    client = _make_zapros_client(timeout_seconds=5.0)
    handler = cast(Any, client.handler)

    assert handler.total_timeout is None


@pytest.mark.asyncio
async def test_zapros_analysis_client_sends_contract_payload() -> None:
    transport = FakeZaprosClient(
        FakeResponse(
            status=200,
            payload=analysis_payload(),
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
async def test_zapros_analysis_client_reads_zapros_response_json_property() -> None:
    transport = FakeZaprosClient(Response(200, json=analysis_payload()))
    client = ZaprosAnalysisClient(
        base_url="http://analysis-service:8000",
        timeout_seconds=3.0,
        client=transport,
    )

    response = await client.analyze(AnalyzeNewsRequest(text="Экспорт вырос"))

    assert response.impact == ImpactLabel.POSITIVE
    assert response.confidence == 0.91


@pytest.mark.asyncio
async def test_zapros_analysis_client_passes_timeout_to_real_client_factory() -> None:
    factory = RecordingClientFactory(FakeResponse(status=200, payload=analysis_payload()))
    client = ZaprosAnalysisClient(
        base_url="http://analysis-service:8000",
        timeout_seconds=4.5,
        client_factory=factory,
    )

    await client.analyze(AnalyzeNewsRequest(text="Экспорт вырос"))

    assert factory.timeout_seconds == 4.5


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


@pytest.mark.asyncio
async def test_zapros_analysis_client_maps_timeout() -> None:
    client = ZaprosAnalysisClient(
        base_url="http://analysis-service:8000",
        timeout_seconds=0.001,
        client=SlowZaprosClient(),
    )

    with pytest.raises(AnalysisServiceUnavailableError):
        await client.analyze(AnalyzeNewsRequest(text="Рынок снизился"))
