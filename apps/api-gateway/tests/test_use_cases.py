import pytest
from economic_news_contracts.analysis import (
    AnalysisModelName,
    AnalyzeNewsRequest,
    AnalyzeNewsResponse,
    ImpactLabel,
)

from api_gateway.application.errors import AnalysisServiceUnavailableError
from api_gateway.application.use_cases import AnalyzeNewsUseCase


class FakeAnalysisClient:
    def __init__(self) -> None:
        self.request: AnalyzeNewsRequest | None = None

    async def analyze(self, request: AnalyzeNewsRequest) -> AnalyzeNewsResponse:
        self.request = request
        return AnalyzeNewsResponse(
            model_name=request.analysis_model,
            impact=ImpactLabel.POSITIVE,
            confidence=0.82,
            explanation="Новость может поддержать рынок.",
            metadata={"source": "fake"},
        )


class FailingAnalysisClient:
    async def analyze(self, request: AnalyzeNewsRequest) -> AnalyzeNewsResponse:
        raise AnalysisServiceUnavailableError("analysis-service is unavailable")


@pytest.mark.asyncio
async def test_analyze_news_use_case_returns_client_response() -> None:
    client = FakeAnalysisClient()
    use_case = AnalyzeNewsUseCase(client)
    request = AnalyzeNewsRequest(
        text="ЦБ снизил ключевую ставку",
        analysis_model=AnalysisModelName.TFIDF_LOGREG,
    )

    response = await use_case.execute(request)

    assert client.request == request
    assert response.impact == ImpactLabel.POSITIVE
    assert response.confidence == 0.82


@pytest.mark.asyncio
async def test_analyze_news_use_case_preserves_unavailable_error() -> None:
    use_case = AnalyzeNewsUseCase(FailingAnalysisClient())
    request = AnalyzeNewsRequest(text="Биржевой индекс снизился")

    with pytest.raises(AnalysisServiceUnavailableError):
        await use_case.execute(request)
