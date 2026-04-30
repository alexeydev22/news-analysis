import pytest
from api_gateway.application.errors import DialogServiceUnavailableError
from api_gateway.application.use_cases import ChatUseCase
from economic_news_contracts.analysis import (
    AnalysisModelName,
    AnalyzeNewsRequest,
    AnalyzeNewsResponse,
    ImpactLabel,
)
from economic_news_contracts.chat import ChatRequest
from economic_news_contracts.dialog import GenerateDialogRequest, GenerateDialogResponse
from economic_news_contracts.retrieval import (
    IndexNewsRequest,
    IndexNewsResponse,
    SearchNewsRequest,
    SearchNewsResponse,
    SearchNewsResult,
)


class FakeRetrievalClient:
    def __init__(self) -> None:
        self.search_request: SearchNewsRequest | None = None

    async def index(self, request: IndexNewsRequest) -> IndexNewsResponse:
        return IndexNewsResponse(indexed_count=0, collection_name="economic_news")

    async def search(self, request: SearchNewsRequest) -> SearchNewsResponse:
        self.search_request = request
        return SearchNewsResponse(
            results=[
                SearchNewsResult(
                    id="news-1",
                    score=0.75,
                    title="GDP grows",
                    text="GDP grew by 2 percent.",
                    source="demo",
                    metadata={"sector": "macro"},
                ),
                SearchNewsResult(
                    id="news-2",
                    score=0.51,
                    title="Inflation slows",
                    text="Inflation slowed in April.",
                    source="demo",
                ),
            ],
        )


class FakeAnalysisClient:
    def __init__(self) -> None:
        self.requests: list[AnalyzeNewsRequest] = []

    async def analyze(self, request: AnalyzeNewsRequest) -> AnalyzeNewsResponse:
        self.requests.append(request)
        return AnalyzeNewsResponse(
            model_name=request.analysis_model,
            impact=ImpactLabel.POSITIVE,
            confidence=0.82,
            explanation=f"Позитивное влияние: {request.text}",
        )


class FakeDialogClient:
    def __init__(self) -> None:
        self.request: GenerateDialogRequest | None = None

    async def generate(self, request: GenerateDialogRequest) -> GenerateDialogResponse:
        self.request = request
        return GenerateDialogResponse(
            answer="Рост ВВП выглядит позитивным фактором.",
            used_context_ids=["news-1"],
            model_name="template-dialog-generator",
            metadata={"context_count": len(request.context)},
        )


class FailingDialogClient:
    async def generate(self, request: GenerateDialogRequest) -> GenerateDialogResponse:
        raise DialogServiceUnavailableError("dialog-service is unavailable")


@pytest.mark.asyncio
async def test_chat_use_case_orchestrates_search_analysis_and_dialog() -> None:
    retrieval_client = FakeRetrievalClient()
    analysis_client = FakeAnalysisClient()
    dialog_client = FakeDialogClient()
    use_case = ChatUseCase(
        retrieval_client=retrieval_client,
        analysis_client=analysis_client,
        dialog_client=dialog_client,
    )

    response = await use_case.execute(
        ChatRequest(
            question="Что значит рост ВВП?",
            analysis_model=AnalysisModelName.EMBEDDING_LOGREG,
            limit=2,
            source="demo",
        ),
    )

    assert retrieval_client.search_request == SearchNewsRequest(
        query="Что значит рост ВВП?",
        limit=2,
        source="demo",
    )
    assert [request.text for request in analysis_client.requests] == [
        "GDP grew by 2 percent.",
        "Inflation slowed in April.",
    ]
    assert {request.analysis_model for request in analysis_client.requests} == {
        AnalysisModelName.EMBEDDING_LOGREG,
    }
    assert dialog_client.request is not None
    assert dialog_client.request.question == "Что значит рост ВВП?"
    assert [source.id for source in dialog_client.request.context] == ["news-1", "news-2"]
    assert [
        summary.news_id for summary in dialog_client.request.impact_summaries
    ] == ["news-1", "news-2"]
    assert response.answer == "Рост ВВП выглядит позитивным фактором."
    assert [source.id for source in response.sources] == ["news-1", "news-2"]
    assert response.impact_summaries[0].model_name == AnalysisModelName.EMBEDDING_LOGREG
    assert response.analysis_model == AnalysisModelName.EMBEDDING_LOGREG
    assert response.metadata == {
        "dialog_model_name": "template-dialog-generator",
        "used_context_ids": ["news-1"],
    }


@pytest.mark.asyncio
async def test_chat_use_case_preserves_dialog_unavailable_error() -> None:
    use_case = ChatUseCase(
        retrieval_client=FakeRetrievalClient(),
        analysis_client=FakeAnalysisClient(),
        dialog_client=FailingDialogClient(),
    )

    with pytest.raises(
        DialogServiceUnavailableError,
        match="dialog-service is unavailable",
    ):
        await use_case.execute(ChatRequest(question="Что значит рост ВВП?"))
