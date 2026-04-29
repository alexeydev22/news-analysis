# Retrieval Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone `retrieval-service` that indexes economic news into Qdrant and searches relevant news with FastEmbed embeddings.

**Architecture:** The service follows the existing DDD/layered pattern: contracts in `packages/contracts`, domain objects without framework dependencies, application use cases behind Protocol ports, infrastructure adapters for FastEmbed/Qdrant, presentation routes through Dishka. The service is intentionally independent from `api-gateway` and `analysis-service` in this phase.

**Tech Stack:** Python 3.12, FastAPI, Granian, Dishka, Pydantic, FastEmbed, Qdrant client, structlog, pytest, Docker Compose.

---

## File Structure

- Modify `pyproject.toml`: add `apps/retrieval-service` to workspace members and pythonpath.
- Modify `packages/contracts/src/economic_news_contracts/__init__.py`: export retrieval contracts if local style requires it.
- Create `packages/contracts/src/economic_news_contracts/retrieval.py`: Pydantic request/response models.
- Modify `packages/contracts/tests/test_contracts.py`: add retrieval contract tests.
- Create `apps/retrieval-service/pyproject.toml`: service package and dependencies.
- Create `apps/retrieval-service/src/retrieval_service/domain/errors.py`: domain/service errors.
- Create `apps/retrieval-service/src/retrieval_service/domain/model.py`: domain value objects.
- Create `apps/retrieval-service/src/retrieval_service/application/ports.py`: `EmbeddingProvider`, `VectorRepository`.
- Create `apps/retrieval-service/src/retrieval_service/application/use_cases.py`: indexing and search use cases.
- Create `apps/retrieval-service/src/retrieval_service/infrastructure/embeddings.py`: FastEmbed adapter.
- Create `apps/retrieval-service/src/retrieval_service/infrastructure/qdrant_repository.py`: Qdrant adapter.
- Create `apps/retrieval-service/src/retrieval_service/main/settings.py`: `RETRIEVAL_` settings.
- Create `apps/retrieval-service/src/retrieval_service/main/container.py`: Dishka providers.
- Create `apps/retrieval-service/src/retrieval_service/main/app.py`: FastAPI app factory.
- Create `apps/retrieval-service/src/retrieval_service/presentation/router.py`: `/api/v1/index`, `/api/v1/search`.
- Create `apps/retrieval-service/src/retrieval_service/presentation/errors.py`: error mapping.
- Create `apps/retrieval-service/tests/*`: focused tests by layer.
- Create `deploy/docker/retrieval-service.Dockerfile`: runtime image.
- Modify `deploy/compose.yaml`: add `retrieval-service`.
- Modify `uv.lock`: dependency lock update.

## Task 1: Retrieval Contracts

**Files:**
- Create: `packages/contracts/src/economic_news_contracts/retrieval.py`
- Modify: `packages/contracts/tests/test_contracts.py`

- [ ] **Step 1: Write failing contract tests**

Append to `packages/contracts/tests/test_contracts.py`:

```python
from economic_news_contracts.retrieval import (
    IndexNewsRequest,
    IndexNewsResponse,
    NewsDocumentPayload,
    SearchNewsRequest,
    SearchNewsResponse,
    SearchNewsResult,
)


def test_news_document_payload_trims_required_text_fields() -> None:
    document = NewsDocumentPayload(
        id=" news-1 ",
        title="  Inflation slows  ",
        text="  Prices grew slower than expected.  ",
        source="  Reuters  ",
    )

    assert document.id == "news-1"
    assert document.title == "Inflation slows"
    assert document.text == "Prices grew slower than expected."
    assert document.source == "Reuters"


def test_index_news_request_requires_documents() -> None:
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

    assert len(request.documents) == 1


def test_search_news_request_trims_query_and_defaults_limit() -> None:
    request = SearchNewsRequest(query="  key rate decision  ")

    assert request.query == "key rate decision"
    assert request.limit == 5
    assert request.source is None


def test_search_news_response_serializes_results() -> None:
    response = SearchNewsResponse(
        results=[
            SearchNewsResult(
                id="news-1",
                score=0.91,
                title="GDP grows",
                text="GDP grew by 2 percent.",
                source="demo",
                metadata={"sector": "macro"},
            ),
        ],
    )

    assert response.model_dump(mode="json") == {
        "results": [
            {
                "id": "news-1",
                "score": 0.91,
                "title": "GDP grows",
                "text": "GDP grew by 2 percent.",
                "source": "demo",
                "published_at": None,
                "metadata": {"sector": "macro"},
            },
        ],
    }


def test_index_news_response_reports_collection_and_count() -> None:
    response = IndexNewsResponse(indexed_count=2, collection_name="economic_news")

    assert response.indexed_count == 2
    assert response.collection_name == "economic_news"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run pytest packages/contracts/tests/test_contracts.py -v
```

Expected: fail with `ModuleNotFoundError: No module named 'economic_news_contracts.retrieval'`.

- [ ] **Step 3: Implement retrieval contracts**

Create `packages/contracts/src/economic_news_contracts/retrieval.py`:

```python
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NewsDocumentPayload(BaseModel):
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


class IndexNewsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documents: list[NewsDocumentPayload] = Field(min_length=1)


class IndexNewsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    indexed_count: int = Field(ge=0)
    collection_name: str = Field(min_length=1)


class SearchNewsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)
    source: str | None = Field(default=None, min_length=1)

    @field_validator("query", "source")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must not be empty")
        return normalized


class SearchNewsResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    score: float = Field(ge=0.0)
    title: str
    text: str
    source: str
    published_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchNewsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[SearchNewsResult]
```

- [ ] **Step 4: Run contract tests and commit**

Run:

```bash
uv run pytest packages/contracts/tests/test_contracts.py -v
```

Expected: pass.

Commit:

```bash
git add packages/contracts/src/economic_news_contracts/retrieval.py packages/contracts/tests/test_contracts.py
git commit -m "feat: добавить контракты retrieval service"
```

## Task 2: Domain and Application Use Cases

**Files:**
- Create: `apps/retrieval-service/pyproject.toml`
- Create package directories under `apps/retrieval-service/src/retrieval_service/`
- Create: `apps/retrieval-service/src/retrieval_service/domain/errors.py`
- Create: `apps/retrieval-service/src/retrieval_service/domain/model.py`
- Create: `apps/retrieval-service/src/retrieval_service/application/ports.py`
- Create: `apps/retrieval-service/src/retrieval_service/application/use_cases.py`
- Create: `apps/retrieval-service/tests/test_domain.py`
- Create: `apps/retrieval-service/tests/test_use_cases.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Add workspace member and service package**

Modify root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = [
  "packages/framework",
  "packages/contracts",
  "apps/api-gateway",
  "apps/analysis-service",
  "apps/retrieval-service",
  "research",
]
```

Add `apps/retrieval-service/src` to `[tool.pytest.ini_options].pythonpath`.

Create `apps/retrieval-service/pyproject.toml`:

```toml
[project]
name = "economic-news-retrieval-service"
version = "0.1.0"
description = "Retrieval service for economic news semantic search"
requires-python = ">=3.12"
dependencies = [
  "economic-news-framework",
  "economic-news-contracts",
  "fastapi>=0.115",
  "granian>=1.7",
  "dishka>=1.4",
  "pydantic-settings>=2.6",
  "structlog>=24.4",
  "fastembed>=0.7",
  "qdrant-client>=1.13",
]

[project.optional-dependencies]
test = [
  "httpx>=0.28",
  "pytest>=8.3",
  "pytest-asyncio>=0.24",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/retrieval_service"]

[tool.uv.sources]
economic-news-framework = { workspace = true }
economic-news-contracts = { workspace = true }
```

Create empty `__init__.py` files in:

```text
apps/retrieval-service/src/retrieval_service/__init__.py
apps/retrieval-service/src/retrieval_service/domain/__init__.py
apps/retrieval-service/src/retrieval_service/application/__init__.py
apps/retrieval-service/src/retrieval_service/infrastructure/__init__.py
apps/retrieval-service/src/retrieval_service/main/__init__.py
apps/retrieval-service/src/retrieval_service/presentation/__init__.py
apps/retrieval-service/src/retrieval_service/workers/__init__.py
```

- [ ] **Step 2: Write failing domain tests**

Create `apps/retrieval-service/tests/test_domain.py`:

```python
import pytest

from retrieval_service.domain.errors import EmptyDocumentTextError, InvalidSearchLimitError
from retrieval_service.domain.model import NewsDocument, SearchQuery


def test_news_document_trims_fields() -> None:
    document = NewsDocument(
        id=" id-1 ",
        title="  Title  ",
        text="  Body  ",
        source="  source  ",
    )

    assert document.id == "id-1"
    assert document.title == "Title"
    assert document.text == "Body"
    assert document.source == "source"


def test_news_document_rejects_blank_text() -> None:
    with pytest.raises(EmptyDocumentTextError):
        NewsDocument(id="id-1", title="Title", text=" ", source="source")


def test_search_query_trims_query_and_source() -> None:
    query = SearchQuery(query="  inflation  ", limit=3, source="  cbr  ")

    assert query.query == "inflation"
    assert query.limit == 3
    assert query.source == "cbr"


def test_search_query_rejects_invalid_limit() -> None:
    with pytest.raises(InvalidSearchLimitError):
        SearchQuery(query="inflation", limit=0)
```

- [ ] **Step 3: Implement domain**

Create `apps/retrieval-service/src/retrieval_service/domain/errors.py`:

```python
class RetrievalError(RuntimeError):
    """Base retrieval-service error."""


class EmptyDocumentTextError(RetrievalError):
    """Raised when a news document has empty text fields."""


class InvalidSearchLimitError(RetrievalError):
    """Raised when search limit is outside the supported range."""


class RetrievalUnavailableError(RetrievalError):
    """Raised when vector search infrastructure is unavailable."""
```

Create `apps/retrieval-service/src/retrieval_service/domain/model.py`:

```python
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping

from retrieval_service.domain.errors import EmptyDocumentTextError, InvalidSearchLimitError


def _required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise EmptyDocumentTextError(f"{field_name} must not be empty")
    return normalized


@dataclass(frozen=True)
class NewsDocument:
    id: str
    title: str
    text: str
    source: str
    published_at: datetime | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _required_text(self.id, "id"))
        object.__setattr__(self, "title", _required_text(self.title, "title"))
        object.__setattr__(self, "text", _required_text(self.text, "text"))
        object.__setattr__(self, "source", _required_text(self.source, "source"))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True)
class SearchQuery:
    query: str
    limit: int = 5
    source: str | None = None

    def __post_init__(self) -> None:
        if self.limit < 1 or self.limit > 20:
            raise InvalidSearchLimitError("Search limit must be between 1 and 20")
        object.__setattr__(self, "query", _required_text(self.query, "query"))
        if self.source is not None:
            object.__setattr__(self, "source", _required_text(self.source, "source"))


@dataclass(frozen=True)
class SearchResult:
    document: NewsDocument
    score: float
```

- [ ] **Step 4: Write failing use case tests**

Create `apps/retrieval-service/tests/test_use_cases.py`:

```python
import pytest

from retrieval_service.application.use_cases import IndexNewsDocuments, SearchNews
from retrieval_service.domain.model import NewsDocument, SearchQuery


class FakeEmbeddingProvider:
    def __init__(self) -> None:
        self.texts: list[str] = []

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.texts = texts
        return [[float(index), 0.5] for index, _ in enumerate(texts, start=1)]


class FakeVectorRepository:
    def __init__(self) -> None:
        self.indexed: list[tuple[NewsDocument, list[float]]] = []
        self.search_vector: list[float] | None = None
        self.search_query: SearchQuery | None = None

    async def upsert(self, documents: list[NewsDocument], vectors: list[list[float]]) -> int:
        self.indexed = list(zip(documents, vectors, strict=True))
        return len(documents)

    async def search(self, query: SearchQuery, vector: list[float]):
        self.search_query = query
        self.search_vector = vector
        return []


@pytest.mark.asyncio
async def test_index_news_documents_embeds_text_and_upserts_vectors() -> None:
    embedder = FakeEmbeddingProvider()
    repository = FakeVectorRepository()
    use_case = IndexNewsDocuments(embedder, repository)
    document = NewsDocument(id="n1", title="Title", text="Body", source="demo")

    indexed_count = await use_case.execute([document])

    assert indexed_count == 1
    assert embedder.texts == ["Title\n\nBody"]
    assert repository.indexed == [(document, [1.0, 0.5])]


@pytest.mark.asyncio
async def test_search_news_embeds_query_and_uses_repository() -> None:
    embedder = FakeEmbeddingProvider()
    repository = FakeVectorRepository()
    use_case = SearchNews(embedder, repository)
    query = SearchQuery(query="inflation", limit=3, source="demo")

    results = await use_case.execute(query)

    assert results == []
    assert embedder.texts == ["inflation"]
    assert repository.search_query == query
    assert repository.search_vector == [1.0, 0.5]
```

- [ ] **Step 5: Implement ports and use cases**

Create `apps/retrieval-service/src/retrieval_service/application/ports.py`:

```python
from typing import Protocol

from retrieval_service.domain.model import NewsDocument, SearchQuery, SearchResult


class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Build embeddings for input texts."""


class VectorRepository(Protocol):
    async def upsert(self, documents: list[NewsDocument], vectors: list[list[float]]) -> int:
        """Store documents with their vectors."""

    async def search(self, query: SearchQuery, vector: list[float]) -> list[SearchResult]:
        """Search nearest documents for query vector."""
```

Create `apps/retrieval-service/src/retrieval_service/application/use_cases.py`:

```python
from retrieval_service.application.ports import EmbeddingProvider, VectorRepository
from retrieval_service.domain.model import NewsDocument, SearchQuery, SearchResult


class IndexNewsDocuments:
    def __init__(self, embedder: EmbeddingProvider, repository: VectorRepository) -> None:
        self._embedder = embedder
        self._repository = repository

    async def execute(self, documents: list[NewsDocument]) -> int:
        texts = [f"{document.title}\n\n{document.text}" for document in documents]
        vectors = await self._embedder.embed(texts)
        return await self._repository.upsert(documents, vectors)


class SearchNews:
    def __init__(self, embedder: EmbeddingProvider, repository: VectorRepository) -> None:
        self._embedder = embedder
        self._repository = repository

    async def execute(self, query: SearchQuery) -> list[SearchResult]:
        vectors = await self._embedder.embed([query.query])
        return await self._repository.search(query, vectors[0])
```

- [ ] **Step 6: Run domain/use case tests and commit**

Run:

```bash
uv lock
uv run pytest apps/retrieval-service/tests/test_domain.py apps/retrieval-service/tests/test_use_cases.py -v
```

Expected: pass.

Commit:

```bash
git add pyproject.toml uv.lock apps/retrieval-service
git commit -m "feat: добавить домен retrieval service"
```

## Task 3: Infrastructure Adapters

**Files:**
- Create: `apps/retrieval-service/src/retrieval_service/infrastructure/embeddings.py`
- Create: `apps/retrieval-service/src/retrieval_service/infrastructure/qdrant_repository.py`
- Create: `apps/retrieval-service/tests/test_infrastructure.py`

- [ ] **Step 1: Write failing infrastructure tests**

Create `apps/retrieval-service/tests/test_infrastructure.py`:

```python
import pytest

from retrieval_service.domain.model import NewsDocument, SearchQuery
from retrieval_service.infrastructure.embeddings import FastEmbedEmbeddingProvider
from retrieval_service.infrastructure.qdrant_repository import QdrantNewsRepository


class FakeEmbeddingModel:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def embed(self, texts: list[str]):
        self.texts = texts
        return [[0.1, 0.2] for _ in texts]


class FakeQdrantClient:
    def __init__(self) -> None:
        self.collection_exists_value = False
        self.created_collection: str | None = None
        self.points: list[object] = []
        self.query_filter: object | None = None

    def collection_exists(self, collection_name: str) -> bool:
        return self.collection_exists_value

    def create_collection(self, collection_name: str, vectors_config: object) -> None:
        self.collection_exists_value = True
        self.created_collection = collection_name

    def upsert(self, collection_name: str, points: list[object]) -> None:
        self.points = points

    def query_points(self, collection_name: str, query: list[float], limit: int, query_filter=None):
        self.query_filter = query_filter
        point = type(
            "ScoredPoint",
            (),
            {
                "id": "news-1",
                "score": 0.87,
                "payload": {
                    "title": "GDP grows",
                    "text": "GDP grew by 2 percent.",
                    "source": "demo",
                    "published_at": None,
                    "metadata": {"sector": "macro"},
                },
            },
        )()
        return type("QueryResponse", (), {"points": [point]})()


@pytest.mark.asyncio
async def test_fastembed_provider_returns_vectors_from_model() -> None:
    model = FakeEmbeddingModel()
    provider = FastEmbedEmbeddingProvider(model_name="unused", model=model)

    vectors = await provider.embed(["hello"])

    assert model.texts == ["hello"]
    assert vectors == [[0.1, 0.2]]


@pytest.mark.asyncio
async def test_qdrant_repository_upserts_documents() -> None:
    client = FakeQdrantClient()
    repository = QdrantNewsRepository(
        client=client,
        collection_name="economic_news",
        vector_size=2,
    )
    document = NewsDocument(
        id="news-1",
        title="GDP grows",
        text="GDP grew by 2 percent.",
        source="demo",
        metadata={"sector": "macro"},
    )

    indexed_count = await repository.upsert([document], [[0.1, 0.2]])

    assert indexed_count == 1
    assert client.created_collection == "economic_news"
    assert len(client.points) == 1


@pytest.mark.asyncio
async def test_qdrant_repository_search_returns_domain_results() -> None:
    client = FakeQdrantClient()
    repository = QdrantNewsRepository(
        client=client,
        collection_name="economic_news",
        vector_size=2,
    )

    results = await repository.search(SearchQuery(query="GDP", source="demo"), [0.1, 0.2])

    assert len(results) == 1
    assert results[0].document.id == "news-1"
    assert results[0].document.metadata == {"sector": "macro"}
    assert results[0].score == 0.87
    assert client.query_filter is not None
```

- [ ] **Step 2: Implement embedding provider**

Create `apps/retrieval-service/src/retrieval_service/infrastructure/embeddings.py`:

```python
from typing import Any

from fastembed import TextEmbedding

from retrieval_service.domain.errors import RetrievalUnavailableError


class FastEmbedEmbeddingProvider:
    def __init__(self, model_name: str, model: Any | None = None) -> None:
        self._model = model or TextEmbedding(model_name=model_name)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            return [list(vector) for vector in self._model.embed(texts)]
        except Exception as error:
            raise RetrievalUnavailableError("embedding provider is unavailable") from error
```

- [ ] **Step 3: Implement Qdrant repository**

Create `apps/retrieval-service/src/retrieval_service/infrastructure/qdrant_repository.py`:

```python
from datetime import datetime
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams

from retrieval_service.domain.errors import RetrievalUnavailableError
from retrieval_service.domain.model import NewsDocument, SearchQuery, SearchResult


class QdrantNewsRepository:
    def __init__(
        self,
        client: QdrantClient,
        collection_name: str,
        vector_size: int,
    ) -> None:
        self._client = client
        self._collection_name = collection_name
        self._vector_size = vector_size

    async def upsert(self, documents: list[NewsDocument], vectors: list[list[float]]) -> int:
        self._ensure_collection()
        points = [
            PointStruct(id=document.id, vector=vector, payload=self._payload(document))
            for document, vector in zip(documents, vectors, strict=True)
        ]
        try:
            self._client.upsert(collection_name=self._collection_name, points=points)
        except Exception as error:
            raise RetrievalUnavailableError("vector repository is unavailable") from error
        return len(points)

    async def search(self, query: SearchQuery, vector: list[float]) -> list[SearchResult]:
        self._ensure_collection()
        try:
            response = self._client.query_points(
                collection_name=self._collection_name,
                query=vector,
                limit=query.limit,
                query_filter=self._filter(query),
            )
        except Exception as error:
            raise RetrievalUnavailableError("vector repository is unavailable") from error
        return [self._to_result(point) for point in response.points]

    def _ensure_collection(self) -> None:
        try:
            if self._client.collection_exists(self._collection_name):
                return
            self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=VectorParams(size=self._vector_size, distance=Distance.COSINE),
            )
        except Exception as error:
            raise RetrievalUnavailableError("vector repository is unavailable") from error

    def _filter(self, query: SearchQuery) -> Filter | None:
        if query.source is None:
            return None
        return Filter(
            must=[FieldCondition(key="source", match=MatchValue(value=query.source))],
        )

    def _payload(self, document: NewsDocument) -> dict[str, Any]:
        return {
            "title": document.title,
            "text": document.text,
            "source": document.source,
            "published_at": document.published_at.isoformat() if document.published_at else None,
            "metadata": dict(document.metadata),
        }

    def _published_at(self, value: Any) -> datetime | None:
        if value is None or isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))

    def _to_result(self, point: Any) -> SearchResult:
        payload = point.payload or {}
        document = NewsDocument(
            id=str(point.id),
            title=str(payload["title"]),
            text=str(payload["text"]),
            source=str(payload["source"]),
            published_at=self._published_at(payload.get("published_at")),
            metadata=payload.get("metadata") or {},
        )
        return SearchResult(document=document, score=float(point.score))
```

- [ ] **Step 4: Run infrastructure tests and commit**

Run:

```bash
uv run pytest apps/retrieval-service/tests/test_infrastructure.py -v
uv run ruff check apps/retrieval-service/src/retrieval_service/infrastructure apps/retrieval-service/tests/test_infrastructure.py
uv run ty check apps/retrieval-service/src/retrieval_service/infrastructure apps/retrieval-service/tests/test_infrastructure.py
```

Expected: pass.

Commit:

```bash
git add apps/retrieval-service/src/retrieval_service/infrastructure apps/retrieval-service/tests/test_infrastructure.py
git commit -m "feat: добавить инфраструктуру retrieval service"
```

## Task 4: Runtime, API, and Error Mapping

**Files:**
- Create: `apps/retrieval-service/src/retrieval_service/main/settings.py`
- Create: `apps/retrieval-service/src/retrieval_service/main/container.py`
- Create: `apps/retrieval-service/src/retrieval_service/main/app.py`
- Create: `apps/retrieval-service/src/retrieval_service/presentation/router.py`
- Create: `apps/retrieval-service/src/retrieval_service/presentation/errors.py`
- Create: `apps/retrieval-service/tests/test_api.py`
- Create: `apps/retrieval-service/tests/test_container.py`

- [ ] **Step 1: Write failing API tests**

Create `apps/retrieval-service/tests/test_api.py`:

```python
from fastapi.testclient import TestClient

from retrieval_service.main.app import create_app


def test_retrieval_service_health_endpoint() -> None:
    with TestClient(create_app(use_fake_components=True)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"service": "retrieval-service", "status": "ok"}


def test_index_endpoint_returns_indexed_count() -> None:
    with TestClient(create_app(use_fake_components=True)) as client:
        response = client.post(
            "/api/v1/index",
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


def test_search_endpoint_returns_results() -> None:
    with TestClient(create_app(use_fake_components=True)) as client:
        response = client.post("/api/v1/search", json={"query": "GDP", "limit": 3})

    assert response.status_code == 200
    assert response.json()["results"][0]["id"] == "news-1"
```

- [ ] **Step 2: Write failing container tests**

Create `apps/retrieval-service/tests/test_container.py`:

```python
import pytest
from dishka import AsyncContainer

from retrieval_service.application.use_cases import IndexNewsDocuments, SearchNews
from retrieval_service.main.container import create_container
from retrieval_service.main.settings import RetrievalServiceSettings


def test_retrieval_settings_defaults_and_env_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RETRIEVAL_QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("RETRIEVAL_COLLECTION_NAME", "test_news")

    settings = RetrievalServiceSettings()

    assert str(settings.qdrant_url) == "http://localhost:6333/"
    assert settings.collection_name == "test_news"


@pytest.mark.asyncio
async def test_container_resolves_use_cases_with_fake_components() -> None:
    container: AsyncContainer = create_container(use_fake_components=True)

    try:
        index_use_case = await container.get(IndexNewsDocuments)
        search_use_case = await container.get(SearchNews)
    finally:
        await container.close()

    assert isinstance(index_use_case, IndexNewsDocuments)
    assert isinstance(search_use_case, SearchNews)
```

- [ ] **Step 3: Implement settings/container/app/router/errors**

Implement runtime files following the `analysis-service` pattern:

`settings.py`:

```python
from pydantic import AnyHttpUrl
from pydantic_settings import SettingsConfigDict

from economic_news_framework.settings import BaseServiceSettings


class RetrievalServiceSettings(BaseServiceSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="RETRIEVAL_",
        extra="ignore",
    )

    service_name: str = "retrieval-service"
    version: str = "0.1.0"
    qdrant_url: AnyHttpUrl = AnyHttpUrl("http://qdrant:6333")
    collection_name: str = "economic_news"
    embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dimension: int = 384
```

Use fake components only for tests. Fake repository should return one deterministic `SearchResult`.

Router maps contract models to domain models and back:

```python
@router.post("/index")
@inject
async def index_news(
    request: IndexNewsRequest,
    use_case: FromDishka[IndexNewsDocuments],
    settings: FromDishka[RetrievalServiceSettings],
) -> IndexNewsResponse:
    documents = [
        NewsDocument(
            id=document.id,
            title=document.title,
            text=document.text,
            source=document.source,
            published_at=document.published_at,
            metadata=document.metadata,
        )
        for document in request.documents
    ]
    indexed_count = await use_case.execute(documents)
    return IndexNewsResponse(indexed_count=indexed_count, collection_name=settings.collection_name)
```

For search, build `SearchQuery`, call `SearchNews`, and map results to `SearchNewsResponse`.

Register `RetrievalUnavailableError` as `503` and domain validation errors as `422`.

- [ ] **Step 4: Run API/runtime tests and commit**

Run:

```bash
uv run pytest apps/retrieval-service/tests/test_api.py apps/retrieval-service/tests/test_container.py -v
uv run ruff check apps/retrieval-service/src/retrieval_service/main apps/retrieval-service/src/retrieval_service/presentation apps/retrieval-service/tests/test_api.py apps/retrieval-service/tests/test_container.py
uv run ty check apps/retrieval-service/src/retrieval_service/main apps/retrieval-service/src/retrieval_service/presentation apps/retrieval-service/tests/test_api.py apps/retrieval-service/tests/test_container.py
```

Expected: pass.

Commit:

```bash
git add apps/retrieval-service/src/retrieval_service/main apps/retrieval-service/src/retrieval_service/presentation apps/retrieval-service/tests/test_api.py apps/retrieval-service/tests/test_container.py
git commit -m "feat: добавить api retrieval service"
```

## Task 5: Docker Compose and Final Verification

**Files:**
- Create: `deploy/docker/retrieval-service.Dockerfile`
- Modify: `deploy/compose.yaml`

- [ ] **Step 1: Add Dockerfile**

Create `deploy/docker/retrieval-service.Dockerfile`:

```dockerfile
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv==0.11.8

COPY pyproject.toml uv.lock ./
COPY packages/framework ./packages/framework
COPY packages/contracts ./packages/contracts
COPY apps/retrieval-service ./apps/retrieval-service

RUN uv sync --frozen --package economic-news-retrieval-service --no-dev

CMD [".venv/bin/granian", "retrieval_service.main.app:app", "--interface", "asgi", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Update compose**

Add service to `deploy/compose.yaml`:

```yaml
  retrieval-service:
    build:
      context: ..
      dockerfile: deploy/docker/retrieval-service.Dockerfile
    env_file:
      - ../.env.example
    environment:
      RETRIEVAL_QDRANT_URL: "http://qdrant:6333"
    ports:
      - "8002:8000"
    depends_on:
      - qdrant
```

- [ ] **Step 3: Run full verification**

Run:

```bash
uv run ruff check apps packages research
uv run ty check apps packages research
uv run pytest packages apps research/tests -v -W error
docker compose -f deploy/compose.yaml config
docker compose -f deploy/compose.yaml build retrieval-service
```

Expected: all commands pass. If Docker daemon is unavailable, report exact error and keep Python checks as the merge gate.

- [ ] **Step 4: Commit deploy wiring**

Commit:

```bash
git add deploy/docker/retrieval-service.Dockerfile deploy/compose.yaml
git commit -m "chore: добавить запуск retrieval service"
```

## Completion

- Push branch:

```bash
git push -u origin feature/retrieval-service
```

- Open PR to `dev`:

```bash
gh pr create --base dev --head feature/retrieval-service --title "feat: добавить retrieval service" --body "Добавляет отдельный retrieval-service для индексации и семантического поиска экономических новостей через FastEmbed и Qdrant."
```
