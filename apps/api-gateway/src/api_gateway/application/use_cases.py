from api_gateway.application.ports import AnalysisClient, RetrievalClient
from economic_news_contracts.analysis import AnalyzeNewsRequest, AnalyzeNewsResponse
from economic_news_contracts.retrieval import (
    IndexNewsRequest,
    IndexNewsResponse,
    SearchNewsRequest,
    SearchNewsResponse,
)


class AnalyzeNewsUseCase:
    def __init__(self, analysis_client: AnalysisClient) -> None:
        self._analysis_client = analysis_client

    async def execute(self, request: AnalyzeNewsRequest) -> AnalyzeNewsResponse:
        return await self._analysis_client.analyze(request)


class IndexNewsUseCase:
    def __init__(self, retrieval_client: RetrievalClient) -> None:
        self._retrieval_client = retrieval_client

    async def execute(self, request: IndexNewsRequest) -> IndexNewsResponse:
        return await self._retrieval_client.index(request)


class SearchNewsUseCase:
    def __init__(self, retrieval_client: RetrievalClient) -> None:
        self._retrieval_client = retrieval_client

    async def execute(self, request: SearchNewsRequest) -> SearchNewsResponse:
        return await self._retrieval_client.search(request)
