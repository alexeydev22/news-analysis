import importlib.util
import sys
from pathlib import Path


def load_demo_smoke_module():
    root = Path(__file__).resolve().parents[3]
    module_path = root / "tools" / "demo_smoke.py"
    spec = importlib.util.spec_from_file_location("demo_smoke", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["demo_smoke"] = module
    spec.loader.exec_module(module)
    return module


def test_join_url_normalizes_slashes() -> None:
    demo_smoke = load_demo_smoke_module()

    assert demo_smoke.join_url("http://localhost:8000/", "/api/v1/chat/stream") == (
        "http://localhost:8000/api/v1/chat/stream"
    )


def test_parse_sse_events_returns_named_json_events() -> None:
    demo_smoke = load_demo_smoke_module()

    events = demo_smoke.parse_sse_events(
        b'event: chat_started\ndata: {"question":"GDP"}\n\nevent: done\ndata: {"answer":"ok"}\n\n',
    )

    assert events == [
        ("chat_started", {"question": "GDP"}),
        ("done", {"answer": "ok"}),
    ]


def test_parse_sse_events_rejects_malformed_json() -> None:
    demo_smoke = load_demo_smoke_module()

    try:
        demo_smoke.parse_sse_events(b"event: done\ndata: not-json\n\n")
    except demo_smoke.DemoSmokeError as error:
        assert "Malformed SSE JSON" in str(error)
        return

    raise AssertionError("Expected malformed SSE JSON error")


def test_demo_dataset_is_russian_language() -> None:
    root = Path(__file__).resolve().parents[3]
    dataset = (root / "data" / "raw" / "economic_news.csv").read_text(encoding="utf-8")

    assert "ВВП" in dataset
    assert "Центральный банк" in dataset
    assert "GDP grows" not in dataset
