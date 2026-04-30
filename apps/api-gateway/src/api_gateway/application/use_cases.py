from api_gateway.application.ports import AnalysisClient, DialogClient, RetrievalClient
from economic_news_contracts.analysis import AnalyzeNewsRequest, AnalyzeNewsResponse
from economic_news_contracts.chat import ChatRequest, ChatResponse
from economic_news_contracts.dialog import (
    DialogContextNews,
    DialogImpactSummary,
    GenerateDialogRequest,
)
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


class ChatUseCase:
    def __init__(
        self,
        retrieval_client: RetrievalClient,
        analysis_client: AnalysisClient,
        dialog_client: DialogClient,
    ) -> None:
        self._retrieval_client = retrieval_client
        self._analysis_client = analysis_client
        self._dialog_client = dialog_client

    async def execute(self, request: ChatRequest) -> ChatResponse:
        search_response = await self._retrieval_client.search(
            SearchNewsRequest(
                query=request.question,
                limit=request.limit,
                source=request.source,
            ),
        )

        sources: list[DialogContextNews] = []
        impact_summaries: list[DialogImpactSummary] = []
        for result in search_response.results:
            sources.append(
                DialogContextNews(
                    id=result.id,
                    title=result.title,
                    text=result.text,
                    source=result.source,
                    score=result.score,
                    published_at=result.published_at,
                    metadata=result.metadata,
                ),
            )
            analysis_response = await self._analysis_client.analyze(
                AnalyzeNewsRequest(
                    text=result.text,
                    analysis_model=request.analysis_model,
                ),
            )
            impact_summaries.append(
                DialogImpactSummary(
                    news_id=result.id,
                    model_name=analysis_response.model_name,
                    impact=analysis_response.impact,
                    confidence=analysis_response.confidence,
                    explanation=analysis_response.explanation,
                ),
            )

        dialog_response = await self._dialog_client.generate(
            GenerateDialogRequest(
                question=request.question,
                context=sources,
                impact_summaries=impact_summaries,
            ),
        )

        return ChatResponse(
            answer=dialog_response.answer,
            sources=sources,
            impact_summaries=impact_summaries,
            analysis_model=request.analysis_model,
            metadata={
                "dialog_model_name": dialog_response.model_name,
                "used_context_ids": dialog_response.used_context_ids,
            },
        )
