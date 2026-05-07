import json

import pytest
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

    assert payload == 'event: sources_found\ndata: {"count":1,"sources":[{"id":"news-1"}]}\n\n'
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


def test_format_sse_event_rejects_event_name_injection() -> None:
    with pytest.raises(ValueError, match="^Invalid SSE event name$"):
        format_sse_event(ChatStreamEvent(event="done\nevent: injected", data={}))


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
