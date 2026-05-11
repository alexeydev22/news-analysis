# Topic Forecast Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a visible topic forecast feature that groups indexed news through Qdrant-neighborhood relationships, aggregates impact signals, and shows cautious forecasts in the frontend.

**Architecture:** `retrieval-service` owns Qdrant access and exposes indexed documents plus neighbor lookup. `analysis-service` owns the topic forecast use case, job state, JSON storage, and forecast aggregation. React frontend starts the job, polls status, and renders the latest forecast.

**Tech Stack:** FastAPI/Granian, Dishka, Taskiq + Redis, Qdrant, zapros/http clients, Pydantic contracts, React/Vite/Vitest, pytest, ruff, ty.

---

## File Structure

- Modify `packages/contracts/src/economic_news_contracts/retrieval.py`: add list/neighbors DTOs.
- Modify `packages/contracts/src/economic_news_contracts/analysis.py`: add topic forecast DTOs.
- Modify `apps/retrieval-service/src/retrieval_service/domain/model.py`: add list/neighbors query/result domain types if needed.
- Modify `apps/retrieval-service/src/retrieval_service/application/ports.py`: extend `VectorRepository`.
- Modify `apps/retrieval-service/src/retrieval_service/application/use_cases.py`: add `ListIndexedDocuments`, `FindNewsNeighbors`.
- Modify `apps/retrieval-service/src/retrieval_service/infrastructure/qdrant_repository.py`: implement scroll and neighbor lookup.
- Modify `apps/retrieval-service/src/retrieval_service/presentation/router.py`: expose `GET /documents`, `POST /neighbors`.
- Add/modify retrieval-service tests in `apps/retrieval-service/tests`.
- Add analysis-service topic forecast domain/application/infrastructure files:
  - `apps/analysis-service/src/analysis_service/application/topic_forecast.py`
  - `apps/analysis-service/src/analysis_service/infrastructure/topic_forecast_storage.py`
  - `apps/analysis-service/src/analysis_service/infrastructure/retrieval_client.py`
  - `apps/analysis-service/src/analysis_service/workers/topic_forecast_tasks.py` or extend existing tasks cleanly.
- Modify `apps/analysis-service/src/analysis_service/main/container.py`, `settings.py`, `presentation/router.py`.
- Add analysis-service tests in `apps/analysis-service/tests`.
- Add frontend API/types/component:
  - `frontend/web/src/api/topicForecast.ts`
  - `frontend/web/src/components/TopicForecastPanel.tsx`
  - modify `frontend/web/src/app/types.ts`, `App.tsx`, `App.module.css`, tests/fixtures.
- Update docs: `docs/demo.md`, `docs/deployment/model-modes-and-large-datasets.md`.

## Task 1: Contracts

**Files:**
- Modify: `packages/contracts/src/economic_news_contracts/retrieval.py`
- Modify: `packages/contracts/src/economic_news_contracts/analysis.py`
- Test: `packages/contracts/tests/test_topic_forecast_contracts.py`

- [ ] **Step 1: Write contract tests**

Create `packages/contracts/tests/test_topic_forecast_contracts.py`:

```python
from economic_news_contracts.analysis import (
    EnqueueTopicForecastJobResponse,
    ImpactLabel,
    TopicForecastItemResponse,
    TopicForecastJobResponse,
    TopicForecastJobStatus,
    TopicForecastNewsItemResponse,
    TopicForecastResponse,
)
from economic_news_contracts.retrieval import (
    FindNeighborsRequest,
    FindNeighborsResponse,
    IndexedNewsDocument,
    ListIndexedDocumentsResponse,
    NewsNeighbor,
    NewsNeighborGroup,
)


def test_retrieval_neighbor_contracts_validate_payloads() -> None:
    document = IndexedNewsDocument(
        id="news-1",
        title="Inflation slows",
        text="Inflation slowed for the second month",
        source="FNSPID",
    )
    request = FindNeighborsRequest(document_ids=["news-1"], limit=3)
    response = FindNeighborsResponse(
        groups=[
            NewsNeighborGroup(
                document_id="news-1",
                neighbors=[
                    NewsNeighbor(
                        id="news-2",
                        score=0.87,
                        title="Prices cool",
                        text="Price pressure eased",
                        source="FNSPID",
                    ),
                ],
            ),
        ],
    )

    assert ListIndexedDocumentsResponse(documents=[document]).documents[0].id == "news-1"
    assert request.limit == 3
    assert response.groups[0].neighbors[0].score == 0.87


def test_topic_forecast_contracts_validate_payloads() -> None:
    news = TopicForecastNewsItemResponse(
        id="news-1",
        title="GDP grows",
        source="FNSPID",
        impact=ImpactLabel.POSITIVE,
        score=0.91,
    )
    topic = TopicForecastItemResponse(
        topic_id="topic-1",
        title="GDP growth",
        summary="Several news items point to stronger growth.",
        overall_impact=ImpactLabel.POSITIVE,
        confidence=0.75,
        positive_count=2,
        neutral_count=1,
        negative_count=0,
        forecast="Вероятно положительное влияние. Это аналитическая оценка, не финансовая рекомендация.",
        arguments=["Доля positive-сигналов выше остальных."],
        risks=["Сигналы могут измениться после новых данных."],
        news=[news],
    )
    response = TopicForecastResponse(generated_at="2026-05-11T10:00:00Z", topics=[topic])
    job = TopicForecastJobResponse(
        job_id="job-1",
        status=TopicForecastJobStatus.SUCCEEDED,
        report_path="reports/topics/topic-forecast.json",
    )

    assert EnqueueTopicForecastJobResponse(job_id="job-1").status == TopicForecastJobStatus.QUEUED
    assert response.topics[0].overall_impact == ImpactLabel.POSITIVE
    assert job.status == TopicForecastJobStatus.SUCCEEDED
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest packages/contracts/tests/test_topic_forecast_contracts.py -v
```

Expected: FAIL with missing contract classes.

- [ ] **Step 3: Add retrieval DTOs**

Append to `packages/contracts/src/economic_news_contracts/retrieval.py`:

```python
class IndexedNewsDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source: str = Field(min_length=1)
    published_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id", "title", "text", "source")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must not be empty")
        return normalized


class ListIndexedDocumentsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documents: list[IndexedNewsDocument] = Field(default_factory=list)


class FindNeighborsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_ids: list[str] = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)
    source: str | None = Field(default=None, min_length=1)

    @field_validator("document_ids")
    @classmethod
    def normalize_document_ids(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("Document ids must not be empty")
        return normalized

    @field_validator("source")
    @classmethod
    def normalize_source(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must not be empty")
        return normalized


class NewsNeighbor(IndexedNewsDocument):
    score: float = Field(ge=-1.0, le=1.0)


class NewsNeighborGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1)
    neighbors: list[NewsNeighbor] = Field(default_factory=list)


class FindNeighborsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    groups: list[NewsNeighborGroup] = Field(default_factory=list)
```

- [ ] **Step 4: Add analysis DTOs**

Append to `packages/contracts/src/economic_news_contracts/analysis.py`:

```python
class TopicForecastJobStatus(StrEnum):
    QUEUED = "queued"
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class EnqueueTopicForecastJobResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(min_length=1)
    status: TopicForecastJobStatus = TopicForecastJobStatus.QUEUED


class TopicForecastJobResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(min_length=1)
    status: TopicForecastJobStatus
    message: str | None = None
    report_path: str | None = None


class TopicForecastNewsItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source: str = Field(min_length=1)
    impact: ImpactLabel
    score: float | None = Field(default=None, ge=-1.0, le=1.0)


class TopicForecastItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    overall_impact: ImpactLabel
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    positive_count: int = Field(ge=0)
    neutral_count: int = Field(ge=0)
    negative_count: int = Field(ge=0)
    forecast: str = Field(min_length=1)
    arguments: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    news: list[TopicForecastNewsItemResponse] = Field(default_factory=list)


class TopicForecastResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: str
    topics: list[TopicForecastItemResponse] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 5: Verify contracts**

Run:

```bash
uv run pytest packages/contracts/tests/test_topic_forecast_contracts.py -v
uv run ruff check packages/contracts/src/economic_news_contracts packages/contracts/tests/test_topic_forecast_contracts.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/contracts/src/economic_news_contracts/retrieval.py packages/contracts/src/economic_news_contracts/analysis.py packages/contracts/tests/test_topic_forecast_contracts.py
git commit -m "feat: добавить контракты тематического прогноза"
```

## Task 2: Retrieval Documents and Neighbors API

**Files:**
- Modify: `apps/retrieval-service/src/retrieval_service/application/ports.py`
- Modify: `apps/retrieval-service/src/retrieval_service/application/use_cases.py`
- Modify: `apps/retrieval-service/src/retrieval_service/presentation/router.py`
- Modify: `apps/retrieval-service/src/retrieval_service/infrastructure/qdrant_repository.py`
- Test: `apps/retrieval-service/tests/test_topic_retrieval_api.py`

- [ ] **Step 1: Write failing API tests with fake repository**

Create `apps/retrieval-service/tests/test_topic_retrieval_api.py`:

```python
from fastapi.testclient import TestClient

from retrieval_service.main.app import create_app


def test_list_documents_endpoint_returns_indexed_documents() -> None:
    with TestClient(create_app(use_fake_components=True)) as client:
        response = client.get("/api/v1/documents?limit=2")

    assert response.status_code == 200
    assert response.json() == {
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
    }


def test_neighbors_endpoint_returns_groups() -> None:
    with TestClient(create_app(use_fake_components=True)) as client:
        response = client.post(
            "/api/v1/neighbors",
            json={"document_ids": ["news-1"], "limit": 2},
        )

    assert response.status_code == 200
    assert response.json() == {
        "groups": [
            {
                "document_id": "news-1",
                "neighbors": [
                    {
                        "id": "news-2",
                        "score": 0.86,
                        "title": "GDP outlook improves",
                        "text": "Analysts upgraded GDP outlook.",
                        "source": "demo",
                        "published_at": None,
                        "metadata": {},
                    },
                ],
            },
        ],
    }
```

Update `FakeVectorRepository` in `apps/retrieval-service/src/retrieval_service/main/container.py` so these endpoints can run with `create_app(use_fake_components=True)`.

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest apps/retrieval-service/tests/test_topic_retrieval_api.py -v
```

Expected: FAIL because endpoints/use cases are missing.

- [ ] **Step 3: Extend repository port**

In `apps/retrieval-service/src/retrieval_service/application/ports.py`, add:

```python
    async def list_documents(self, *, limit: int, source: str | None) -> list[NewsDocument]:
        """Return indexed documents from vector store payloads."""
        raise NotImplementedError

    async def neighbors(
        self,
        *,
        document_ids: list[str],
        limit: int,
        source: str | None,
    ) -> dict[str, list[SearchResult]]:
        """Return nearest indexed documents for each seed document id."""
        raise NotImplementedError
```

- [ ] **Step 4: Add use cases**

In `apps/retrieval-service/src/retrieval_service/application/use_cases.py`, add:

```python
class ListIndexedDocuments:
    def __init__(self, repository: VectorRepository) -> None:
        self._repository = repository

    async def execute(self, *, limit: int, source: str | None) -> list[NewsDocument]:
        return await self._repository.list_documents(limit=limit, source=source)


class FindNewsNeighbors:
    def __init__(self, repository: VectorRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        *,
        document_ids: list[str],
        limit: int,
        source: str | None,
    ) -> dict[str, list[SearchResult]]:
        return await self._repository.neighbors(
            document_ids=document_ids,
            limit=limit,
            source=source,
        )
```

- [ ] **Step 5: Add router endpoints**

In `apps/retrieval-service/src/retrieval_service/presentation/router.py`, import new DTOs/use cases and add:

```python
@router.get("/documents")
@inject
async def list_documents(
    use_case: FromDishka[ListIndexedDocuments],
    limit: int = 100,
    source: str | None = None,
) -> ListIndexedDocumentsResponse:
    documents = await use_case.execute(limit=min(max(limit, 1), 500), source=source)
    return ListIndexedDocumentsResponse(
        documents=[_to_indexed_document(document) for document in documents],
    )


@router.post("/neighbors")
@inject
async def find_neighbors(
    request: FindNeighborsRequest,
    use_case: FromDishka[FindNewsNeighbors],
) -> FindNeighborsResponse:
    groups = await use_case.execute(
        document_ids=request.document_ids,
        limit=request.limit,
        source=request.source,
    )
    return FindNeighborsResponse(
        groups=[
            NewsNeighborGroup(
                document_id=document_id,
                neighbors=[_to_neighbor(result) for result in results],
            )
            for document_id, results in groups.items()
        ],
    )
```

Add helpers `_to_indexed_document` and `_to_neighbor` by copying mapping style from existing search endpoint.

- [ ] **Step 6: Implement Qdrant methods**

In `qdrant_repository.py`, implement:

- `list_documents`: call `scroll`, map points via existing `_to_document` helper.
- `neighbors`: retrieve seed points by `_point_id`, query Qdrant by seed vector, exclude same document.

Keep this implementation small and covered by unit/infrastructure tests where feasible. If Qdrant client API details differ, adapt to existing qdrant-client version used in the repo.

- [ ] **Step 7: Verify retrieval API tests**

Run:

```bash
uv run pytest apps/retrieval-service/tests/test_topic_retrieval_api.py -v
uv run ruff check apps/retrieval-service/src/retrieval_service apps/retrieval-service/tests/test_topic_retrieval_api.py
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add apps/retrieval-service/src/retrieval_service packages/contracts/src/economic_news_contracts/retrieval.py apps/retrieval-service/tests/test_topic_retrieval_api.py
git commit -m "feat: добавить endpoints соседей новостей"
```

## Task 3: Analysis Topic Forecast Core

**Files:**
- Create: `apps/analysis-service/src/analysis_service/application/topic_forecast.py`
- Test: `apps/analysis-service/tests/test_topic_forecast_core.py`

- [ ] **Step 1: Write core tests**

Create `apps/analysis-service/tests/test_topic_forecast_core.py`:

```python
from economic_news_contracts.analysis import AnalysisModelName, ImpactLabel
from economic_news_contracts.dialog import DialogImpactSummary
from economic_news_contracts.retrieval import IndexedNewsDocument, NewsNeighbor, NewsNeighborGroup

from analysis_service.application.topic_forecast import build_topic_forecast


def test_topic_forecast_groups_neighbors_and_aggregates_impacts() -> None:
    documents = [
        IndexedNewsDocument(id="news-1", title="GDP grows", text="GDP grew", source="demo"),
        IndexedNewsDocument(id="news-2", title="GDP outlook improves", text="Outlook improves", source="demo"),
        IndexedNewsDocument(id="news-3", title="Oil falls", text="Oil prices fall", source="demo"),
    ]
    neighbor_groups = [
        NewsNeighborGroup(
            document_id="news-1",
            neighbors=[
                NewsNeighbor(
                    id="news-2",
                    score=0.88,
                    title="GDP outlook improves",
                    text="Outlook improves",
                    source="demo",
                ),
            ],
        ),
    ]
    impacts = {
        "news-1": DialogImpactSummary(
            news_id="news-1",
            model_name=AnalysisModelName.TFIDF_LOGREG,
            impact=ImpactLabel.POSITIVE,
            confidence=0.8,
            explanation="growth signal",
        ),
        "news-2": DialogImpactSummary(
            news_id="news-2",
            model_name=AnalysisModelName.TFIDF_LOGREG,
            impact=ImpactLabel.POSITIVE,
            confidence=0.7,
            explanation="outlook signal",
        ),
        "news-3": DialogImpactSummary(
            news_id="news-3",
            model_name=AnalysisModelName.TFIDF_LOGREG,
            impact=ImpactLabel.NEGATIVE,
            confidence=0.6,
            explanation="price signal",
        ),
    }

    topics = build_topic_forecast(
        documents=documents,
        neighbor_groups=neighbor_groups,
        impacts_by_news_id=impacts,
        min_neighbor_score=0.72,
        max_topic_size=8,
    )

    assert topics[0].overall_impact == ImpactLabel.POSITIVE
    assert topics[0].positive_count == 2
    assert "не финансовая рекомендация" in topics[0].forecast
    assert {item.id for item in topics[0].news} == {"news-1", "news-2"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest apps/analysis-service/tests/test_topic_forecast_core.py -v
```

Expected: FAIL because module is missing.

- [ ] **Step 3: Implement core pure functions**

In `topic_forecast.py`, implement pure functions:

- `build_components(documents, neighbor_groups, min_score)`;
- `build_topic_title(news_items)`;
- `aggregate_impact(news_items, predictions)`;
- `build_topic_forecast(documents, neighbor_groups, impacts_by_news_id, min_neighbor_score, max_topic_size)`.

Use existing `ImpactLabel` and avoid external dependencies.

- [ ] **Step 4: Verify core tests**

Run:

```bash
uv run pytest apps/analysis-service/tests/test_topic_forecast_core.py -v
uv run ruff check apps/analysis-service/src/analysis_service/application/topic_forecast.py apps/analysis-service/tests/test_topic_forecast_core.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/analysis-service/src/analysis_service/application/topic_forecast.py apps/analysis-service/tests/test_topic_forecast_core.py
git commit -m "feat: добавить расчет тематического прогноза"
```

## Task 4: Analysis Topic Forecast API and Worker

**Files:**
- Create/modify analysis-service topic forecast storage/client/queue/task files.
- Modify `apps/analysis-service/src/analysis_service/main/settings.py`
- Modify `apps/analysis-service/src/analysis_service/main/container.py`
- Modify `apps/analysis-service/src/analysis_service/presentation/router.py`
- Test: `apps/analysis-service/tests/test_topic_forecast_api.py`
- Test: `apps/analysis-service/tests/test_topic_forecast_infrastructure.py`

- [ ] **Step 1: Write API/storage tests**

Tests should cover:

- `POST /api/v1/topic-forecast/jobs` returns queued job;
- `GET /api/v1/topic-forecast/jobs/{job_id}` returns status;
- missing job returns 404 or mapped domain error;
- `GET /api/v1/topic-forecast/latest` returns forecast or null;
- JSON storage round-trips job and forecast.

- [ ] **Step 2: Implement storage and use cases**

Mirror the existing ML report job pattern:

- `TopicForecastStorage`;
- `JsonTopicForecastStorage`;
- `EnqueueTopicForecastJob`;
- `GetTopicForecastJob`;
- `GetLatestTopicForecast`.

Generate job id before enqueue and persist queued before publishing task.

- [ ] **Step 3: Implement retrieval client**

Add `analysis_service.infrastructure.retrieval_client.TopicRetrievalClient` using zapros/http pattern already used in repo clients. It calls:

- `GET /api/v1/documents`;
- `POST /api/v1/neighbors`.

- [ ] **Step 4: Implement task**

Task flow:

1. save `started`;
2. list documents;
3. if not enough documents, save empty forecast with metadata message and `succeeded`;
4. get neighbors;
5. run topic forecast core;
6. save latest forecast;
7. save job `succeeded`;
8. on exception save `failed` with message.

- [ ] **Step 5: Wire DI/router/settings**

Settings:

- `topic_forecast_output_path = reports/topics/topic-forecast.json`;
- `topic_forecast_jobs_dir = reports/topics/jobs`;
- `topic_forecast_max_documents = 100`;
- `topic_forecast_min_neighbor_score = 0.72`;
- `topic_forecast_max_topic_size = 8`.

Router endpoints:

- `POST /api/v1/topic-forecast/jobs`;
- `GET /api/v1/topic-forecast/jobs/{job_id}`;
- `GET /api/v1/topic-forecast/latest`.

- [ ] **Step 6: Verify analysis tests**

Run:

```bash
uv run pytest apps/analysis-service/tests/test_topic_forecast_core.py apps/analysis-service/tests/test_topic_forecast_api.py apps/analysis-service/tests/test_topic_forecast_infrastructure.py -v
uv run ruff check apps/analysis-service/src/analysis_service apps/analysis-service/tests/test_topic_forecast_core.py apps/analysis-service/tests/test_topic_forecast_api.py apps/analysis-service/tests/test_topic_forecast_infrastructure.py
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/analysis-service/src/analysis_service apps/analysis-service/tests packages/contracts/src/economic_news_contracts/analysis.py
git commit -m "feat: добавить API тематического прогноза"
```

## Task 5: Compose and Frontend

**Files:**
- Modify `deploy/compose.yaml`
- Modify `frontend/web/src/app/types.ts`
- Create `frontend/web/src/api/topicForecast.ts`
- Create `frontend/web/src/components/TopicForecastPanel.tsx`
- Modify `frontend/web/src/app/App.tsx`
- Modify `frontend/web/src/app/App.module.css`
- Modify frontend tests/fixtures.

- [ ] **Step 1: Write frontend API/component tests**

Add tests for:

- start topic forecast job API;
- load latest topic forecast;
- button starts job and renders topic title/forecast.

- [ ] **Step 2: Implement frontend API/types**

Add TS types mirroring contracts:

- `TopicForecastJob`;
- `TopicForecast`;
- `TopicForecastTopic`;
- `TopicForecastNewsItem`.

Add API functions:

- `startTopicForecastJob`;
- `getTopicForecastJob`;
- `getLatestTopicForecast`.

- [ ] **Step 3: Implement panel and App integration**

Panel props:

- `forecast`;
- `status`;
- `error`;
- `isLoading`;
- `onGenerate`.

Render compact topic cards with impact counts, forecast, arguments, risks, and news list.

- [ ] **Step 4: Compose volumes/env**

Ensure `analysis-service` and `analysis-worker` share `reports/topics` through existing `../reports:/app/reports` volume. Add env if settings require retrieval URL or topic forecast paths.

- [ ] **Step 5: Verify frontend**

Run:

```bash
npm --prefix frontend/web test -- --run
npm --prefix frontend/web run build
docker compose -f deploy/compose.yaml config --quiet
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/web deploy/compose.yaml
git commit -m "feat: показать тематический прогноз"
```

## Task 6: Documentation and Final Verification

**Files:**
- Modify `docs/demo.md`
- Modify `docs/deployment/model-modes-and-large-datasets.md`
- Modify `docs/coursework/thesis-draft.md` if needed.

- [ ] **Step 1: Update docs**

Document demo flow:

```bash
just prepare-fnspid
just ml-full
just demo-up-trained
```

Then in UI:

1. preview CSV;
2. index CSV;
3. click `Сформировать прогноз по темам`;
4. inspect topic forecast panel.

- [ ] **Step 2: Full focused verification**

Run:

```bash
uv run pytest packages/contracts/tests/test_topic_forecast_contracts.py apps/retrieval-service/tests/test_topic_retrieval_api.py apps/analysis-service/tests/test_topic_forecast_core.py apps/analysis-service/tests/test_topic_forecast_api.py apps/analysis-service/tests/test_topic_forecast_infrastructure.py -v
uv run ruff check packages/contracts/src/economic_news_contracts apps/retrieval-service/src/retrieval_service apps/analysis-service/src/analysis_service
uv run ty check packages/contracts/src/economic_news_contracts apps/retrieval-service/src/retrieval_service apps/analysis-service/src/analysis_service
npm --prefix frontend/web test -- --run
npm --prefix frontend/web run build
docker compose -f deploy/compose.yaml config --quiet
```

Expected: PASS.

- [ ] **Step 3: Commit docs/fixes**

```bash
git add docs
git commit -m "docs: описать тематический прогноз в demo"
```

- [ ] **Step 4: Push and PR**

```bash
git push -u origin feature/topic-forecast-design
gh pr create --base dev --head feature/topic-forecast-design --title "feat: добавить тематический прогноз" --body "<summary and checks>"
```

## Self-Review

- Spec coverage: retrieval documents/neighbors, analysis topic forecast, job storage, frontend, docs, and verification are covered.
- Scope: no separate forecast-service, no per-question recomputation, no investment advice.
- Type consistency: DTO names match spec names.
- Risk: Qdrant neighbor implementation may need adaptation to exact qdrant-client methods; this is isolated in Task 2.
