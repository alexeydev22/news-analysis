from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from api_gateway.application.errors import (
    AnalysisServiceUnavailableError,
    DialogServiceUnavailableError,
    RetrievalServiceUnavailableError,
)
from api_gateway.application.use_cases import (
    ChatStreamEvent,
    ChatStreamUseCase,
    ChatUseCase,
)
from api_gateway.presentation.router import router
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider, setup_dishka
from economic_news_contracts.analysis import AnalysisModelName, ImpactLabel
from economic_news_contracts.chat import ChatRequest, ChatResponse
from economic_news_contracts.dialog import DialogContextNews, DialogImpactSummary
from economic_news_framework.apps import create_service_app
from fastapi.testclient import TestClient


class StubChatUseCase(ChatUseCase):
    def __init__(self, error: Exception | None = None) -> None:
        self.request: ChatRequest | None = None
        self._error = error

    async def execute(self, request: ChatRequest) -> ChatResponse:
        self.request = request
        if self._error is not None:
            raise self._error
        return ChatResponse(
            answer=f"Ответ на вопрос: {request.question}",
            sources=[
                DialogContextNews(
                    id="news-1",
                    title="GDP grows",
                    text="GDP grew by 2 percent.",
                    source=request.source or "demo",
                    score=0.75,
                    metadata={"limit": request.limit},
                ),
            ],
            impact_summaries=[
                DialogImpactSummary(
                    news_id="news-1",
                    model_name=request.analysis_model,
                    impact=ImpactLabel.POSITIVE,
                    confidence=0.82,
                    explanation="Рост ВВП обычно поддерживает рынок.",
                ),
            ],
            analysis_model=request.analysis_model,
            metadata={
                "dialog_model_name": "template-dialog-generator",
                "used_context_ids": ["news-1"],
            },
        )


class StubChatStreamUseCase(ChatStreamUseCase):
    def __init__(self, error: Exception | None = None) -> None:
        self.request: ChatRequest | None = None
        self._error = error

    async def stream(self, request: ChatRequest):
        self.request = request
        yield ChatStreamEvent(
            event="chat_started",
            data={
                "question": request.question,
                "analysis_model": request.analysis_model.value,
                "limit": request.limit,
                "source": request.source,
            },
        )
        if self._error is not None:
            raise self._error
        yield ChatStreamEvent(event="done", data={"status": "ok"})


class ChatProvider(Provider):
    def __init__(
        self,
        use_case: ChatUseCase,
        stream_use_case: ChatStreamUseCase | None = None,
    ) -> None:
        super().__init__()
        self._use_case = use_case
        self._stream_use_case = stream_use_case or StubChatStreamUseCase()

    @provide(scope=Scope.APP)
    def chat_use_case(self) -> ChatUseCase:
        return self._use_case

    @provide(scope=Scope.APP)
    def chat_stream_use_case(self) -> ChatStreamUseCase:
        return self._stream_use_case


def make_client(
    use_case: ChatUseCase,
    stream_use_case: ChatStreamUseCase | None = None,
) -> TestClient:
    app = create_service_app(
        service_name="api-gateway",
        routers=(router,),
        log_level="INFO",
    )
    container = make_async_container(
        ChatProvider(use_case, stream_use_case),
        FastapiProvider(),
    )
    setup_dishka(container=container, app=app)

    @asynccontextmanager
    async def close_container(_: object) -> AsyncIterator[None]:
        yield
        await container.close()

    app.router.lifespan_context = close_container
    return TestClient(app)


def test_chat_endpoint_returns_chat_response() -> None:
    use_case = StubChatUseCase()

    with make_client(use_case) as client:
        response = client.post(
            "/api/v1/chat",
            json={
                "question": "  Что значит рост ВВП?  ",
                "analysis_model": "embedding-logreg",
                "limit": 2,
                "source": "demo",
            },
        )

    assert response.status_code == 200
    assert use_case.request == ChatRequest(
        question="Что значит рост ВВП?",
        analysis_model=AnalysisModelName.EMBEDDING_LOGREG,
        limit=2,
        source="demo",
    )
    assert response.json() == {
        "answer": "Ответ на вопрос: Что значит рост ВВП?",
        "sources": [
            {
                "id": "news-1",
                "title": "GDP grows",
                "text": "GDP grew by 2 percent.",
                "source": "demo",
                "score": 0.75,
                "published_at": None,
                "metadata": {"limit": 2},
            },
        ],
        "impact_summaries": [
            {
                "news_id": "news-1",
                "model_name": "embedding-logreg",
                "impact": "positive",
                "confidence": 0.82,
                "explanation": "Рост ВВП обычно поддерживает рынок.",
            },
        ],
        "analysis_model": "embedding-logreg",
        "metadata": {
            "dialog_model_name": "template-dialog-generator",
            "used_context_ids": ["news-1"],
        },
    }


def test_chat_endpoint_maps_analysis_unavailable_error_to_503() -> None:
    use_case = StubChatUseCase(
        AnalysisServiceUnavailableError("analysis-service is unavailable"),
    )

    with make_client(use_case) as client:
        response = client.post("/api/v1/chat", json={"question": "Что с ВВП?"})

    assert response.status_code == 503
    assert response.json() == {"detail": "analysis-service is unavailable"}


def test_chat_endpoint_maps_retrieval_unavailable_error_to_503() -> None:
    use_case = StubChatUseCase(
        RetrievalServiceUnavailableError("connection refused at 10.0.0.12"),
    )

    with make_client(use_case) as client:
        response = client.post("/api/v1/chat", json={"question": "Что с ВВП?"})

    assert response.status_code == 503
    assert response.json() == {"detail": "retrieval-service is unavailable"}


def test_chat_endpoint_maps_dialog_unavailable_error_to_503() -> None:
    use_case = StubChatUseCase(
        DialogServiceUnavailableError("connection refused at 10.0.0.13"),
    )

    with make_client(use_case) as client:
        response = client.post("/api/v1/chat", json={"question": "Что с ВВП?"})

    assert response.status_code == 503
    assert response.json() == {"detail": "dialog-service is unavailable"}


def test_chat_stream_endpoint_returns_sse_events() -> None:
    stream_use_case = StubChatStreamUseCase()

    with make_client(StubChatUseCase(), stream_use_case) as client:
        with client.stream(
            "POST",
            "/api/v1/chat/stream",
            json={
                "question": "  Что значит рост ВВП?  ",
                "analysis_model": "embedding-logreg",
                "limit": 2,
                "source": "demo",
            },
        ) as response:
            body = response.read().decode()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert stream_use_case.request == ChatRequest(
        question="Что значит рост ВВП?",
        analysis_model=AnalysisModelName.EMBEDDING_LOGREG,
        limit=2,
        source="demo",
    )
    assert "event: chat_started\n" in body
    assert (
        'data: {"question":"Что значит рост ВВП?",'
        '"analysis_model":"embedding-logreg","limit":2,"source":"demo"}\n\n'
    ) in body
    assert "event: done\n" in body
    assert 'data: {"status":"ok"}\n\n' in body


def test_chat_stream_endpoint_maps_stream_error_to_sse_error_event() -> None:
    stream_use_case = StubChatStreamUseCase(
        AnalysisServiceUnavailableError("connection refused at 10.0.0.12"),
    )

    with make_client(StubChatUseCase(), stream_use_case) as client:
        with client.stream(
            "POST",
            "/api/v1/chat/stream",
            json={"question": "Что с ВВП?"},
        ) as response:
            body = response.read().decode()

    assert response.status_code == 200
    assert "event: error\n" in body
    assert 'data: {"stage":"analysis","detail":"analysis-service is unavailable"}\n\n' in body
    assert "connection refused" not in body
