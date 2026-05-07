# API Gateway Chat SSE Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `POST /api/v1/chat/stream` to `api-gateway` with deterministic SSE progress events for the existing economic-news chat pipeline.

**Architecture:** Keep orchestration in the application layer through a new `ChatStreamUseCase` that yields domain-neutral `ChatStreamEvent` values. Keep HTTP/SSE mechanics in presentation via a small formatter and a FastAPI `StreamingResponse`. Reuse existing clients and error classes so the non-streaming `/api/v1/chat` endpoint remains unchanged.

**Tech Stack:** Python 3.13, FastAPI `StreamingResponse`, Dishka, Pydantic contracts, existing Zapros clients, pytest, ruff, ty.

---

## File Structure

- Modify `apps/api-gateway/src/api_gateway/application/use_cases.py`
  - Add `ChatStreamEvent`.
  - Add `ChatStreamUseCase`.
  - Extract small private helpers only if needed to keep `ChatUseCase` and `ChatStreamUseCase` aligned.
- Modify `apps/api-gateway/src/api_gateway/main/container.py`
  - Provide `ChatStreamUseCase` through Dishka.
- Create `apps/api-gateway/src/api_gateway/presentation/sse.py`
  - Format application events into SSE wire text.
  - Map application errors into sanitized stream error events.
- Modify `apps/api-gateway/src/api_gateway/presentation/router.py`
  - Add `POST /api/v1/chat/stream`.
  - Return `StreamingResponse`.
- Modify `apps/api-gateway/tests/test_chat_use_cases.py`
  - Add application-level stream tests.
- Modify `apps/api-gateway/tests/test_api_chat.py`
  - Add route-level SSE tests.
- Create `apps/api-gateway/tests/test_sse.py`
  - Add formatter tests.
- Modify `README.md`
  - Document the streaming chat endpoint briefly.

---

### Task 1: Application Stream Use Case

**Files:**
- Modify: `apps/api-gateway/src/api_gateway/application/use_cases.py`
- Test: `apps/api-gateway/tests/test_chat_use_cases.py`

- [ ] **Step 1: Write failing tests for successful stream events**

Append these imports in `apps/api-gateway/tests/test_chat_use_cases.py`:

```python
from api_gateway.application.use_cases import ChatStreamUseCase
```

Append this helper:

```python
async def collect_stream_events(use_case: ChatStreamUseCase, request: ChatRequest) -> list[tuple[str, dict[str, object]]]:
    return [(event.event, event.data) async for event in use_case.stream(request)]
```

Append this test:

```python
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
```

- [ ] **Step 2: Write failing tests for error propagation**

Append fake failing clients:

```python
class FailingRetrievalClient(FakeRetrievalClient):
    async def search(self, request: SearchNewsRequest) -> SearchNewsResponse:
        raise RetrievalServiceUnavailableError("connection refused at 10.0.0.11")


class FailingAnalysisClient(FakeAnalysisClient):
    async def analyze(self, request: AnalyzeNewsRequest) -> AnalyzeNewsResponse:
        raise AnalysisServiceUnavailableError("connection refused at 10.0.0.12")
```

Update the existing top import:

```python
from api_gateway.application.errors import (
    AnalysisServiceUnavailableError,
    DialogServiceUnavailableError,
    RetrievalServiceUnavailableError,
)
```

Append tests:

```python
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
```

- [ ] **Step 3: Run tests and verify they fail**

Run:

```bash
uv run pytest apps/api-gateway/tests/test_chat_use_cases.py -v -W error
```

Expected: fail with `ImportError` or `NameError` for `ChatStreamUseCase`.

- [ ] **Step 4: Implement stream use case**

Modify `apps/api-gateway/src/api_gateway/application/use_cases.py`.

Add imports:

```python
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any
```

Add event model near the top:

```python
@dataclass(frozen=True, slots=True)
class ChatStreamEvent:
    event: str
    data: dict[str, Any]
```

Add helpers above `ChatUseCase`:

```python
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
```

Add `SearchNewsResult` and `GenerateDialogResponse` to existing imports from contracts.

Replace the source construction in `ChatUseCase.execute` with `_context_from_search_result(result)`, and replace final `ChatResponse(...)` construction with `_chat_response(...)`.

Add `ChatStreamUseCase` after `ChatUseCase`:

```python
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
        sources = [_context_from_search_result(result) for result in search_response.results]
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
```

- [ ] **Step 5: Run task tests**

Run:

```bash
uv run pytest apps/api-gateway/tests/test_chat_use_cases.py -v -W error
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

Run:

```bash
git add apps/api-gateway/src/api_gateway/application/use_cases.py apps/api-gateway/tests/test_chat_use_cases.py
git commit -m "feat: добавить stream use case для чата"
```

---

### Task 2: SSE Formatter

**Files:**
- Create: `apps/api-gateway/src/api_gateway/presentation/sse.py`
- Test: `apps/api-gateway/tests/test_sse.py`

- [ ] **Step 1: Write failing formatter tests**

Create `apps/api-gateway/tests/test_sse.py`:

```python
import json

from api_gateway.application.errors import (
    AnalysisServiceUnavailableError,
    DialogServiceUnavailableError,
    RetrievalServiceUnavailableError,
)
from api_gateway.application.use_cases import ChatStreamEvent
from api_gateway.presentation.sse import format_sse_event, stream_error_event


def test_format_sse_event_serializes_event_and_json_data() -> None:
    payload = format_sse_event(
        ChatStreamEvent(
            event="sources_found",
            data={"count": 1, "sources": [{"id": "news-1"}]},
        ),
    )

    assert payload.startswith("event: sources_found\n")
    assert payload.endswith("\n\n")
    data_line = payload.splitlines()[1]
    assert data_line.startswith("data: ")
    assert json.loads(data_line.removeprefix("data: ")) == {
        "count": 1,
        "sources": [{"id": "news-1"}],
    }


def test_format_sse_event_keeps_unicode_readable() -> None:
    payload = format_sse_event(
        ChatStreamEvent(event="answer_completed", data={"answer": "Рост ВВП"}),
    )

    assert "Рост ВВП" in payload


def test_stream_error_event_maps_retrieval_error() -> None:
    event = stream_error_event(RetrievalServiceUnavailableError("internal url leaked"))

    assert event == ChatStreamEvent(
        event="error",
        data={"stage": "retrieval", "detail": "retrieval-service is unavailable"},
    )


def test_stream_error_event_maps_analysis_error() -> None:
    event = stream_error_event(AnalysisServiceUnavailableError("internal url leaked"))

    assert event == ChatStreamEvent(
        event="error",
        data={"stage": "analysis", "detail": "analysis-service is unavailable"},
    )


def test_stream_error_event_maps_dialog_error() -> None:
    event = stream_error_event(DialogServiceUnavailableError("internal url leaked"))

    assert event == ChatStreamEvent(
        event="error",
        data={"stage": "dialog", "detail": "dialog-service is unavailable"},
    )


def test_stream_error_event_maps_unknown_error_without_details() -> None:
    event = stream_error_event(RuntimeError("secret stack detail"))

    assert event == ChatStreamEvent(
        event="error",
        data={"stage": "unknown", "detail": "chat stream is unavailable"},
    )
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run pytest apps/api-gateway/tests/test_sse.py -v -W error
```

Expected: fail with `ModuleNotFoundError` for `api_gateway.presentation.sse`.

- [ ] **Step 3: Implement formatter**

Create `apps/api-gateway/src/api_gateway/presentation/sse.py`:

```python
import json

from api_gateway.application.errors import (
    AnalysisServiceUnavailableError,
    DialogServiceUnavailableError,
    RetrievalServiceUnavailableError,
)
from api_gateway.application.use_cases import ChatStreamEvent


def format_sse_event(event: ChatStreamEvent) -> str:
    data = json.dumps(event.data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event.event}\ndata: {data}\n\n"


def stream_error_event(error: Exception) -> ChatStreamEvent:
    if isinstance(error, RetrievalServiceUnavailableError):
        return ChatStreamEvent(
            event="error",
            data={"stage": "retrieval", "detail": "retrieval-service is unavailable"},
        )
    if isinstance(error, AnalysisServiceUnavailableError):
        return ChatStreamEvent(
            event="error",
            data={"stage": "analysis", "detail": "analysis-service is unavailable"},
        )
    if isinstance(error, DialogServiceUnavailableError):
        return ChatStreamEvent(
            event="error",
            data={"stage": "dialog", "detail": "dialog-service is unavailable"},
        )
    return ChatStreamEvent(
        event="error",
        data={"stage": "unknown", "detail": "chat stream is unavailable"},
    )
```

- [ ] **Step 4: Run formatter tests**

Run:

```bash
uv run pytest apps/api-gateway/tests/test_sse.py -v -W error
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add apps/api-gateway/src/api_gateway/presentation/sse.py apps/api-gateway/tests/test_sse.py
git commit -m "feat: добавить форматирование sse событий"
```

---

### Task 3: Stream Route and DI

**Files:**
- Modify: `apps/api-gateway/src/api_gateway/main/container.py`
- Modify: `apps/api-gateway/src/api_gateway/presentation/router.py`
- Modify: `apps/api-gateway/tests/test_api_chat.py`

- [ ] **Step 1: Write failing route tests**

Modify imports in `apps/api-gateway/tests/test_api_chat.py`:

```python
from api_gateway.application.use_cases import ChatStreamEvent, ChatStreamUseCase, ChatUseCase
```

Add stream stub:

```python
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
```

Update provider and client factory:

```python
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
```

Append tests:

```python
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
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run pytest apps/api-gateway/tests/test_api_chat.py -v -W error
```

Expected: fail because `ChatStreamUseCase` is not provided or route does not exist.

- [ ] **Step 3: Provide ChatStreamUseCase through Dishka**

Modify `apps/api-gateway/src/api_gateway/main/container.py`.

Import:

```python
from api_gateway.application.use_cases import (
    AnalyzeNewsUseCase,
    ChatStreamUseCase,
    ChatUseCase,
    IndexNewsUseCase,
    SearchNewsUseCase,
)
```

Add provider method next to existing chat provider:

```python
@provide(scope=Scope.APP)
def chat_stream_use_case(
    self,
    retrieval_client: RetrievalClient,
    analysis_client: AnalysisClient,
    dialog_client: DialogClient,
) -> ChatStreamUseCase:
    return ChatStreamUseCase(
        retrieval_client=retrieval_client,
        analysis_client=analysis_client,
        dialog_client=dialog_client,
    )
```

- [ ] **Step 4: Implement stream route**

Modify `apps/api-gateway/src/api_gateway/presentation/router.py`.

Add imports:

```python
from collections.abc import AsyncIterator

from api_gateway.application.use_cases import ChatStreamUseCase
from api_gateway.presentation.sse import format_sse_event, stream_error_event
from fastapi.responses import StreamingResponse
```

Add private generator near route functions:

```python
async def _chat_sse_stream(
    request: ChatRequest,
    use_case: ChatStreamUseCase,
) -> AsyncIterator[str]:
    try:
        async for event in use_case.stream(request):
            yield format_sse_event(event)
    except Exception as error:
        yield format_sse_event(stream_error_event(error))
```

Add route:

```python
@router.post("/chat/stream")
@inject
async def chat_stream(
    request: ChatRequest,
    use_case: FromDishka[ChatStreamUseCase],
) -> StreamingResponse:
    return StreamingResponse(
        _chat_sse_stream(request, use_case),
        media_type="text/event-stream",
    )
```

- [ ] **Step 5: Run route tests**

Run:

```bash
uv run pytest apps/api-gateway/tests/test_api_chat.py -v -W error
```

Expected: all tests pass.

- [ ] **Step 6: Run focused api-gateway tests**

Run:

```bash
uv run pytest apps/api-gateway/tests -v -W error
```

Expected: all api-gateway tests pass.

- [ ] **Step 7: Commit**

Run:

```bash
git add apps/api-gateway/src/api_gateway/main/container.py apps/api-gateway/src/api_gateway/presentation/router.py apps/api-gateway/tests/test_api_chat.py
git commit -m "feat: добавить sse endpoint для чата"
```

---

### Task 4: README and Final Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document streaming endpoint**

Add this section after the existing chat or service examples in `README.md`:

````markdown
## Chat SSE endpoint

`api-gateway` exposes pipeline-progress streaming for the chat flow:

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H 'Content-Type: application/json' \
  -H 'Accept: text/event-stream' \
  -d '{"question":"Что значит рост ВВП?","analysis_model":"tfidf-logreg","limit":5}'
```

The stream emits stage events: `chat_started`, `search_started`, `sources_found`,
`analysis_started`, `analysis_completed`, `answer_started`, `answer_completed`,
and `done`. If a downstream service fails after streaming starts, the response emits
one sanitized `error` event and closes the stream.
````

- [ ] **Step 2: Run all checks**

Run:

```bash
uv run ruff check apps packages research
uv run ty check apps packages research
uv run pytest packages apps research/tests -v -W error
docker compose -f deploy/compose.yaml config
```

Expected: all pass.

- [ ] **Step 3: Run Docker build if daemon is available**

Run:

```bash
docker compose -f deploy/compose.yaml build api-gateway
```

Expected: image builds successfully. If Docker daemon is not running, record the daemon error and continue without claiming Docker build passed.

- [ ] **Step 4: Commit docs**

Run:

```bash
git add README.md
git commit -m "docs: описать sse чат"
```

- [ ] **Step 5: Final branch review**

Request a final code review for `origin/dev..HEAD` with this checklist:

- stream event order matches the spec;
- `/api/v1/chat` behavior is unchanged;
- SSE formatter never leaks internal exception details;
- DI wiring resolves `ChatStreamUseCase`;
- tests cover success and downstream failures;
- no token-streaming, Redis, Taskiq or UI code was added.

Expected: reviewer returns `PASS` or only non-blocking comments.

---

## Plan Self-Review

Spec coverage:

- `POST /api/v1/chat/stream`: Task 3.
- Existing `/api/v1/chat` unchanged: Task 3 tests keep existing assertions.
- Deterministic event sequence: Task 1 tests event order.
- Application owns event semantics, presentation owns SSE formatting: Tasks 1 and 2.
- Sanitized downstream stream errors: Tasks 1, 2 and 3.
- No React UI, token streaming, background jobs or Redis: explicitly excluded from all tasks.
- Verification commands: Task 4.

Placeholder scan:

- No placeholders, deferred-work markers, vague test steps or vague edge-case steps remain.

Type consistency:

- `ChatStreamEvent.event` and `ChatStreamEvent.data` are used consistently by the use case, formatter and route tests.
- `ChatStreamUseCase.stream(request)` is the single streaming API.
- Existing contract models continue using `model_dump(mode="json")` for SSE-safe JSON payloads.
