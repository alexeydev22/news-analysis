# API Analysis Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `POST /api/v1/analyze` to `api-gateway` and route it to `analysis-service` through a typed application port.

**Architecture:** `api-gateway` stays thin: presentation validates shared contracts, application owns the use case and Protocol, infrastructure owns the Zapros HTTP call. Dishka wires the use case and client; Docker Compose points gateway to `analysis-service`.

**Tech Stack:** Python 3.12, FastAPI, Dishka, Zapros, Pydantic contracts, pytest, TestClient, Docker Compose.

---

## File Structure

- Modify `apps/api-gateway/pyproject.toml`: add runtime Zapros dependency.
- Modify `apps/api-gateway/src/api_gateway/application/ports.py`: add `AnalysisClient` Protocol.
- Create `apps/api-gateway/src/api_gateway/application/errors.py`: define service-unavailable application error.
- Create `apps/api-gateway/src/api_gateway/application/use_cases.py`: define `AnalyzeNewsUseCase`.
- Create `apps/api-gateway/src/api_gateway/infrastructure/analysis_client.py`: implement Zapros-backed HTTP client.
- Modify `apps/api-gateway/src/api_gateway/main/settings.py`: add analysis service URL and timeout settings.
- Modify `apps/api-gateway/src/api_gateway/main/container.py`: wire settings, client, and use case through Dishka.
- Modify `apps/api-gateway/src/api_gateway/presentation/router.py`: add `POST /api/v1/analyze`.
- Create `apps/api-gateway/src/api_gateway/presentation/errors.py`: map application errors to FastAPI HTTP responses.
- Modify `apps/api-gateway/tests/test_health.py`: keep existing health/version coverage working.
- Create `apps/api-gateway/tests/test_use_cases.py`: test application use case with fake client.
- Create `apps/api-gateway/tests/test_api_analysis.py`: test gateway endpoint success and unavailable service.
- Create `apps/api-gateway/tests/test_infrastructure.py`: test Zapros client behavior with a fake client object.
- Create `apps/api-gateway/tests/test_container.py`: test settings and DI can resolve the use case.
- Modify `deploy/compose.yaml`: add gateway env and `analysis-service` dependency.
- Modify `uv.lock`: update with Zapros dependency.

## Task 1: Application Port and Use Case

**Files:**
- Modify: `apps/api-gateway/src/api_gateway/application/ports.py`
- Create: `apps/api-gateway/src/api_gateway/application/errors.py`
- Create: `apps/api-gateway/src/api_gateway/application/use_cases.py`
- Create: `apps/api-gateway/tests/test_use_cases.py`

- [ ] **Step 1: Write failing use case tests**

Create `apps/api-gateway/tests/test_use_cases.py`:

```python
import pytest
from economic_news_contracts.analysis import (
    AnalysisModelName,
    AnalyzeNewsRequest,
    AnalyzeNewsResponse,
    ImpactLabel,
)

from api_gateway.application.errors import AnalysisServiceUnavailableError
from api_gateway.application.use_cases import AnalyzeNewsUseCase


class FakeAnalysisClient:
    def __init__(self) -> None:
        self.request: AnalyzeNewsRequest | None = None

    async def analyze(self, request: AnalyzeNewsRequest) -> AnalyzeNewsResponse:
        self.request = request
        return AnalyzeNewsResponse(
            model_name=request.analysis_model,
            impact=ImpactLabel.POSITIVE,
            confidence=0.82,
            explanation="Новость может поддержать рынок.",
            metadata={"source": "fake"},
        )


class FailingAnalysisClient:
    async def analyze(self, request: AnalyzeNewsRequest) -> AnalyzeNewsResponse:
        raise AnalysisServiceUnavailableError("analysis-service is unavailable")


@pytest.mark.asyncio
async def test_analyze_news_use_case_returns_client_response() -> None:
    client = FakeAnalysisClient()
    use_case = AnalyzeNewsUseCase(client)
    request = AnalyzeNewsRequest(
        text="ЦБ снизил ключевую ставку",
        analysis_model=AnalysisModelName.TFIDF_LOGREG,
    )

    response = await use_case.execute(request)

    assert client.request == request
    assert response.impact == ImpactLabel.POSITIVE
    assert response.confidence == 0.82


@pytest.mark.asyncio
async def test_analyze_news_use_case_preserves_unavailable_error() -> None:
    use_case = AnalyzeNewsUseCase(FailingAnalysisClient())
    request = AnalyzeNewsRequest(text="Биржевой индекс снизился")

    with pytest.raises(AnalysisServiceUnavailableError):
        await use_case.execute(request)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run pytest apps/api-gateway/tests/test_use_cases.py -v
```

Expected: fail because `api_gateway.application.errors` or `AnalyzeNewsUseCase` does not exist.

- [ ] **Step 3: Implement application error**

Create `apps/api-gateway/src/api_gateway/application/errors.py`:

```python
class AnalysisServiceUnavailableError(RuntimeError):
    """Raised when analysis-service cannot process a gateway request."""
```

- [ ] **Step 4: Implement application port**

Update `apps/api-gateway/src/api_gateway/application/ports.py`:

```python
from typing import Protocol

from economic_news_contracts.analysis import AnalyzeNewsRequest, AnalyzeNewsResponse


class VersionProvider(Protocol):
    def get_version(self) -> str:
        """Return current service version."""


class AnalysisClient(Protocol):
    async def analyze(self, request: AnalyzeNewsRequest) -> AnalyzeNewsResponse:
        """Analyze economic news text through analysis-service."""


class StaticVersionProvider:
    def __init__(self, version: str) -> None:
        self._version = version

    def get_version(self) -> str:
        return self._version
```

- [ ] **Step 5: Implement use case**

Create `apps/api-gateway/src/api_gateway/application/use_cases.py`:

```python
from economic_news_contracts.analysis import AnalyzeNewsRequest, AnalyzeNewsResponse

from api_gateway.application.ports import AnalysisClient


class AnalyzeNewsUseCase:
    def __init__(self, analysis_client: AnalysisClient) -> None:
        self._analysis_client = analysis_client

    async def execute(self, request: AnalyzeNewsRequest) -> AnalyzeNewsResponse:
        return await self._analysis_client.analyze(request)
```

- [ ] **Step 6: Run use case tests and commit**

Run:

```bash
uv run pytest apps/api-gateway/tests/test_use_cases.py -v
```

Expected: pass.

Commit:

```bash
git add apps/api-gateway/src/api_gateway/application apps/api-gateway/tests/test_use_cases.py
git commit -m "feat: добавить сценарий анализа в api gateway"
```

## Task 2: Zapros Infrastructure Client

**Files:**
- Modify: `apps/api-gateway/pyproject.toml`
- Create: `apps/api-gateway/src/api_gateway/infrastructure/analysis_client.py`
- Create: `apps/api-gateway/tests/test_infrastructure.py`
- Modify: `uv.lock`

- [ ] **Step 1: Add dependency**

Update `apps/api-gateway/pyproject.toml` dependencies:

```toml
dependencies = [
  "economic-news-framework",
  "economic-news-contracts",
  "fastapi>=0.115",
  "granian>=1.7",
  "dishka>=1.4",
  "pydantic-settings>=2.6",
  "structlog>=24.4",
  "zapros>=0.3.0",
]
```

- [ ] **Step 2: Update lockfile**

Run:

```bash
uv lock
```

Expected: `uv.lock` includes `zapros`.

- [ ] **Step 3: Write failing infrastructure tests**

Create `apps/api-gateway/tests/test_infrastructure.py`:

```python
import pytest
from economic_news_contracts.analysis import (
    AnalysisModelName,
    AnalyzeNewsRequest,
    ImpactLabel,
)

from api_gateway.application.errors import AnalysisServiceUnavailableError
from api_gateway.infrastructure.analysis_client import ZaprosAnalysisClient


class FakeResponse:
    def __init__(self, status: int, payload: dict[str, object]) -> None:
        self.status = status
        self._payload = payload

    def json(self) -> dict[str, object]:
        return self._payload


class FakeZaprosClient:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.url: str | None = None
        self.json_payload: dict[str, object] | None = None

    async def post(self, url: str, json: dict[str, object]) -> FakeResponse:
        self.url = url
        self.json_payload = json
        return self.response


class RaisingZaprosClient:
    async def post(self, url: str, json: dict[str, object]) -> FakeResponse:
        raise OSError("connection refused")


@pytest.mark.asyncio
async def test_zapros_analysis_client_sends_contract_payload() -> None:
    transport = FakeZaprosClient(
        FakeResponse(
            status=200,
            payload={
                "model_name": "tfidf-logreg",
                "impact": "positive",
                "confidence": 0.91,
                "explanation": "Позитивное влияние.",
                "metadata": {"source": "static"},
            },
        ),
    )
    client = ZaprosAnalysisClient(
        base_url="http://analysis-service:8000",
        timeout_seconds=3.0,
        client=transport,
    )
    request = AnalyzeNewsRequest(
        text="Экспорт вырос",
        analysis_model=AnalysisModelName.TFIDF_LOGREG,
    )

    response = await client.analyze(request)

    assert transport.url == "http://analysis-service:8000/api/v1/analyze"
    assert transport.json_payload == {
        "text": "Экспорт вырос",
        "analysis_model": "tfidf-logreg",
    }
    assert response.impact == ImpactLabel.POSITIVE
    assert response.confidence == 0.91


@pytest.mark.asyncio
async def test_zapros_analysis_client_maps_5xx_to_unavailable_error() -> None:
    client = ZaprosAnalysisClient(
        base_url="http://analysis-service:8000/",
        timeout_seconds=3.0,
        client=FakeZaprosClient(FakeResponse(status=503, payload={"detail": "down"})),
    )

    with pytest.raises(AnalysisServiceUnavailableError):
        await client.analyze(AnalyzeNewsRequest(text="Рынок снизился"))


@pytest.mark.asyncio
async def test_zapros_analysis_client_maps_transport_error() -> None:
    client = ZaprosAnalysisClient(
        base_url="http://analysis-service:8000",
        timeout_seconds=3.0,
        client=RaisingZaprosClient(),
    )

    with pytest.raises(AnalysisServiceUnavailableError):
        await client.analyze(AnalyzeNewsRequest(text="Рынок снизился"))
```

- [ ] **Step 4: Run tests and verify failure**

Run:

```bash
uv run pytest apps/api-gateway/tests/test_infrastructure.py -v
```

Expected: fail because `ZaprosAnalysisClient` does not exist.

- [ ] **Step 5: Implement infrastructure client**

Create `apps/api-gateway/src/api_gateway/infrastructure/analysis_client.py`:

```python
from typing import Any

from economic_news_contracts.analysis import AnalyzeNewsRequest, AnalyzeNewsResponse
from zapros import AsyncClient

from api_gateway.application.errors import AnalysisServiceUnavailableError


class ZaprosAnalysisClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        client: Any | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client = client

    async def analyze(self, request: AnalyzeNewsRequest) -> AnalyzeNewsResponse:
        payload = request.model_dump(mode="json")
        response = await self._post(payload)
        if response.status >= 500:
            raise AnalysisServiceUnavailableError("analysis-service is unavailable")
        return AnalyzeNewsResponse.model_validate(response.json())

    async def _post(self, payload: dict[str, Any]) -> Any:
        url = f"{self._base_url}/api/v1/analyze"
        try:
            if self._client is not None:
                return await self._client.post(url, json=payload)
            async with AsyncClient(timeout=self._timeout_seconds) as client:
                return await client.post(url, json=payload)
        except Exception as error:
            raise AnalysisServiceUnavailableError(
                "analysis-service is unavailable",
            ) from error
```

If `AsyncClient(timeout=...)` is not accepted by installed Zapros, keep timeout in settings but construct `AsyncClient()` and cover timeout behavior in a later transport-level task. The public gateway behavior remains the same.

- [ ] **Step 6: Run infrastructure tests and commit**

Run:

```bash
uv run pytest apps/api-gateway/tests/test_infrastructure.py -v
```

Expected: pass.

Commit:

```bash
git add apps/api-gateway/pyproject.toml uv.lock apps/api-gateway/src/api_gateway/infrastructure/analysis_client.py apps/api-gateway/tests/test_infrastructure.py
git commit -m "feat: добавить http клиент analysis service"
```

## Task 3: Presentation Endpoint and DI

**Files:**
- Modify: `apps/api-gateway/src/api_gateway/main/settings.py`
- Modify: `apps/api-gateway/src/api_gateway/main/container.py`
- Modify: `apps/api-gateway/src/api_gateway/presentation/router.py`
- Create: `apps/api-gateway/src/api_gateway/presentation/errors.py`
- Create: `apps/api-gateway/tests/test_api_analysis.py`
- Create: `apps/api-gateway/tests/test_container.py`

- [ ] **Step 1: Write failing API tests**

Create `apps/api-gateway/tests/test_api_analysis.py`:

```python
from collections.abc import AsyncIterator

from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider, setup_dishka
from economic_news_contracts.analysis import AnalyzeNewsRequest, AnalyzeNewsResponse, ImpactLabel
from economic_news_framework.apps import create_service_app
from fastapi.testclient import TestClient

from api_gateway.application.errors import AnalysisServiceUnavailableError
from api_gateway.application.use_cases import AnalyzeNewsUseCase
from api_gateway.presentation.router import router


class SuccessfulClient:
    async def analyze(self, request: AnalyzeNewsRequest) -> AnalyzeNewsResponse:
        return AnalyzeNewsResponse(
            model_name=request.analysis_model,
            impact=ImpactLabel.NEUTRAL,
            confidence=0.7,
            explanation="Существенного влияния не ожидается.",
            metadata={"source": "test"},
        )


class UnavailableClient:
    async def analyze(self, request: AnalyzeNewsRequest) -> AnalyzeNewsResponse:
        raise AnalysisServiceUnavailableError("analysis-service is unavailable")


class TestProvider(Provider):
    def __init__(self, analysis_client: object) -> None:
        super().__init__()
        self._analysis_client = analysis_client

    @provide(scope=Scope.APP)
    def analyze_news_use_case(self) -> AnalyzeNewsUseCase:
        return AnalyzeNewsUseCase(self._analysis_client)


def make_client(analysis_client: object) -> TestClient:
    app = create_service_app(
        service_name="api-gateway",
        routers=(router,),
        log_level="INFO",
    )
    container = make_async_container(TestProvider(analysis_client), FastapiProvider())
    setup_dishka(container=container, app=app)

    async def close_container() -> AsyncIterator[None]:
        yield
        await container.close()

    app.router.lifespan_context = close_container
    return TestClient(app)


def test_analyze_endpoint_returns_analysis_response() -> None:
    client = make_client(SuccessfulClient())

    response = client.post(
        "/api/v1/analyze",
        json={"text": "Инфляция замедлилась", "analysis_model": "tfidf-logreg"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "model_name": "tfidf-logreg",
        "impact": "neutral",
        "confidence": 0.7,
        "explanation": "Существенного влияния не ожидается.",
        "metadata": {"source": "test"},
    }


def test_analyze_endpoint_maps_unavailable_error_to_503() -> None:
    client = make_client(UnavailableClient())

    response = client.post("/api/v1/analyze", json={"text": "Индекс снизился"})

    assert response.status_code == 503
    assert response.json() == {"detail": "analysis-service is unavailable"}
```

- [ ] **Step 2: Write failing container test**

Create `apps/api-gateway/tests/test_container.py`:

```python
import pytest
from dishka import AsyncContainer

from api_gateway.application.use_cases import AnalyzeNewsUseCase
from api_gateway.main.container import create_container
from api_gateway.main.settings import ApiGatewaySettings


@pytest.mark.asyncio
async def test_container_resolves_analyze_news_use_case() -> None:
    container: AsyncContainer = create_container()

    try:
        use_case = await container.get(AnalyzeNewsUseCase)
    finally:
        await container.close()

    assert isinstance(use_case, AnalyzeNewsUseCase)


def test_api_gateway_settings_include_analysis_service_defaults() -> None:
    settings = ApiGatewaySettings()

    assert str(settings.analysis_service_url) == "http://analysis-service:8000/"
    assert settings.analysis_service_timeout_seconds == 3.0
```

- [ ] **Step 3: Run tests and verify failure**

Run:

```bash
uv run pytest apps/api-gateway/tests/test_api_analysis.py apps/api-gateway/tests/test_container.py -v
```

Expected: fail because route and DI providers are not implemented.

- [ ] **Step 4: Add settings**

Update `apps/api-gateway/src/api_gateway/main/settings.py`:

```python
from pydantic import AnyHttpUrl

from economic_news_framework.settings import BaseServiceSettings


class ApiGatewaySettings(BaseServiceSettings):
    service_name: str = "api-gateway"
    version: str = "0.1.0"
    analysis_service_url: AnyHttpUrl = "http://analysis-service:8000"
    analysis_service_timeout_seconds: float = 3.0
```

- [ ] **Step 5: Wire container**

Update `apps/api-gateway/src/api_gateway/main/container.py`:

```python
from api_gateway.application.ports import AnalysisClient, StaticVersionProvider, VersionProvider
from api_gateway.application.use_cases import AnalyzeNewsUseCase
from api_gateway.infrastructure.analysis_client import ZaprosAnalysisClient
from api_gateway.main.settings import ApiGatewaySettings
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider


class ApiGatewayProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> ApiGatewaySettings:
        return ApiGatewaySettings()

    @provide(scope=Scope.APP)
    def version_provider(self, settings: ApiGatewaySettings) -> VersionProvider:
        return StaticVersionProvider(settings.version)

    @provide(scope=Scope.APP)
    def analysis_client(self, settings: ApiGatewaySettings) -> AnalysisClient:
        return ZaprosAnalysisClient(
            base_url=str(settings.analysis_service_url),
            timeout_seconds=settings.analysis_service_timeout_seconds,
        )

    @provide(scope=Scope.APP)
    def analyze_news_use_case(self, analysis_client: AnalysisClient) -> AnalyzeNewsUseCase:
        return AnalyzeNewsUseCase(analysis_client)


def create_container():
    return make_async_container(ApiGatewayProvider(), FastapiProvider())
```

- [ ] **Step 6: Add presentation error handler**

Create `apps/api-gateway/src/api_gateway/presentation/errors.py`:

```python
from fastapi import HTTPException, status

from api_gateway.application.errors import AnalysisServiceUnavailableError


def map_analysis_error(error: AnalysisServiceUnavailableError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(error),
    )
```

- [ ] **Step 7: Add route**

Update `apps/api-gateway/src/api_gateway/presentation/router.py`:

```python
from api_gateway.application.errors import AnalysisServiceUnavailableError
from api_gateway.application.ports import VersionProvider
from api_gateway.application.use_cases import AnalyzeNewsUseCase
from api_gateway.presentation.errors import map_analysis_error
from dishka.integrations.fastapi import FromDishka, inject
from economic_news_contracts.analysis import AnalyzeNewsRequest, AnalyzeNewsResponse
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")


@router.get("/version")
@inject
async def version(version_provider: FromDishka[VersionProvider]) -> dict[str, str]:
    return {"service": "api-gateway", "version": version_provider.get_version()}


@router.post("/analyze")
@inject
async def analyze(
    request: AnalyzeNewsRequest,
    use_case: FromDishka[AnalyzeNewsUseCase],
) -> AnalyzeNewsResponse:
    try:
        return await use_case.execute(request)
    except AnalysisServiceUnavailableError as error:
        raise map_analysis_error(error) from error
```

- [ ] **Step 8: Run API and container tests and commit**

Run:

```bash
uv run pytest apps/api-gateway/tests/test_api_analysis.py apps/api-gateway/tests/test_container.py apps/api-gateway/tests/test_health.py -v
```

Expected: pass.

Commit:

```bash
git add apps/api-gateway/src/api_gateway/main apps/api-gateway/src/api_gateway/presentation apps/api-gateway/tests/test_api_analysis.py apps/api-gateway/tests/test_container.py apps/api-gateway/tests/test_health.py
git commit -m "feat: добавить endpoint анализа в api gateway"
```

## Task 4: Compose Wiring and Full Verification

**Files:**
- Modify: `deploy/compose.yaml`
- Modify if needed: `README.md`

- [ ] **Step 1: Update compose gateway dependency**

Update `deploy/compose.yaml` `api-gateway` service:

```yaml
  api-gateway:
    build:
      context: ..
      dockerfile: deploy/docker/api-gateway.Dockerfile
    env_file:
      - ../.env.example
    environment:
      API_GATEWAY_ANALYSIS_SERVICE_URL: "http://analysis-service:8000"
    ports:
      - "8000:8000"
    depends_on:
      - analysis-service
      - postgres
      - redis
      - qdrant
```

- [ ] **Step 2: Run focused checks**

Run:

```bash
uv run pytest apps/api-gateway/tests -v -W error
```

Expected: pass.

- [ ] **Step 3: Run repository checks**

Run:

```bash
uv run ruff check apps packages research
uv run ty check apps packages research
uv run pytest packages apps research/tests -v -W error
```

Expected: all commands pass.

- [ ] **Step 4: Optional Docker smoke check**

Run:

```bash
docker compose -f deploy/compose.yaml build api-gateway
```

Expected: build completes and Zapros is installed inside the gateway image.

- [ ] **Step 5: Commit deploy wiring**

Commit:

```bash
git add deploy/compose.yaml README.md
git commit -m "chore: настроить gateway для analysis service"
```

If `README.md` is not changed, omit it from `git add`.

## Completion

- Push branch:

```bash
git push -u origin feature/api-analysis-integration
```

- Open PR to `dev`:

```bash
gh pr create --base dev --head feature/api-analysis-integration --title "feat: интегрировать api gateway с analysis service" --body "Добавляет POST /api/v1/analyze в api-gateway и проксирует запросы в analysis-service через typed application port и Zapros HTTP client."
```
