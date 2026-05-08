from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class DemoSmokeError(RuntimeError):
    """Ошибка smoke-проверки демо-сценария."""


@dataclass(frozen=True)
class DemoConfig:
    """Настройки запуска smoke-проверки."""

    api_url: str
    news_url: str
    frontend_url: str | None
    question: str
    limit: int
    timeout_seconds: float


def join_url(base_url: str, path: str) -> str:
    """Собирает URL без двойных слэшей между base и path.

    Args:
        base_url: Базовый URL сервиса.
        path: Путь endpoint.

    Returns:
        Нормализованный абсолютный URL.
    """
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def parse_sse_events(payload: bytes) -> list[tuple[str, dict[str, Any]]]:
    """Парсит именованные SSE-события с JSON payload.

    Args:
        payload: Сырые байты ответа `text/event-stream`.

    Returns:
        Список пар `(event_name, data)`.

    Raises:
        DemoSmokeError: Если событие содержит некорректный JSON.
    """
    text = payload.decode("utf-8")
    events: list[tuple[str, dict[str, Any]]] = []
    for block in text.split("\n\n"):
        event_name: str | None = None
        data_lines: list[str] = []
        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                data_lines.append(line.removeprefix("data:").strip())
        if event_name is None:
            continue
        data_text = "\n".join(data_lines) or "{}"
        try:
            data = json.loads(data_text)
        except json.JSONDecodeError as error:
            raise DemoSmokeError(f"Malformed SSE JSON for event {event_name}") from error
        if not isinstance(data, dict):
            raise DemoSmokeError(f"SSE event {event_name} must contain JSON object data")
        events.append((event_name, data))
    return events


def request_json(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Выполняет HTTP-запрос и возвращает JSON object."""
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    response_body = request_bytes(request, timeout_seconds=timeout_seconds)
    try:
        data = json.loads(response_body.decode("utf-8"))
    except json.JSONDecodeError as error:
        raise DemoSmokeError(f"Response from {url} is not valid JSON") from error
    if not isinstance(data, dict):
        raise DemoSmokeError(f"Response from {url} must be a JSON object")
    return data


def request_bytes(request: Request, *, timeout_seconds: float) -> bytes:
    """Выполняет HTTP-запрос и возвращает тело ответа."""
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return response.read()
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise DemoSmokeError(f"HTTP {error.code} for {request.full_url}: {detail}") from error
    except URLError as error:
        raise DemoSmokeError(f"Cannot reach {request.full_url}: {error.reason}") from error


def check_health(config: DemoConfig) -> None:
    """Проверяет health endpoints gateway и news-service."""
    for service_name, base_url in (
        ("api-gateway", config.api_url),
        ("news-service", config.news_url),
    ):
        response = request_json(
            "GET",
            join_url(base_url, "/health"),
            timeout_seconds=config.timeout_seconds,
        )
        if response != {"service": service_name, "status": "ok"}:
            raise DemoSmokeError(f"Unexpected {service_name} health response: {response}")
        print(f"ok: {service_name} health")


def check_news_preview(config: DemoConfig) -> None:
    """Проверяет чтение demo CSV через news-service."""
    response = request_json(
        "GET",
        join_url(config.news_url, f"/api/v1/news/preview?limit={config.limit}"),
        timeout_seconds=config.timeout_seconds,
    )
    documents = response.get("documents")
    if not isinstance(documents, list) or not documents:
        raise DemoSmokeError("News preview returned no documents")
    print(f"ok: news preview returned {len(documents)} documents")


def check_index_job(config: DemoConfig) -> None:
    """Проверяет постановку фоновой индексации."""
    response = request_json(
        "POST",
        join_url(config.news_url, "/api/v1/news/index/jobs"),
        payload={"limit": config.limit},
        timeout_seconds=config.timeout_seconds,
    )
    if response.get("status") != "queued" or not response.get("job_id"):
        raise DemoSmokeError(f"Unexpected index job response: {response}")
    print(f"ok: queued index job {response['job_id']}")


def check_news_index(config: DemoConfig) -> None:
    """Проверяет синхронную индексацию demo dataset."""
    response = request_json(
        "POST",
        join_url(config.news_url, "/api/v1/news/index"),
        payload={"limit": config.limit},
        timeout_seconds=config.timeout_seconds,
    )
    indexed_count = response.get("indexed_count")
    if not isinstance(indexed_count, int) or indexed_count <= 0:
        raise DemoSmokeError(f"Unexpected index response: {response}")
    print(f"ok: indexed {indexed_count} demo documents")


def check_chat_stream(config: DemoConfig) -> None:
    """Проверяет SSE-сценарий диалога через api-gateway."""
    payload = {
        "question": config.question,
        "analysis_model": "tfidf-logreg",
        "limit": config.limit,
    }
    request = Request(
        join_url(config.api_url, "/api/v1/chat/stream"),
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
        },
    )
    events = parse_sse_events(request_bytes(request, timeout_seconds=config.timeout_seconds))
    event_names = {event_name for event_name, _ in events}
    required_events = {"chat_started", "sources_found", "answer_completed", "done"}
    missing_events = required_events - event_names
    if missing_events:
        raise DemoSmokeError(f"Missing SSE events: {sorted(missing_events)}")
    print(f"ok: chat stream emitted {len(events)} events")


def check_frontend(config: DemoConfig) -> None:
    """Проверяет доступность HTML frontend, если URL задан."""
    if config.frontend_url is None:
        return
    request = Request(config.frontend_url, method="GET")
    body = request_bytes(request, timeout_seconds=config.timeout_seconds).decode(
        "utf-8",
        errors="replace",
    )
    if "<html" not in body.lower():
        raise DemoSmokeError("Frontend response is not HTML")
    print("ok: frontend returned HTML")


def run_smoke(config: DemoConfig) -> None:
    """Запускает полный demo smoke сценарий."""
    check_health(config)
    check_news_preview(config)
    check_news_index(config)
    check_index_job(config)
    check_chat_stream(config)
    check_frontend(config)


def parse_args(argv: list[str]) -> DemoConfig:
    """Парсит CLI-аргументы smoke script."""
    parser = argparse.ArgumentParser(description="Run local E2E demo smoke checks.")
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--news-url", default="http://localhost:8004")
    parser.add_argument("--frontend-url", default="http://localhost:5173")
    parser.add_argument(
        "--question",
        default="Что означает рост ВВП и снижение инфляции для рынка?",
    )
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    parser.add_argument("--skip-frontend", action="store_true")
    args = parser.parse_args(argv)
    return DemoConfig(
        api_url=args.api_url,
        news_url=args.news_url,
        frontend_url=None if args.skip_frontend else args.frontend_url,
        question=args.question,
        limit=args.limit,
        timeout_seconds=args.timeout_seconds,
    )


def main(argv: list[str] | None = None) -> int:
    """Точка входа CLI."""
    try:
        run_smoke(parse_args(sys.argv[1:] if argv is None else argv))
    except DemoSmokeError as error:
        print(f"failed: {error}", file=sys.stderr)
        return 1
    print("ok: demo smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
