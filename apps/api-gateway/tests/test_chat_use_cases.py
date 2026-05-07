import pytest
from api_gateway.application.errors import (
    AnalysisServiceUnavailableError,
    DialogServiceUnavailableError,
    RetrievalServiceUnavailableError,
)
from api_gateway.application.use_cases import ChatStreamUseCase, ChatUseCase
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


class FailingRetrievalClient(FakeRetrievalClient):
    async def search(self, request: SearchNewsRequest) -> SearchNewsResponse:
        raise RetrievalServiceUnavailableError("connection refused at 10.0.0.11")


class FailingAnalysisClient(FakeAnalysisClient):
    async def analyze(self, request: AnalyzeNewsRequest) -> AnalyzeNewsResponse:
        raise AnalysisServiceUnavailableError("connection refused at 10.0.0.12")


async def collect_stream_events(
    use_case: ChatStreamUseCase,
    request: ChatRequest,
) -> list[tuple[str, dict[str, object]]]:
    return [(event.event, event.data) async for event in use_case.stream(request)]


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
        "GDP grows\n\nGDP grew by 2 percent.",
        "Inflation slows\n\nInflation slowed in April.",
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


@pytest.mark.asyncio
async def test_chat_stream_use_case_yields_pipeline_events() -> None:
    retrieval_client = FakeRetrievalClient()
    analysis_client = FakeAnalysisClient()
    dialog_client = FakeDialogClient()
    use_case = ChatStreamUseCase(
        retrieval_client=retrieval_client,
        analysis_client=analysis_client,
        dialog_client=dialog_client,
    )

    events = await collect_stream_events(
        use_case,
        ChatRequest(
            question="Что значит рост ВВП?",
            analysis_model=AnalysisModelName.EMBEDDING_LOGREG,
            limit=2,
            source="demo",
        ),
    )

    assert [event for event, _ in events] == [
        "chat_started",
        "search_started",
        "sources_found",
        "analysis_started",
        "analysis_completed",
        "answer_started",
        "answer_completed",
        "done",
    ]
    assert events[0][1] == {
        "question": "Что значит рост ВВП?",
        "analysis_model": "embedding-logreg",
        "limit": 2,
        "source": "demo",
    }
    assert events[1][1] == {
        "query": "Что значит рост ВВП?",
        "limit": 2,
        "source": "demo",
    }
    assert events[2][1] == {
        "count": 2,
        "sources": [
            {
                "id": "news-1",
                "title": "GDP grows",
                "source": "demo",
                "score": 0.75,
                "published_at": None,
                "metadata": {"sector": "macro"},
            },
            {
                "id": "news-2",
                "title": "Inflation slows",
                "source": "demo",
                "score": 0.51,
                "published_at": None,
                "metadata": {},
            },
        ],
    }
    assert events[3][1] == {
        "count": 2,
        "analysis_model": "embedding-logreg",
    }
    assert events[4][1]["count"] == 2
    assert events[5][1] == {
        "context_count": 2,
        "impact_summary_count": 2,
    }
    assert events[6][1]["answer"] == "Рост ВВП выглядит позитивным фактором."
    assert events[6][1]["analysis_model"] == "embedding-logreg"
    assert events[7][1] == {"status": "ok"}


@pytest.mark.asyncio
async def test_chat_stream_use_case_preserves_retrieval_unavailable_error() -> None:
    use_case = ChatStreamUseCase(
        retrieval_client=FailingRetrievalClient(),
        analysis_client=FakeAnalysisClient(),
        dialog_client=FakeDialogClient(),
    )
    stream = use_case.stream(ChatRequest(question="Что с ВВП?"))

    first_event = await anext(stream)
    second_event = await anext(stream)

    assert first_event.event == "chat_started"
    assert second_event.event == "search_started"
    with pytest.raises(RetrievalServiceUnavailableError):
        await anext(stream)


@pytest.mark.asyncio
async def test_chat_stream_use_case_preserves_analysis_unavailable_error() -> None:
    use_case = ChatStreamUseCase(
        retrieval_client=FakeRetrievalClient(),
        analysis_client=FailingAnalysisClient(),
        dialog_client=FakeDialogClient(),
    )
    stream = use_case.stream(ChatRequest(question="Что с ВВП?"))

    emitted: list[str] = []
    with pytest.raises(AnalysisServiceUnavailableError):
        async for event in stream:
            emitted.append(event.event)

    assert emitted == [
        "chat_started",
        "search_started",
        "sources_found",
        "analysis_started",
    ]


@pytest.mark.asyncio
async def test_chat_stream_use_case_preserves_dialog_unavailable_error() -> None:
    use_case = ChatStreamUseCase(
        retrieval_client=FakeRetrievalClient(),
        analysis_client=FakeAnalysisClient(),
        dialog_client=FailingDialogClient(),
    )
    stream = use_case.stream(ChatRequest(question="Что с ВВП?"))

    emitted: list[str] = []
    with pytest.raises(DialogServiceUnavailableError):
        async for event in stream:
            emitted.append(event.event)

    assert emitted == [
        "chat_started",
        "search_started",
        "sources_found",
        "analysis_started",
        "analysis_completed",
        "answer_started",
    ]
