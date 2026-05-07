from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from api_gateway.application.ports import AnalysisClient, DialogClient, RetrievalClient
from economic_news_contracts.analysis import AnalyzeNewsRequest, AnalyzeNewsResponse
from economic_news_contracts.chat import ChatRequest, ChatResponse
from economic_news_contracts.dialog import (
    DialogContextNews,
    DialogImpactSummary,
    GenerateDialogRequest,
    GenerateDialogResponse,
)
from economic_news_contracts.retrieval import (
    IndexNewsRequest,
    IndexNewsResponse,
    SearchNewsRequest,
    SearchNewsResponse,
    SearchNewsResult,
)


@dataclass(frozen=True, slots=True)
class ChatStreamEvent:
    event: str
    data: dict[str, Any]


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


def _context_from_search_result(result: SearchNewsResult) -> DialogContextNews:
    return DialogContextNews(
        id=result.id,
        title=result.title,
        text=result.text,
        source=result.source,
        score=result.score,
        published_at=result.published_at,
        metadata=result.metadata,
    )


def _source_preview(source: DialogContextNews) -> dict[str, Any]:
    return {
        "id": source.id,
        "title": source.title,
        "source": source.source,
        "score": source.score,
        "published_at": source.published_at,
        "metadata": source.metadata,
    }


def _chat_response(
    *,
    request: ChatRequest,
    sources: list[DialogContextNews],
    impact_summaries: list[DialogImpactSummary],
    dialog_response: GenerateDialogResponse,
) -> ChatResponse:
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
            source = _context_from_search_result(result)
            sources.append(source)
            analysis_response = await self._analysis_client.analyze(
                AnalyzeNewsRequest(
                    text=f"{result.title}\n\n{result.text}",
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

        return _chat_response(
            request=request,
            sources=sources,
            impact_summaries=impact_summaries,
            dialog_response=dialog_response,
        )


class ChatStreamUseCase:
    def __init__(
        self,
        retrieval_client: RetrievalClient,
        analysis_client: AnalysisClient,
        dialog_client: DialogClient,
    ) -> None:
        self._retrieval_client = retrieval_client
        self._analysis_client = analysis_client
        self._dialog_client = dialog_client

    async def stream(self, request: ChatRequest) -> AsyncIterator[ChatStreamEvent]:
        yield ChatStreamEvent(
            event="chat_started",
            data={
                "question": request.question,
                "analysis_model": request.analysis_model.value,
                "limit": request.limit,
                "source": request.source,
            },
        )
        yield ChatStreamEvent(
            event="search_started",
            data={
                "query": request.question,
                "limit": request.limit,
                "source": request.source,
            },
        )

        search_response = await self._retrieval_client.search(
            SearchNewsRequest(
                query=request.question,
                limit=request.limit,
                source=request.source,
            ),
        )
        sources = [
            _context_from_search_result(result) for result in search_response.results
        ]
        yield ChatStreamEvent(
            event="sources_found",
            data={
                "count": len(sources),
                "sources": [_source_preview(source) for source in sources],
            },
        )
        yield ChatStreamEvent(
            event="analysis_started",
            data={
                "count": len(sources),
                "analysis_model": request.analysis_model.value,
            },
        )

        impact_summaries: list[DialogImpactSummary] = []
        for source in sources:
            analysis_response = await self._analysis_client.analyze(
                AnalyzeNewsRequest(
                    text=f"{source.title}\n\n{source.text}",
                    analysis_model=request.analysis_model,
                ),
            )
            impact_summaries.append(
                DialogImpactSummary(
                    news_id=source.id,
                    model_name=analysis_response.model_name,
                    impact=analysis_response.impact,
                    confidence=analysis_response.confidence,
                    explanation=analysis_response.explanation,
                ),
            )

        yield ChatStreamEvent(
            event="analysis_completed",
            data={
                "count": len(impact_summaries),
                "impact_summaries": [
                    summary.model_dump(mode="json") for summary in impact_summaries
                ],
            },
        )
        yield ChatStreamEvent(
            event="answer_started",
            data={
                "context_count": len(sources),
                "impact_summary_count": len(impact_summaries),
            },
        )

        dialog_response = await self._dialog_client.generate(
            GenerateDialogRequest(
                question=request.question,
                context=sources,
                impact_summaries=impact_summaries,
            ),
        )
        response = _chat_response(
            request=request,
            sources=sources,
            impact_summaries=impact_summaries,
            dialog_response=dialog_response,
        )
        yield ChatStreamEvent(
            event="answer_completed",
            data=response.model_dump(mode="json"),
        )
        yield ChatStreamEvent(event="done", data={"status": "ok"})
