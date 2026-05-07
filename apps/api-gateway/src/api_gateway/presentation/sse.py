import json

from api_gateway.application.errors import (
    AnalysisServiceUnavailableError,
    DialogServiceUnavailableError,
    RetrievalServiceUnavailableError,
)
from api_gateway.application.use_cases import ChatStreamEvent

ALLOWED_SSE_EVENT_NAMES = frozenset(
    {
        "chat_started",
        "search_started",
        "sources_found",
        "analysis_started",
        "analysis_completed",
        "answer_started",
        "answer_completed",
        "done",
        "error",
    },
)


def format_sse_event(event: ChatStreamEvent) -> str:
    if event.event not in ALLOWED_SSE_EVENT_NAMES:
        raise ValueError("Invalid SSE event name")

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
