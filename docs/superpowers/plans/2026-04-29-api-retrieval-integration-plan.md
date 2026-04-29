# API Retrieval Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose retrieval-service indexing and semantic search through `api-gateway`.

**Architecture:** `api-gateway` remains a thin facade. Presentation routes accept shared retrieval contracts, application use cases delegate through a `RetrievalClient` Protocol, and infrastructure uses Zapros to call `retrieval-service`. Docker Compose wires gateway to the retrieval service with prefixed settings.

**Tech Stack:** Python 3.12, FastAPI, Dishka, Zapros, Pydantic contracts, pytest, Docker Compose.

---

## File Structure

- Modify `apps/api-gateway/src/api_gateway/application/errors.py`: add `RetrievalServiceUnavailableError`.
- Modify `apps/api-gateway/src/api_gateway/application/ports.py`: add `RetrievalClient` Protocol.
- Modify `apps/api-gateway/src/api_gateway/application/use_cases.py`: add `IndexNewsUseCase` and `SearchNewsUseCase`.
- Create `apps/api-gateway/src/api_gateway/infrastructure/retrieval_client.py`: Zapros HTTP client for retrieval-service.
- Modify `apps/api-gateway/src/api_gateway/main/settings.py`: add retrieval service URL and timeout.
- Modify `apps/api-gateway/src/api_gateway/main/container.py`: wire retrieval client and use cases.
- Modify `apps/api-gateway/src/api_gateway/presentation/errors.py`: add retrieval error mapper.
- Modify `apps/api-gateway/src/api_gateway/presentation/router.py`: add `/retrieval/index` and `/retrieval/search`.
- Create `apps/api-gateway/tests/test_retrieval_use_cases.py`: application tests.
- Create `apps/api-gateway/tests/test_retrieval_infrastructure.py`: Zapros client tests.
- Create `apps/api-gateway/tests/test_api_retrieval.py`: route tests.
- Modify `apps/api-gateway/tests/test_container.py`: settings/container tests.
- Modify `deploy/compose.yaml`: add retrieval env and dependency for gateway.

## Task 1: Application Port and Use Cases

**Files:**
- Modify: `apps/api-gateway/src/api_gateway/application/errors.py`
- Modify: `apps/api-gateway/src/api_gateway/application/ports.py`
- Modify: `apps/api-gateway/src/api_gateway/application/use_cases.py`
- Create: `apps/api-gateway/tests/test_retrieval_use_cases.py`

- [ ] **Step 1: Write failing application tests**

Create `apps/api-gateway/tests/test_retrieval_use_cases.py`:

```python
import pytest
from api_gateway.application.errors import RetrievalServiceUnavailableError
from api_gateway.application.use_cases import IndexNewsUseCase, SearchNewsUseCase
from economic_news_contracts.retrieval import (
    IndexNewsRequest,
    IndexNewsResponse,
    NewsDocumentPayload,
    SearchNewsRequest,
    SearchNewsResponse,
    SearchNewsResult,
)


class FakeRetrievalClient:
    def __init__(self) -> None:
        self.index_request: IndexNewsRequest | None = None
        self.search_request: SearchNewsRequest | None = None

    async def index(self, request: IndexNewsRequest) -> IndexNewsResponse:
        self.index_request = request
        return IndexNewsResponse(indexed_count=len(request.documents), collection_name="economic_news")

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
                ),
            ],
        )


class FailingRetrievalClient:
    async def index(self, request: IndexNewsRequest) -> IndexNewsResponse:
        raise RetrievalServiceUnavailableError("retrieval-service is unavailable")

    async def search(self, request: SearchNewsRequest) -> SearchNewsResponse:
        raise RetrievalServiceUnavailableError("retrieval-service is unavailable")


@pytest.mark.asyncio
async def test_index_news_use_case_delegates_to_client() -> None:
    client = FakeRetrievalClient()
    use_case = IndexNewsUseCase(client)
    request = IndexNewsRequest(
        documents=[
            NewsDocumentPayload(
                id="news-1",
                title="GDP grows",
                text="GDP grew by 2 percent.",
                source="demo",
            ),
        ],
    )

    response = await use_case.execute(request)

    assert client.index_request == request
    assert response.indexed_count == 1


@pytest.mark.asyncio
async def test_search_news_use_case_delegates_to_client() -> None:
    client = FakeRetrievalClient()
    use_case = SearchNewsUseCase(client)
    request = SearchNewsRequest(query="GDP", limit=3)

    response = await use_case.execute(request)

    assert client.search_request == request
    assert response.results[0].id == "news-1"


@pytest.mark.asyncio
async def test_retrieval_use_cases_preserve_unavailable_error() -> None:
    index_use_case = IndexNewsUseCase(FailingRetrievalClient())
    search_use_case = SearchNewsUseCase(FailingRetrievalClient())

    with pytest.raises(RetrievalServiceUnavailableError):
        await index_use_case.execute(
            IndexNewsRequest(
                documents=[
                    NewsDocumentPayload(
                        id="news-1",
                        title="GDP grows",
                        text="GDP grew by 2 percent.",
                        source="demo",
                    ),
                ],
            ),
        )

    with pytest.raises(RetrievalServiceUnavailableError):
        await search_use_case.execute(SearchNewsRequest(query="GDP"))
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run pytest apps/api-gateway/tests/test_retrieval_use_cases.py -v
```

Expected: fail because retrieval error/use cases do not exist.

- [ ] **Step 3: Implement application layer**

Update `apps/api-gateway/src/api_gateway/application/errors.py`:

```python
class AnalysisServiceUnavailableError(RuntimeError):
    """Raised when analysis-service cannot process a gateway request."""


class RetrievalServiceUnavailableError(RuntimeError):
    """Raised when retrieval-service cannot process a gateway request."""
```

Update `apps/api-gateway/src/api_gateway/application/ports.py`:

```python
from typing import Protocol

from economic_news_contracts.analysis import AnalyzeNewsRequest, AnalyzeNewsResponse
from economic_news_contracts.retrieval import (
    IndexNewsRequest,
    IndexNewsResponse,
    SearchNewsRequest,
    SearchNewsResponse,
)


class VersionProvider(Protocol):
    def get_version(self) -> str:
        """Return current service version."""


class AnalysisClient(Protocol):
    async def analyze(self, request: AnalyzeNewsRequest) -> AnalyzeNewsResponse:
        """Analyze economic news text through analysis-service."""


class RetrievalClient(Protocol):
    async def index(self, request: IndexNewsRequest) -> IndexNewsResponse:
        """Index economic news documents through retrieval-service."""

    async def search(self, request: SearchNewsRequest) -> SearchNewsResponse:
        """Search economic news documents through retrieval-service."""


class StaticVersionProvider:
    def __init__(self, version: str) -> None:
        self._version = version

    def get_version(self) -> str:
        return self._version
```

Update `apps/api-gateway/src/api_gateway/application/use_cases.py` by keeping `AnalyzeNewsUseCase` and adding:

```python
from economic_news_contracts.retrieval import (
    IndexNewsRequest,
    IndexNewsResponse,
    SearchNewsRequest,
    SearchNewsResponse,
)


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
```

Keep imports sorted by Ruff.

- [ ] **Step 4: Run tests and commit**

Run:

```bash
uv run pytest apps/api-gateway/tests/test_retrieval_use_cases.py -v
uv run ruff check apps/api-gateway/src/api_gateway/application apps/api-gateway/tests/test_retrieval_use_cases.py
uv run ty check apps/api-gateway/src/api_gateway/application apps/api-gateway/tests/test_retrieval_use_cases.py
```

Expected: pass.

Commit:

```bash
git add apps/api-gateway/src/api_gateway/application apps/api-gateway/tests/test_retrieval_use_cases.py
git commit -m "feat: добавить сценарии retrieval в api gateway"
```

## Task 2: Zapros Retrieval Client

**Files:**
- Create: `apps/api-gateway/src/api_gateway/infrastructure/retrieval_client.py`
- Create: `apps/api-gateway/tests/test_retrieval_infrastructure.py`

- [ ] **Step 1: Write failing infrastructure tests**

Create `apps/api-gateway/tests/test_retrieval_infrastructure.py`:

```python
import pytest
from api_gateway.application.errors import RetrievalServiceUnavailableError
from api_gateway.infrastructure.retrieval_client import ZaprosRetrievalClient
from economic_news_contracts.retrieval import IndexNewsRequest, NewsDocumentPayload, SearchNewsRequest
from zapros import Response


class FakeZaprosClient:
    def __init__(self, response: Response) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def post(self, url: str, json: dict[str, object]) -> Response:
        self.calls.append((url, json))
        return self.response


class RaisingZaprosClient:
    async def post(self, url: str, json: dict[str, object]) -> Response:
        raise OSError("connection refused")


def index_request() -> IndexNewsRequest:
    return IndexNewsRequest(
        documents=[
            NewsDocumentPayload(
                id="news-1",
                title="GDP grows",
                text="GDP grew by 2 percent.",
                source="demo",
            ),
        ],
    )


@pytest.mark.asyncio
async def test_retrieval_client_indexes_documents() -> None:
    transport = FakeZaprosClient(
        Response(200, json={"indexed_count": 1, "collection_name": "economic_news"}),
    )
    client = ZaprosRetrievalClient(
        base_url="http://retrieval-service:8000/",
        timeout_seconds=3.0,
        client=transport,
    )

    response = await client.index(index_request())

    assert response.indexed_count == 1
    assert transport.calls[0] == (
        "http://retrieval-service:8000/api/v1/index",
        {
            "documents": [
                {
                    "id": "news-1",
                    "title": "GDP grows",
                    "text": "GDP grew by 2 percent.",
                    "source": "demo",
                    "published_at": None,
                    "metadata": {},
                },
            ],
        },
    )


@pytest.mark.asyncio
async def test_retrieval_client_searches_documents() -> None:
    transport = FakeZaprosClient(
        Response(
            200,
            json={
                "results": [
                    {
                        "id": "news-1",
                        "score": -0.1,
                        "title": "GDP grows",
                        "text": "GDP grew by 2 percent.",
                        "source": "demo",
                        "published_at": None,
                        "metadata": {},
                    },
                ],
            },
        ),
    )
    client = ZaprosRetrievalClient(
        base_url="http://retrieval-service:8000",
        timeout_seconds=3.0,
        client=transport,
    )

    response = await client.search(SearchNewsRequest(query="GDP", limit=3))

    assert response.results[0].score == -0.1
    assert transport.calls[0] == (
        "http://retrieval-service:8000/api/v1/search",
        {"query": "GDP", "limit": 3, "source": None},
    )


@pytest.mark.asyncio
async def test_retrieval_client_maps_5xx_to_unavailable_error() -> None:
    client = ZaprosRetrievalClient(
        base_url="http://retrieval-service:8000",
        timeout_seconds=3.0,
        client=FakeZaprosClient(Response(503, json={"detail": "down"})),
    )

    with pytest.raises(RetrievalServiceUnavailableError):
        await client.search(SearchNewsRequest(query="GDP"))


@pytest.mark.asyncio
async def test_retrieval_client_maps_transport_error() -> None:
    client = ZaprosRetrievalClient(
        base_url="http://retrieval-service:8000",
        timeout_seconds=3.0,
        client=RaisingZaprosClient(),
    )

    with pytest.raises(RetrievalServiceUnavailableError):
        await client.index(index_request())
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run pytest apps/api-gateway/tests/test_retrieval_infrastructure.py -v
```

Expected: fail because `ZaprosRetrievalClient` does not exist.

- [ ] **Step 3: Implement retrieval client**

Create `apps/api-gateway/src/api_gateway/infrastructure/retrieval_client.py`:

```python
from collections.abc import Callable
from typing import Any

from api_gateway.application.errors import RetrievalServiceUnavailableError
from economic_news_contracts.retrieval import (
    IndexNewsRequest,
    IndexNewsResponse,
    SearchNewsRequest,
    SearchNewsResponse,
)
from zapros import AsyncClient, AsyncStdNetworkHandler


def _make_zapros_client(timeout_seconds: float) -> AsyncClient:
    return AsyncClient(handler=AsyncStdNetworkHandler(total_timeout=timeout_seconds))


class ZaprosRetrievalClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        client: Any | None = None,
        client_factory: Callable[[float], Any] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client = client
        self._client_factory = client_factory or _make_zapros_client

    async def index(self, request: IndexNewsRequest) -> IndexNewsResponse:
        response = await self._post("/api/v1/index", request.model_dump(mode="json"))
        if response.status >= 500:
            raise RetrievalServiceUnavailableError("retrieval-service is unavailable")
        return IndexNewsResponse.model_validate(response.json)

    async def search(self, request: SearchNewsRequest) -> SearchNewsResponse:
        response = await self._post("/api/v1/search", request.model_dump(mode="json"))
        if response.status >= 500:
            raise RetrievalServiceUnavailableError("retrieval-service is unavailable")
        return SearchNewsResponse.model_validate(response.json)

    async def _post(self, path: str, payload: dict[str, Any]) -> Any:
        url = f"{self._base_url}{path}"
        try:
            if self._client is not None:
                return await self._client.post(url, json=payload)
            async with self._client_factory(self._timeout_seconds) as client:
                return await client.post(url, json=payload)
        except Exception as error:
            raise RetrievalServiceUnavailableError("retrieval-service is unavailable") from error
```

- [ ] **Step 4: Run tests and commit**

Run:

```bash
uv run pytest apps/api-gateway/tests/test_retrieval_infrastructure.py -v
uv run ruff check apps/api-gateway/src/api_gateway/infrastructure/retrieval_client.py apps/api-gateway/tests/test_retrieval_infrastructure.py
uv run ty check apps/api-gateway/src/api_gateway/infrastructure/retrieval_client.py apps/api-gateway/tests/test_retrieval_infrastructure.py
```

Expected: pass.

Commit:

```bash
git add apps/api-gateway/src/api_gateway/infrastructure/retrieval_client.py apps/api-gateway/tests/test_retrieval_infrastructure.py
git commit -m "feat: добавить http клиент retrieval service"
```

## Task 3: API Routes, DI, and Settings

**Files:**
- Modify: `apps/api-gateway/src/api_gateway/main/settings.py`
- Modify: `apps/api-gateway/src/api_gateway/main/container.py`
- Modify: `apps/api-gateway/src/api_gateway/presentation/errors.py`
- Modify: `apps/api-gateway/src/api_gateway/presentation/router.py`
- Create: `apps/api-gateway/tests/test_api_retrieval.py`
- Modify: `apps/api-gateway/tests/test_container.py`

- [ ] **Step 1: Write failing route tests**

Create `apps/api-gateway/tests/test_api_retrieval.py`:

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from api_gateway.application.errors import RetrievalServiceUnavailableError
from api_gateway.application.use_cases import IndexNewsUseCase, SearchNewsUseCase
from api_gateway.presentation.router import router
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider, setup_dishka
from economic_news_contracts.retrieval import (
    IndexNewsRequest,
    IndexNewsResponse,
    SearchNewsRequest,
    SearchNewsResponse,
    SearchNewsResult,
)
from economic_news_framework.apps import create_service_app
from fastapi.testclient import TestClient


class SuccessfulRetrievalClient:
    async def index(self, request: IndexNewsRequest) -> IndexNewsResponse:
        return IndexNewsResponse(indexed_count=len(request.documents), collection_name="economic_news")

    async def search(self, request: SearchNewsRequest) -> SearchNewsResponse:
        return SearchNewsResponse(
            results=[
                SearchNewsResult(
                    id="news-1",
                    score=0.6,
                    title="GDP grows",
                    text="GDP grew by 2 percent.",
                    source="demo",
                ),
            ],
        )


class UnavailableRetrievalClient:
    async def index(self, request: IndexNewsRequest) -> IndexNewsResponse:
        raise RetrievalServiceUnavailableError("retrieval-service is unavailable")

    async def search(self, request: SearchNewsRequest) -> SearchNewsResponse:
        raise RetrievalServiceUnavailableError("retrieval-service is unavailable")


class TestProvider(Provider):
    def __init__(self, retrieval_client: object) -> None:
        super().__init__()
        self._retrieval_client = retrieval_client

    @provide(scope=Scope.APP)
    def index_news_use_case(self) -> IndexNewsUseCase:
        return IndexNewsUseCase(self._retrieval_client)

    @provide(scope=Scope.APP)
    def search_news_use_case(self) -> SearchNewsUseCase:
        return SearchNewsUseCase(self._retrieval_client)


def make_client(retrieval_client: object) -> TestClient:
    app = create_service_app(service_name="api-gateway", routers=(router,), log_level="INFO")
    container = make_async_container(TestProvider(retrieval_client), FastapiProvider())
    setup_dishka(container=container, app=app)

    @asynccontextmanager
    async def close_container(_: object) -> AsyncIterator[None]:
        yield
        await container.close()

    app.router.lifespan_context = close_container
    return TestClient(app)


def test_retrieval_index_endpoint_returns_index_response() -> None:
    with make_client(SuccessfulRetrievalClient()) as client:
        response = client.post(
            "/api/v1/retrieval/index",
            json={
                "documents": [
                    {
                        "id": "news-1",
                        "title": "GDP grows",
                        "text": "GDP grew by 2 percent.",
                        "source": "demo",
                    },
                ],
            },
        )

    assert response.status_code == 200
    assert response.json() == {"indexed_count": 1, "collection_name": "economic_news"}


def test_retrieval_search_endpoint_returns_search_response() -> None:
    with make_client(SuccessfulRetrievalClient()) as client:
        response = client.post("/api/v1/retrieval/search", json={"query": "GDP"})

    assert response.status_code == 200
    assert response.json()["results"][0]["id"] == "news-1"


def test_retrieval_endpoint_maps_unavailable_error_to_503() -> None:
    with make_client(UnavailableRetrievalClient()) as client:
        response = client.post("/api/v1/retrieval/search", json={"query": "GDP"})

    assert response.status_code == 503
    assert response.json() == {"detail": "retrieval-service is unavailable"}
```

- [ ] **Step 2: Add failing settings/container tests**

Append to `apps/api-gateway/tests/test_container.py`:

```python
from api_gateway.application.use_cases import IndexNewsUseCase, SearchNewsUseCase


def test_api_gateway_settings_read_prefixed_retrieval_service_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_GATEWAY_RETRIEVAL_SERVICE_URL", "http://localhost:9002")
    monkeypatch.setenv("API_GATEWAY_RETRIEVAL_SERVICE_TIMEOUT_SECONDS", "4.5")

    settings = ApiGatewaySettings()

    assert str(settings.retrieval_service_url) == "http://localhost:9002/"
    assert settings.retrieval_service_timeout_seconds == 4.5


@pytest.mark.asyncio
async def test_container_resolves_retrieval_use_cases() -> None:
    container: AsyncContainer = create_container()

    try:
        index_use_case = await container.get(IndexNewsUseCase)
        search_use_case = await container.get(SearchNewsUseCase)
    finally:
        await container.close()

    assert isinstance(index_use_case, IndexNewsUseCase)
    assert isinstance(search_use_case, SearchNewsUseCase)
```

Keep imports sorted and avoid duplicate imports.

- [ ] **Step 3: Run tests and verify failure**

Run:

```bash
uv run pytest apps/api-gateway/tests/test_api_retrieval.py apps/api-gateway/tests/test_container.py -v
```

Expected: fail because routes/settings/DI are missing.

- [ ] **Step 4: Implement settings and DI**

Update `apps/api-gateway/src/api_gateway/main/settings.py`:

```python
retrieval_service_url: AnyHttpUrl = AnyHttpUrl("http://retrieval-service:8000")
retrieval_service_timeout_seconds: float = 3.0
```

Update `apps/api-gateway/src/api_gateway/main/container.py`:

```python
from api_gateway.application.ports import AnalysisClient, RetrievalClient, StaticVersionProvider, VersionProvider
from api_gateway.application.use_cases import AnalyzeNewsUseCase, IndexNewsUseCase, SearchNewsUseCase
from api_gateway.infrastructure.retrieval_client import ZaprosRetrievalClient
```

Add providers:

```python
@provide(scope=Scope.APP)
def retrieval_client(self, settings: ApiGatewaySettings) -> RetrievalClient:
    return ZaprosRetrievalClient(
        base_url=str(settings.retrieval_service_url),
        timeout_seconds=settings.retrieval_service_timeout_seconds,
    )


@provide(scope=Scope.APP)
def index_news_use_case(self, retrieval_client: RetrievalClient) -> IndexNewsUseCase:
    return IndexNewsUseCase(retrieval_client)


@provide(scope=Scope.APP)
def search_news_use_case(self, retrieval_client: RetrievalClient) -> SearchNewsUseCase:
    return SearchNewsUseCase(retrieval_client)
```

- [ ] **Step 5: Implement presentation mapping**

Update `apps/api-gateway/src/api_gateway/presentation/errors.py`:

```python
from api_gateway.application.errors import (
    AnalysisServiceUnavailableError,
    RetrievalServiceUnavailableError,
)


def map_retrieval_error(error: RetrievalServiceUnavailableError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(error),
    )
```

Update `apps/api-gateway/src/api_gateway/presentation/router.py` with imports and routes:

```python
@router.post("/retrieval/index")
@inject
async def retrieval_index(
    request: IndexNewsRequest,
    use_case: FromDishka[IndexNewsUseCase],
) -> IndexNewsResponse:
    try:
        return await use_case.execute(request)
    except RetrievalServiceUnavailableError as error:
        raise map_retrieval_error(error) from error


@router.post("/retrieval/search")
@inject
async def retrieval_search(
    request: SearchNewsRequest,
    use_case: FromDishka[SearchNewsUseCase],
) -> SearchNewsResponse:
    try:
        return await use_case.execute(request)
    except RetrievalServiceUnavailableError as error:
        raise map_retrieval_error(error) from error
```

- [ ] **Step 6: Run tests and commit**

Run:

```bash
uv run pytest apps/api-gateway/tests/test_api_retrieval.py apps/api-gateway/tests/test_container.py apps/api-gateway/tests/test_health.py -v
uv run ruff check apps/api-gateway/src/api_gateway/main apps/api-gateway/src/api_gateway/presentation apps/api-gateway/tests/test_api_retrieval.py apps/api-gateway/tests/test_container.py
uv run ty check apps/api-gateway/src/api_gateway/main apps/api-gateway/src/api_gateway/presentation apps/api-gateway/tests/test_api_retrieval.py apps/api-gateway/tests/test_container.py
```

Expected: pass.

Commit:

```bash
git add apps/api-gateway/src/api_gateway/main apps/api-gateway/src/api_gateway/presentation apps/api-gateway/tests/test_api_retrieval.py apps/api-gateway/tests/test_container.py
git commit -m "feat: добавить retrieval endpoints в api gateway"
```

## Task 4: Compose Wiring and Final Verification

**Files:**
- Modify: `deploy/compose.yaml`

- [ ] **Step 1: Update compose**

Update `api-gateway` service:

```yaml
    environment:
      API_GATEWAY_ANALYSIS_SERVICE_URL: "http://analysis-service:8000"
      API_GATEWAY_RETRIEVAL_SERVICE_URL: "http://retrieval-service:8000"
```

Add dependency:

```yaml
    depends_on:
      - postgres
      - redis
      - qdrant
      - analysis-service
      - retrieval-service
```

- [ ] **Step 2: Run full verification**

Run:

```bash
uv run ruff check apps packages research
uv run ty check apps packages research
uv run pytest packages apps research/tests -v -W error
docker compose -f deploy/compose.yaml config
docker compose -f deploy/compose.yaml build api-gateway
```

Expected: all commands pass.

- [ ] **Step 3: Commit**

Commit:

```bash
git add deploy/compose.yaml
git commit -m "chore: подключить retrieval service к gateway"
```

## Completion

- Push branch:

```bash
git push -u origin feature/api-retrieval-integration
```

- Open PR to `dev`:

```bash
gh pr create --base dev --head feature/api-retrieval-integration --title "feat: подключить retrieval service к api gateway" --body "Добавляет retrieval endpoints в api-gateway и проксирует index/search запросы в retrieval-service через typed application port и Zapros HTTP client."
```
