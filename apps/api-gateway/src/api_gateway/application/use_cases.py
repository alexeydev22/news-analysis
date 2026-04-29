from economic_news_contracts.analysis import AnalyzeNewsRequest, AnalyzeNewsResponse

from api_gateway.application.ports import AnalysisClient


class AnalyzeNewsUseCase:
    def __init__(self, analysis_client: AnalysisClient) -> None:
        self._analysis_client = analysis_client

    async def execute(self, request: AnalyzeNewsRequest) -> AnalyzeNewsResponse:
        return await self._analysis_client.analyze(request)
