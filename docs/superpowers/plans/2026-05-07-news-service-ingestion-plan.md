# News Service Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a lean `news-service` that loads local economic-news CSV data, normalizes it, previews it over HTTP, and indexes it through `retrieval-service`.

**Architecture:** Add a new DDD/layered microservice under `apps/news-service`, mirroring existing backend services. Contracts live in `packages/contracts`; domain/application stay independent from FastAPI and Zapros; infrastructure owns CSV reading and retrieval-service transport. This slice stays synchronous and local-file based, intentionally excluding PostgreSQL, Redis, Taskiq and FastStream.

**Tech Stack:** Python 3.13, FastAPI, Granian, Dishka, Zapros, Pydantic contracts, stdlib `csv`, Docker Compose, pytest, ruff, ty.

---

## File Structure

- Modify `packages/contracts/src/economic_news_contracts/news.py`
  - New external API contracts for `news-service`.
- Modify `packages/contracts/src/economic_news_contracts/__init__.py`
  - Export module only if existing package pattern requires it.
- Modify `packages/contracts/tests/test_contracts.py`
  - Contract tests for preview/index DTOs.
- Create `apps/news-service/pyproject.toml`
  - Workspace package definition.
- Create `apps/news-service/src/news_service/...`
  - Standard layered service layout.
- Create `apps/news-service/tests/...`
  - Domain, use case, infrastructure, API, container tests.
- Modify `pyproject.toml`
  - Add `apps/news-service` to workspace members and `tool.uv.sources`.
- Modify `deploy/compose.yaml`
  - Add `news-service`.
- Create `deploy/docker/news-service.Dockerfile`
  - Slim Granian runtime.
- Modify `.env.example`
  - Add `NEWS_SERVICE_*` settings.
- Modify `README.md`
  - Add local news ingestion demo commands.

---

### Task 1: News API Contracts

**Files:**
- Create: `packages/contracts/src/economic_news_contracts/news.py`
- Modify: `packages/contracts/tests/test_contracts.py`

- [ ] **Step 1: Write failing contract tests**

Append imports to `packages/contracts/tests/test_contracts.py`:

```python
from economic_news_contracts.news import (
    IndexNewsDatasetRequest,
    IndexNewsDatasetResponse,
    NewsDocumentResponse,
    PreviewNewsResponse,
)
```

Append tests:

```python
def test_news_document_response_trims_required_fields() -> None:
    document = NewsDocumentResponse(
        id=" news-1 ",
        title=" GDP grows ",
        text=" GDP grew by 2 percent. ",
        source=" demo ",
        metadata={"impact": "positive"},
    )

    assert document.id == "news-1"
    assert document.title == "GDP grows"
    assert document.text == "GDP grew by 2 percent."
    assert document.source == "demo"
    assert document.published_at is None
    assert document.metadata == {"impact": "positive"}


def test_news_document_response_rejects_empty_required_fields() -> None:
    with pytest.raises(ValueError):
        NewsDocumentResponse(id="news-1", title=" ", text="text", source="demo")


def test_preview_news_response_reports_documents_and_total_count() -> None:
    response = PreviewNewsResponse(
        documents=[
            NewsDocumentResponse(
                id="news-1",
                title="GDP grows",
                text="GDP grew by 2 percent.",
                source="demo",
            ),
        ],
        total_count=3,
    )

    assert response.model_dump(mode="json") == {
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
        "total_count": 3,
    }


def test_index_news_dataset_request_defaults_and_bounds() -> None:
    assert IndexNewsDatasetRequest().limit == 100

    with pytest.raises(ValueError):
        IndexNewsDatasetRequest(limit=0)

    with pytest.raises(ValueError):
        IndexNewsDatasetRequest(limit=1001)


def test_index_news_dataset_response_serializes_counts() -> None:
    response = IndexNewsDatasetResponse(
        loaded_count=2,
        indexed_count=2,
        collection_name="economic_news",
    )

    assert response.model_dump(mode="json") == {
        "loaded_count": 2,
        "indexed_count": 2,
        "collection_name": "economic_news",
    }
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run pytest packages/contracts/tests/test_contracts.py -v -W error
```

Expected: fail with `ModuleNotFoundError: No module named 'economic_news_contracts.news'`.

- [ ] **Step 3: Implement news contracts**

Create `packages/contracts/src/economic_news_contracts/news.py`:

```python
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NewsDocumentResponse(BaseModel):
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


class PreviewNewsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documents: list[NewsDocumentResponse]
    total_count: int = Field(ge=0)


class IndexNewsDatasetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=100, ge=1, le=1000)


class IndexNewsDatasetResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loaded_count: int = Field(ge=0)
    indexed_count: int = Field(ge=0)
    collection_name: str = Field(min_length=1)

    @field_validator("collection_name")
    @classmethod
    def normalize_collection_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must not be empty")
        return normalized
```

- [ ] **Step 4: Run contract tests**

Run:

```bash
uv run pytest packages/contracts/tests/test_contracts.py -v -W error
```

Expected: all contract tests pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add packages/contracts/src/economic_news_contracts/news.py packages/contracts/tests/test_contracts.py
git commit -m "feat: добавить контракты news service"
```

---

### Task 2: News Domain and Use Cases

**Files:**
- Create: `apps/news-service/pyproject.toml`
- Create: `apps/news-service/src/news_service/__init__.py`
- Create: `apps/news-service/src/news_service/domain/__init__.py`
- Create: `apps/news-service/src/news_service/domain/errors.py`
- Create: `apps/news-service/src/news_service/domain/model.py`
- Create: `apps/news-service/src/news_service/application/__init__.py`
- Create: `apps/news-service/src/news_service/application/ports.py`
- Create: `apps/news-service/src/news_service/application/use_cases.py`
- Create: `apps/news-service/tests/test_news_domain.py`
- Create: `apps/news-service/tests/test_news_use_cases.py`

- [ ] **Step 1: Create package skeleton**

Create `apps/news-service/pyproject.toml`:

```toml
[project]
name = "economic-news-news-service"
version = "0.1.0"
description = "News ingestion service for economic news dialog system"
requires-python = ">=3.12"
dependencies = [
  "economic-news-framework",
  "economic-news-contracts",
  "fastapi>=0.115",
  "granian>=1.7",
  "dishka>=1.4",
  "pydantic-settings>=2.6",
  "structlog>=24.4",
  "zapros>=0.10",
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
packages = ["src/news_service"]

[tool.uv.sources]
economic-news-framework = { workspace = true }
economic-news-contracts = { workspace = true }
```

Create empty `__init__.py` files:

```bash
mkdir -p apps/news-service/src/news_service/{application,domain,infrastructure,main,presentation,workers}
touch apps/news-service/src/news_service/__init__.py
touch apps/news-service/src/news_service/application/__init__.py
touch apps/news-service/src/news_service/domain/__init__.py
touch apps/news-service/src/news_service/infrastructure/__init__.py
touch apps/news-service/src/news_service/main/__init__.py
touch apps/news-service/src/news_service/presentation/__init__.py
touch apps/news-service/src/news_service/workers/__init__.py
```

- [ ] **Step 2: Write failing domain tests**

Create `apps/news-service/tests/test_news_domain.py`:

```python
from datetime import UTC, datetime

import pytest
from news_service.domain.errors import EmptyNewsFieldError
from news_service.domain.model import NewsDocument, stable_news_id


def test_news_document_trims_required_fields_and_copies_metadata() -> None:
    published_at = datetime(2026, 5, 7, 9, 30, tzinfo=UTC)
    metadata = {"impact": "positive"}
    document = NewsDocument(
        id=" news-1 ",
        title=" GDP grows ",
        text=" GDP grew by 2 percent. ",
        source=" demo ",
        published_at=published_at,
        metadata=metadata,
    )
    metadata["impact"] = "mutated"

    assert document.id == "news-1"
    assert document.title == "GDP grows"
    assert document.text == "GDP grew by 2 percent."
    assert document.source == "demo"
    assert document.published_at == published_at
    assert document.metadata == {"impact": "positive"}


def test_news_document_rejects_empty_required_fields() -> None:
    with pytest.raises(EmptyNewsFieldError, match="title must not be empty"):
        NewsDocument(id="news-1", title=" ", text="text", source="demo")


def test_stable_news_id_is_deterministic_and_source_sensitive() -> None:
    first = stable_news_id(source="demo", title="GDP grows", text="GDP grew")
    second = stable_news_id(source="demo", title=" GDP grows ", text="GDP grew")
    different = stable_news_id(source="another", title="GDP grows", text="GDP grew")

    assert first == second
    assert first.startswith("news-")
    assert first != different
```

- [ ] **Step 3: Write failing use-case tests**

Create `apps/news-service/tests/test_news_use_cases.py`:

```python
import pytest
from economic_news_contracts.retrieval import IndexNewsResponse
from news_service.application.use_cases import IndexNewsDataset, PreviewNews
from news_service.domain.model import NewsDocument


class FakeNewsSource:
    def __init__(self) -> None:
        self.limit: int | None = None

    async def load(self, limit: int | None = None) -> list[NewsDocument]:
        self.limit = limit
        return [
            NewsDocument(
                id="news-1",
                title="GDP grows",
                text="GDP grew by 2 percent.",
                source="demo",
            ),
            NewsDocument(
                id="news-2",
                title="Inflation slows",
                text="Inflation slowed in April.",
                source="demo",
            ),
        ]


class FakeRetrievalIndexer:
    def __init__(self) -> None:
        self.documents: list[NewsDocument] = []

    async def index(self, documents: list[NewsDocument]) -> IndexNewsResponse:
        self.documents = documents
        return IndexNewsResponse(
            indexed_count=len(documents),
            collection_name="economic_news",
        )


@pytest.mark.asyncio
async def test_preview_news_loads_documents_and_reports_total_count() -> None:
    source = FakeNewsSource()
    use_case = PreviewNews(source)

    documents, total_count = await use_case.execute(limit=1)

    assert source.limit is None
    assert [document.id for document in documents] == ["news-1"]
    assert total_count == 2


@pytest.mark.asyncio
async def test_index_news_dataset_loads_limited_documents_and_indexes_them() -> None:
    source = FakeNewsSource()
    indexer = FakeRetrievalIndexer()
    use_case = IndexNewsDataset(source, indexer)

    result = await use_case.execute(limit=1)

    assert source.limit == 1
    assert [document.id for document in indexer.documents] == ["news-1"]
    assert result.loaded_count == 1
    assert result.indexed_count == 1
    assert result.collection_name == "economic_news"
```

- [ ] **Step 4: Run tests and verify they fail**

Run:

```bash
uv run pytest apps/news-service/tests/test_news_domain.py apps/news-service/tests/test_news_use_cases.py -v -W error
```

Expected: fail with import errors for `news_service`.

- [ ] **Step 5: Implement domain errors and model**

Create `apps/news-service/src/news_service/domain/errors.py`:

```python
class NewsDomainError(Exception):
    """Base class for news-service domain errors."""


class EmptyNewsFieldError(NewsDomainError, ValueError):
    """Raised when required news field is empty."""


class NewsSourceUnavailableError(Exception):
    """Raised when configured news source cannot be loaded."""


class NewsSourceValidationError(ValueError):
    """Raised when configured news source has invalid shape or rows."""


class RetrievalIndexUnavailableError(Exception):
    """Raised when retrieval-service indexing is unavailable."""
```

Create `apps/news-service/src/news_service/domain/model.py`:

```python
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from types import MappingProxyType
from typing import Any

from news_service.domain.errors import EmptyNewsFieldError


def _required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise EmptyNewsFieldError(f"{field_name} must not be empty")
    return normalized


def stable_news_id(*, source: str, title: str, text: str) -> str:
    normalized = "\n".join(
        (
            source.strip().casefold(),
            title.strip().casefold(),
            text.strip(),
        ),
    )
    digest = sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"news-{digest}"


@dataclass(frozen=True, slots=True)
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
```

- [ ] **Step 6: Implement application ports and use cases**

Create `apps/news-service/src/news_service/application/ports.py`:

```python
from typing import Protocol

from economic_news_contracts.retrieval import IndexNewsResponse
from news_service.domain.model import NewsDocument


class NewsSource(Protocol):
    async def load(self, limit: int | None = None) -> list[NewsDocument]:
        """Load normalized news documents."""


class RetrievalIndexer(Protocol):
    async def index(self, documents: list[NewsDocument]) -> IndexNewsResponse:
        """Index normalized news documents through retrieval-service."""
```

Create `apps/news-service/src/news_service/application/use_cases.py`:

```python
from economic_news_contracts.news import IndexNewsDatasetResponse

from news_service.application.ports import NewsSource, RetrievalIndexer
from news_service.domain.model import NewsDocument


class PreviewNews:
    def __init__(self, source: NewsSource) -> None:
        self._source = source

    async def execute(self, limit: int) -> tuple[list[NewsDocument], int]:
        documents = await self._source.load()
        return documents[:limit], len(documents)


class IndexNewsDataset:
    def __init__(self, source: NewsSource, indexer: RetrievalIndexer) -> None:
        self._source = source
        self._indexer = indexer

    async def execute(self, limit: int) -> IndexNewsDatasetResponse:
        documents = await self._source.load(limit=limit)
        index_response = await self._indexer.index(documents)
        return IndexNewsDatasetResponse(
            loaded_count=len(documents),
            indexed_count=index_response.indexed_count,
            collection_name=index_response.collection_name,
        )
```

- [ ] **Step 7: Run task tests**

Run:

```bash
uv run pytest apps/news-service/tests/test_news_domain.py apps/news-service/tests/test_news_use_cases.py -v -W error
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

Run:

```bash
git add apps/news-service
git commit -m "feat: добавить домен news service"
```

---

### Task 3: CSV News Source

**Files:**
- Create: `apps/news-service/src/news_service/infrastructure/csv_news_source.py`
- Create: `apps/news-service/tests/test_csv_news_source.py`

- [ ] **Step 1: Write failing CSV adapter tests**

Create `apps/news-service/tests/test_csv_news_source.py`:

```python
from pathlib import Path

import pytest
from news_service.domain.errors import NewsSourceUnavailableError, NewsSourceValidationError
from news_service.infrastructure.csv_news_source import CsvNewsSource


def write_csv(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


@pytest.mark.asyncio
async def test_csv_news_source_reads_alias_columns_and_metadata(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path / "news.csv",
        "article_id,headline,body,publisher,date,impact\n"
        "a-1,GDP grows,GDP grew by 2 percent,demo,2026-05-07T09:30:00Z,positive\n",
    )
    source = CsvNewsSource(csv_path)

    documents = await source.load()

    assert len(documents) == 1
    assert documents[0].id == "a-1"
    assert documents[0].title == "GDP grows"
    assert documents[0].text == "GDP grew by 2 percent"
    assert documents[0].source == "demo"
    assert documents[0].published_at is not None
    assert documents[0].metadata == {"row_number": 2, "impact": "positive"}


@pytest.mark.asyncio
async def test_csv_news_source_generates_stable_id_when_id_is_missing(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path / "news.csv",
        "title,text,source\nGDP grows,GDP grew,demo\n",
    )
    source = CsvNewsSource(csv_path)

    first = await source.load()
    second = await source.load()

    assert first[0].id == second[0].id
    assert first[0].id.startswith("news-")


@pytest.mark.asyncio
async def test_csv_news_source_applies_limit(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path / "news.csv",
        "title,text,source\nA,Text A,demo\nB,Text B,demo\n",
    )
    source = CsvNewsSource(csv_path)

    documents = await source.load(limit=1)

    assert [document.title for document in documents] == ["A"]


@pytest.mark.asyncio
async def test_csv_news_source_rejects_missing_required_columns(tmp_path: Path) -> None:
    csv_path = write_csv(tmp_path / "news.csv", "title,source\nGDP grows,demo\n")
    source = CsvNewsSource(csv_path)

    with pytest.raises(NewsSourceValidationError, match="Missing required CSV column: text"):
        await source.load()


@pytest.mark.asyncio
async def test_csv_news_source_rejects_empty_required_row_value(tmp_path: Path) -> None:
    csv_path = write_csv(tmp_path / "news.csv", "title,text,source\nGDP grows, ,demo\n")
    source = CsvNewsSource(csv_path)

    with pytest.raises(NewsSourceValidationError, match="row 2"):
        await source.load()


@pytest.mark.asyncio
async def test_csv_news_source_maps_missing_file_to_unavailable_error(tmp_path: Path) -> None:
    source = CsvNewsSource(tmp_path / "missing.csv")

    with pytest.raises(NewsSourceUnavailableError, match="news source is unavailable"):
        await source.load()
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run pytest apps/news-service/tests/test_csv_news_source.py -v -W error
```

Expected: fail with `ModuleNotFoundError` for `news_service.infrastructure.csv_news_source`.

- [ ] **Step 3: Implement CSV adapter**

Create `apps/news-service/src/news_service/infrastructure/csv_news_source.py`:

```python
import csv
from datetime import datetime
from pathlib import Path

from news_service.domain.errors import NewsSourceUnavailableError, NewsSourceValidationError
from news_service.domain.model import NewsDocument, stable_news_id

_TITLE_COLUMNS = ("title", "headline")
_TEXT_COLUMNS = ("text", "content", "body", "description")
_SOURCE_COLUMNS = ("source", "publisher")
_ID_COLUMNS = ("id", "news_id", "article_id")
_PUBLISHED_COLUMNS = ("published_at", "date", "published")
_CORE_COLUMNS = {*_TITLE_COLUMNS, *_TEXT_COLUMNS, *_SOURCE_COLUMNS, *_ID_COLUMNS, *_PUBLISHED_COLUMNS}


class CsvNewsSource:
    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    async def load(self, limit: int | None = None) -> list[NewsDocument]:
        try:
            return self._load_sync(limit)
        except NewsSourceValidationError:
            raise
        except FileNotFoundError as error:
            raise NewsSourceUnavailableError("news source is unavailable") from error
        except OSError as error:
            raise NewsSourceUnavailableError("news source is unavailable") from error

    def _load_sync(self, limit: int | None) -> list[NewsDocument]:
        with self._path.open(encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            fieldnames = {name.strip() for name in (reader.fieldnames or []) if name}
            title_column = self._required_column(fieldnames, _TITLE_COLUMNS, "title")
            text_column = self._required_column(fieldnames, _TEXT_COLUMNS, "text")
            source_column = self._required_column(fieldnames, _SOURCE_COLUMNS, "source")
            id_column = self._optional_column(fieldnames, _ID_COLUMNS)
            published_column = self._optional_column(fieldnames, _PUBLISHED_COLUMNS)

            documents: list[NewsDocument] = []
            for row_number, row in enumerate(reader, start=2):
                document = self._document_from_row(
                    row=row,
                    row_number=row_number,
                    title_column=title_column,
                    text_column=text_column,
                    source_column=source_column,
                    id_column=id_column,
                    published_column=published_column,
                )
                documents.append(document)
                if limit is not None and len(documents) >= limit:
                    break
            return documents

    def _document_from_row(
        self,
        *,
        row: dict[str, str | None],
        row_number: int,
        title_column: str,
        text_column: str,
        source_column: str,
        id_column: str | None,
        published_column: str | None,
    ) -> NewsDocument:
        title = self._required_value(row, title_column, row_number)
        text = self._required_value(row, text_column, row_number)
        source = self._required_value(row, source_column, row_number)
        raw_id = self._optional_value(row, id_column)
        document_id = raw_id or stable_news_id(source=source, title=title, text=text)
        published_at = self._parse_published_at(self._optional_value(row, published_column), row_number)
        metadata = {
            key: value.strip()
            for key, value in row.items()
            if key is not None
            and key.strip() not in _CORE_COLUMNS
            and value is not None
            and value.strip()
        }
        metadata["row_number"] = row_number
        try:
            return NewsDocument(
                id=document_id,
                title=title,
                text=text,
                source=source,
                published_at=published_at,
                metadata=metadata,
            )
        except ValueError as error:
            raise NewsSourceValidationError(f"Invalid CSV row {row_number}") from error

    def _required_column(
        self,
        fieldnames: set[str],
        aliases: tuple[str, ...],
        semantic_name: str,
    ) -> str:
        column = self._optional_column(fieldnames, aliases)
        if column is None:
            raise NewsSourceValidationError(f"Missing required CSV column: {semantic_name}")
        return column

    def _optional_column(self, fieldnames: set[str], aliases: tuple[str, ...]) -> str | None:
        for alias in aliases:
            if alias in fieldnames:
                return alias
        return None

    def _required_value(self, row: dict[str, str | None], column: str, row_number: int) -> str:
        value = row.get(column)
        if value is None or not value.strip():
            raise NewsSourceValidationError(f"Missing required value in row {row_number}: {column}")
        return value.strip()

    def _optional_value(self, row: dict[str, str | None], column: str | None) -> str | None:
        if column is None:
            return None
        value = row.get(column)
        if value is None or not value.strip():
            return None
        return value.strip()

    def _parse_published_at(self, value: str | None, row_number: int) -> datetime | None:
        if value is None:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise NewsSourceValidationError(f"Invalid published_at in row {row_number}") from error
```

- [ ] **Step 4: Run CSV tests**

Run:

```bash
uv run pytest apps/news-service/tests/test_csv_news_source.py -v -W error
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add apps/news-service/src/news_service/infrastructure/csv_news_source.py apps/news-service/tests/test_csv_news_source.py
git commit -m "feat: добавить csv источник новостей"
```

---

### Task 4: Retrieval Indexer Client

**Files:**
- Create: `apps/news-service/src/news_service/infrastructure/retrieval_client.py`
- Create: `apps/news-service/tests/test_retrieval_indexer.py`

- [ ] **Step 1: Write failing retrieval indexer tests**

Create `apps/news-service/tests/test_retrieval_indexer.py`:

```python
import pytest
from news_service.domain.errors import RetrievalIndexUnavailableError
from news_service.domain.model import NewsDocument
from news_service.infrastructure.retrieval_client import ZaprosRetrievalIndexer


class FakeResponse:
    def __init__(self, status: int, json: object) -> None:
        self.status = status
        self.json = json


class FakeZaprosClient:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def post(self, url: str, json: dict[str, object]) -> FakeResponse:
        self.calls.append((url, json))
        return self.response


class RaisingZaprosClient:
    async def post(self, url: str, json: dict[str, object]) -> FakeResponse:
        raise OSError("connection refused")


@pytest.mark.asyncio
async def test_zapros_retrieval_indexer_sends_index_payload() -> None:
    transport = FakeZaprosClient(
        FakeResponse(200, {"indexed_count": 1, "collection_name": "economic_news"}),
    )
    indexer = ZaprosRetrievalIndexer(
        base_url="http://retrieval-service:8000/",
        timeout_seconds=5.0,
        client=transport,
    )

    response = await indexer.index(
        [
            NewsDocument(
                id="news-1",
                title="GDP grows",
                text="GDP grew by 2 percent.",
                source="demo",
                metadata={"impact": "positive"},
            ),
        ],
    )

    assert response.indexed_count == 1
    assert response.collection_name == "economic_news"
    assert transport.calls == [
        (
            "http://retrieval-service:8000/api/v1/index",
            {
                "documents": [
                    {
                        "id": "news-1",
                        "title": "GDP grows",
                        "text": "GDP grew by 2 percent.",
                        "source": "demo",
                        "published_at": None,
                        "metadata": {"impact": "positive"},
                    },
                ],
            },
        ),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        FakeResponse(503, {"detail": "down"}),
        FakeResponse(200, {"indexed_count": -1, "collection_name": "economic_news"}),
    ],
)
async def test_zapros_retrieval_indexer_maps_bad_responses(response: FakeResponse) -> None:
    indexer = ZaprosRetrievalIndexer(
        base_url="http://retrieval-service:8000",
        timeout_seconds=5.0,
        client=FakeZaprosClient(response),
    )

    with pytest.raises(RetrievalIndexUnavailableError, match="retrieval-service is unavailable"):
        await indexer.index([NewsDocument(id="news-1", title="GDP", text="Text", source="demo")])


@pytest.mark.asyncio
async def test_zapros_retrieval_indexer_maps_transport_error() -> None:
    indexer = ZaprosRetrievalIndexer(
        base_url="http://retrieval-service:8000",
        timeout_seconds=5.0,
        client=RaisingZaprosClient(),
    )

    with pytest.raises(RetrievalIndexUnavailableError, match="retrieval-service is unavailable"):
        await indexer.index([NewsDocument(id="news-1", title="GDP", text="Text", source="demo")])
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run pytest apps/news-service/tests/test_retrieval_indexer.py -v -W error
```

Expected: fail with `ModuleNotFoundError` for `news_service.infrastructure.retrieval_client`.

- [ ] **Step 3: Implement Zapros retrieval indexer**

Create `apps/news-service/src/news_service/infrastructure/retrieval_client.py`:

```python
from collections.abc import Callable
from typing import Any

from economic_news_contracts.retrieval import (
    IndexNewsRequest,
    IndexNewsResponse,
    NewsDocumentPayload,
)
from news_service.domain.errors import RetrievalIndexUnavailableError
from news_service.domain.model import NewsDocument
from zapros import AsyncClient, AsyncStdNetworkHandler


def _make_zapros_client(timeout_seconds: float) -> AsyncClient:
    return AsyncClient(handler=AsyncStdNetworkHandler(total_timeout=timeout_seconds))


class ZaprosRetrievalIndexer:
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

    async def index(self, documents: list[NewsDocument]) -> IndexNewsResponse:
        request = IndexNewsRequest(
            documents=[
                NewsDocumentPayload(
                    id=document.id,
                    title=document.title,
                    text=document.text,
                    source=document.source,
                    published_at=document.published_at,
                    metadata=dict(document.metadata),
                )
                for document in documents
            ],
        )
        response = await self._post(request.model_dump(mode="json"))
        if response.status >= 400:
            raise RetrievalIndexUnavailableError("retrieval-service is unavailable")
        try:
            return IndexNewsResponse.model_validate(response.json)
        except Exception as error:
            raise RetrievalIndexUnavailableError("retrieval-service is unavailable") from error

    async def _post(self, payload: dict[str, Any]) -> Any:
        url = f"{self._base_url}/api/v1/index"
        try:
            if self._client is not None:
                return await self._client.post(url, json=payload)
            async with self._client_factory(self._timeout_seconds) as client:
                return await client.post(url, json=payload)
        except RetrievalIndexUnavailableError:
            raise
        except Exception as error:
            raise RetrievalIndexUnavailableError("retrieval-service is unavailable") from error
```

- [ ] **Step 4: Run retrieval indexer tests**

Run:

```bash
uv run pytest apps/news-service/tests/test_retrieval_indexer.py -v -W error
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add apps/news-service/src/news_service/infrastructure/retrieval_client.py apps/news-service/tests/test_retrieval_indexer.py
git commit -m "feat: добавить retrieval indexer client"
```

---

### Task 5: News Service API, Settings and DI

**Files:**
- Create: `apps/news-service/src/news_service/main/settings.py`
- Create: `apps/news-service/src/news_service/main/container.py`
- Create: `apps/news-service/src/news_service/main/app.py`
- Create: `apps/news-service/src/news_service/presentation/router.py`
- Create: `apps/news-service/src/news_service/presentation/errors.py`
- Create: `apps/news-service/tests/test_news_api.py`
- Create: `apps/news-service/tests/test_news_container.py`

- [ ] **Step 1: Write failing API tests**

Create `apps/news-service/tests/test_news_api.py`:

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider, setup_dishka
from economic_news_contracts.news import IndexNewsDatasetResponse
from economic_news_framework.apps import create_service_app
from fastapi.testclient import TestClient
from news_service.application.use_cases import IndexNewsDataset, PreviewNews
from news_service.domain.errors import NewsSourceUnavailableError, NewsSourceValidationError
from news_service.domain.model import NewsDocument
from news_service.presentation.errors import register_error_handlers
from news_service.presentation.router import router


class StubPreviewNews(PreviewNews):
    def __init__(self, error: Exception | None = None) -> None:
        self.limit: int | None = None
        self._error = error

    async def execute(self, limit: int) -> tuple[list[NewsDocument], int]:
        self.limit = limit
        if self._error is not None:
            raise self._error
        return (
            [
                NewsDocument(
                    id="news-1",
                    title="GDP grows",
                    text="GDP grew by 2 percent.",
                    source="demo",
                    metadata={"impact": "positive"},
                ),
            ],
            3,
        )


class StubIndexNewsDataset(IndexNewsDataset):
    def __init__(self, error: Exception | None = None) -> None:
        self.limit: int | None = None
        self._error = error

    async def execute(self, limit: int) -> IndexNewsDatasetResponse:
        self.limit = limit
        if self._error is not None:
            raise self._error
        return IndexNewsDatasetResponse(
            loaded_count=1,
            indexed_count=1,
            collection_name="economic_news",
        )


class NewsProvider(Provider):
    def __init__(self, preview: PreviewNews, index: IndexNewsDataset) -> None:
        super().__init__()
        self._preview = preview
        self._index = index

    @provide(scope=Scope.APP)
    def preview_news(self) -> PreviewNews:
        return self._preview

    @provide(scope=Scope.APP)
    def index_news_dataset(self) -> IndexNewsDataset:
        return self._index


def make_client(preview: PreviewNews, index: IndexNewsDataset) -> TestClient:
    app = create_service_app(service_name="news-service", routers=(router,), log_level="INFO")
    register_error_handlers(app)
    container = make_async_container(NewsProvider(preview, index), FastapiProvider())
    setup_dishka(container=container, app=app)

    @asynccontextmanager
    async def close_container(_: object) -> AsyncIterator[None]:
        yield
        await container.close()

    app.router.lifespan_context = close_container
    return TestClient(app)


def test_preview_endpoint_returns_documents() -> None:
    preview = StubPreviewNews()

    with make_client(preview, StubIndexNewsDataset()) as client:
        response = client.get("/api/v1/news/preview?limit=1")

    assert response.status_code == 200
    assert preview.limit == 1
    assert response.json() == {
        "documents": [
            {
                "id": "news-1",
                "title": "GDP grows",
                "text": "GDP grew by 2 percent.",
                "source": "demo",
                "published_at": None,
                "metadata": {"impact": "positive"},
            },
        ],
        "total_count": 3,
    }


def test_index_endpoint_indexes_dataset() -> None:
    index = StubIndexNewsDataset()

    with make_client(StubPreviewNews(), index) as client:
        response = client.post("/api/v1/news/index", json={"limit": 5})

    assert response.status_code == 200
    assert index.limit == 5
    assert response.json() == {
        "loaded_count": 1,
        "indexed_count": 1,
        "collection_name": "economic_news",
    }


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (NewsSourceValidationError("Missing required CSV column: text"), 422, "Invalid news source data"),
        (NewsSourceUnavailableError("secret path /tmp/news.csv"), 503, "news source is unavailable"),
    ],
)
def test_news_endpoint_maps_source_errors(error: Exception, status_code: int, detail: str) -> None:
    with make_client(StubPreviewNews(error), StubIndexNewsDataset()) as client:
        response = client.get("/api/v1/news/preview")

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
```

- [ ] **Step 2: Write failing container tests**

Create `apps/news-service/tests/test_news_container.py`:

```python
from pathlib import Path

import pytest
from dishka import AsyncContainer
from news_service.application.use_cases import IndexNewsDataset, PreviewNews
from news_service.main.container import create_container
from news_service.main.settings import NewsServiceSettings


def test_news_settings_defaults_and_env_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NEWS_SERVICE_NEWS_DATASET_PATH", raising=False)
    settings = NewsServiceSettings()

    assert settings.service_name == "news-service"
    assert settings.news_dataset_path == Path("data/raw/economic_news.csv")
    assert str(settings.retrieval_service_url) == "http://retrieval-service:8000/"
    assert settings.default_index_limit == 100


def test_news_settings_reads_prefixed_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEWS_SERVICE_NEWS_DATASET_PATH", "data/raw/demo.csv")
    monkeypatch.setenv("NEWS_SERVICE_RETRIEVAL_SERVICE_URL", "http://localhost:8002")
    monkeypatch.setenv("NEWS_SERVICE_DEFAULT_INDEX_LIMIT", "25")

    settings = NewsServiceSettings()

    assert settings.news_dataset_path == Path("data/raw/demo.csv")
    assert str(settings.retrieval_service_url) == "http://localhost:8002/"
    assert settings.default_index_limit == 25


@pytest.mark.asyncio
async def test_container_resolves_use_cases_with_fake_components() -> None:
    container: AsyncContainer = create_container(use_fake_components=True)
    try:
        async with container() as request_container:
            preview = await request_container.get(PreviewNews)
            index = await request_container.get(IndexNewsDataset)
    finally:
        await container.close()

    assert isinstance(preview, PreviewNews)
    assert isinstance(index, IndexNewsDataset)
```

- [ ] **Step 3: Run tests and verify they fail**

Run:

```bash
uv run pytest apps/news-service/tests/test_news_api.py apps/news-service/tests/test_news_container.py -v -W error
```

Expected: fail with import errors for `news_service.main` and `news_service.presentation`.

- [ ] **Step 4: Implement settings**

Create `apps/news-service/src/news_service/main/settings.py`:

```python
from pathlib import Path

from economic_news_framework.settings import BaseServiceSettings
from pydantic import Field, HttpUrl
from pydantic_settings import SettingsConfigDict


class NewsServiceSettings(BaseServiceSettings):
    model_config = SettingsConfigDict(
        env_prefix="NEWS_SERVICE_",
        env_file=".env",
        extra="ignore",
    )

    service_name: str = "news-service"
    news_dataset_path: Path = Path("data/raw/economic_news.csv")
    retrieval_service_url: HttpUrl = Field(default="http://retrieval-service:8000")
    retrieval_service_timeout_seconds: float = Field(default=10.0, gt=0)
    default_index_limit: int = Field(default=100, ge=1, le=1000)
```

- [ ] **Step 5: Implement presentation errors and router**

Create `apps/news-service/src/news_service/presentation/errors.py`:

```python
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from news_service.domain.errors import (
    NewsSourceUnavailableError,
    NewsSourceValidationError,
    RetrievalIndexUnavailableError,
)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NewsSourceValidationError)
    async def handle_validation_error(
        _: Request,
        __: NewsSourceValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Invalid news source data"},
        )

    @app.exception_handler(NewsSourceUnavailableError)
    async def handle_source_unavailable(
        _: Request,
        __: NewsSourceUnavailableError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "news source is unavailable"},
        )

    @app.exception_handler(RetrievalIndexUnavailableError)
    async def handle_retrieval_unavailable(
        _: Request,
        __: RetrievalIndexUnavailableError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "retrieval-service is unavailable"},
        )
```

Create `apps/news-service/src/news_service/presentation/router.py`:

```python
from dishka.integrations.fastapi import FromDishka, inject
from economic_news_contracts.news import (
    IndexNewsDatasetRequest,
    IndexNewsDatasetResponse,
    NewsDocumentResponse,
    PreviewNewsResponse,
)
from fastapi import APIRouter, Query
from news_service.application.use_cases import IndexNewsDataset, PreviewNews
from news_service.main.settings import NewsServiceSettings

router = APIRouter(prefix="/api/v1/news")


@router.get("/preview")
@inject
async def preview_news(
    use_case: FromDishka[PreviewNews],
    limit: int = Query(default=10, ge=1, le=100),
) -> PreviewNewsResponse:
    documents, total_count = await use_case.execute(limit=limit)
    return PreviewNewsResponse(
        documents=[
            NewsDocumentResponse(
                id=document.id,
                title=document.title,
                text=document.text,
                source=document.source,
                published_at=document.published_at,
                metadata=dict(document.metadata),
            )
            for document in documents
        ],
        total_count=total_count,
    )


@router.post("/index")
@inject
async def index_news(
    request: IndexNewsDatasetRequest,
    use_case: FromDishka[IndexNewsDataset],
    settings: FromDishka[NewsServiceSettings],
) -> IndexNewsDatasetResponse:
    return await use_case.execute(limit=request.limit or settings.default_index_limit)
```

- [ ] **Step 6: Implement container and app**

Create `apps/news-service/src/news_service/main/container.py`:

```python
from pathlib import Path
from typing import Any

from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider
from economic_news_contracts.retrieval import IndexNewsResponse
from news_service.application.ports import NewsSource, RetrievalIndexer
from news_service.application.use_cases import IndexNewsDataset, PreviewNews
from news_service.domain.model import NewsDocument
from news_service.infrastructure.csv_news_source import CsvNewsSource
from news_service.infrastructure.retrieval_client import ZaprosRetrievalIndexer
from news_service.main.settings import NewsServiceSettings


class FakeNewsSource:
    async def load(self, limit: int | None = None) -> list[NewsDocument]:
        documents = [
            NewsDocument(
                id="news-1",
                title="GDP grows",
                text="GDP grew by 2 percent.",
                source="demo",
            ),
        ]
        if limit is None:
            return documents
        return documents[:limit]


class FakeRetrievalIndexer:
    async def index(self, documents: list[NewsDocument]) -> IndexNewsResponse:
        return IndexNewsResponse(indexed_count=len(documents), collection_name="economic_news")


class NewsServiceProvider(Provider):
    def __init__(
        self,
        settings: NewsServiceSettings | None = None,
        *,
        use_fake_components: bool = False,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._use_fake_components = use_fake_components

    @provide(scope=Scope.APP)
    def settings(self) -> NewsServiceSettings:
        return self._settings or NewsServiceSettings()

    @provide(scope=Scope.APP, provides=NewsSource)
    def news_source(self, settings: NewsServiceSettings) -> NewsSource:
        if self._use_fake_components:
            return FakeNewsSource()
        return CsvNewsSource(Path(settings.news_dataset_path))

    @provide(scope=Scope.APP, provides=RetrievalIndexer)
    def retrieval_indexer(self, settings: NewsServiceSettings) -> RetrievalIndexer:
        if self._use_fake_components:
            return FakeRetrievalIndexer()
        return ZaprosRetrievalIndexer(
            base_url=str(settings.retrieval_service_url),
            timeout_seconds=settings.retrieval_service_timeout_seconds,
        )

    @provide(scope=Scope.APP)
    def preview_news(self, source: NewsSource) -> PreviewNews:
        return PreviewNews(source)

    @provide(scope=Scope.APP)
    def index_news_dataset(
        self,
        source: NewsSource,
        indexer: RetrievalIndexer,
    ) -> IndexNewsDataset:
        return IndexNewsDataset(source, indexer)


def create_container(
    settings: NewsServiceSettings | None = None,
    *,
    use_fake_components: bool = False,
) -> Any:
    return make_async_container(
        NewsServiceProvider(settings, use_fake_components=use_fake_components),
        FastapiProvider(),
    )
```

Create `apps/news-service/src/news_service/main/app.py`:

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dishka.integrations.fastapi import setup_dishka
from economic_news_framework.apps import create_service_app
from fastapi import FastAPI
from news_service.main.container import create_container
from news_service.main.settings import NewsServiceSettings
from news_service.presentation.errors import register_error_handlers
from news_service.presentation.router import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await app.state.dishka_container.close()


def create_app(*, use_fake_components: bool = False) -> FastAPI:
    settings = NewsServiceSettings()
    container = create_container(settings, use_fake_components=use_fake_components)
    app = create_service_app(
        service_name=settings.service_name,
        routers=(router,),
        log_level=settings.log_level,
    )
    app.router.lifespan_context = lifespan
    setup_dishka(container=container, app=app)
    register_error_handlers(app)
    return app


app = create_app()
```

- [ ] **Step 7: Run API and container tests**

Run:

```bash
uv run pytest apps/news-service/tests/test_news_api.py apps/news-service/tests/test_news_container.py -v -W error
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

Run:

```bash
git add apps/news-service/src/news_service/main apps/news-service/src/news_service/presentation apps/news-service/tests/test_news_api.py apps/news-service/tests/test_news_container.py
git commit -m "feat: добавить api news service"
```

---

### Task 6: Workspace, Compose, README and Final Verification

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `.env.example`
- Modify: `deploy/compose.yaml`
- Create: `deploy/docker/news-service.Dockerfile`
- Modify: `README.md`

- [ ] **Step 1: Add news-service to workspace**

Modify root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = [
  "packages/framework",
  "packages/contracts",
  "apps/api-gateway",
  "apps/analysis-service",
  "apps/dialog-service",
  "apps/retrieval-service",
  "apps/news-service",
  "research",
]
```

Add source:

```toml
economic-news-news-service = { workspace = true }
```

Run:

```bash
uv lock
uv sync --all-packages
```

Expected: lock and sync succeed.

- [ ] **Step 2: Add compose and Dockerfile**

Create `deploy/docker/news-service.Dockerfile`:

```dockerfile
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv==0.11.8

COPY pyproject.toml uv.lock ./
COPY packages/framework ./packages/framework
COPY packages/contracts ./packages/contracts
COPY apps/news-service ./apps/news-service

RUN uv sync --frozen --package economic-news-news-service --no-dev

CMD [".venv/bin/granian", "news_service.main.app:app", "--interface", "asgi", "--host", "0.0.0.0", "--port", "8000"]
```

Modify `deploy/compose.yaml` by adding service:

```yaml
  news-service:
    build:
      context: ..
      dockerfile: deploy/docker/news-service.Dockerfile
    env_file:
      - ../.env.example
    environment:
      NEWS_SERVICE_RETRIEVAL_SERVICE_URL: "http://retrieval-service:8000"
      NEWS_SERVICE_NEWS_DATASET_PATH: "${NEWS_SERVICE_NEWS_DATASET_PATH:-data/raw/economic_news.csv}"
    ports:
      - "8004:8000"
    volumes:
      - ../data:/app/data:ro
    depends_on:
      - retrieval-service
```

Modify `.env.example`:

```env
NEWS_SERVICE_NEWS_DATASET_PATH=data/raw/economic_news.csv
NEWS_SERVICE_RETRIEVAL_SERVICE_URL=http://localhost:8002
NEWS_SERVICE_RETRIEVAL_SERVICE_TIMEOUT_SECONDS=10.0
NEWS_SERVICE_DEFAULT_INDEX_LIMIT=100
```

- [ ] **Step 3: Update README**

Add a section:

````markdown
## News Service ingestion

`news-service` loads local CSV news and indexes them through `retrieval-service`.

Expected CSV semantic columns:

- title: `title` or `headline`
- text: `text`, `content`, `body` or `description`
- source: `source` or `publisher`

Local preview:

```bash
NEWS_SERVICE_NEWS_DATASET_PATH=research/tests/fixtures/news_impact_sample.csv \
  uv run --package economic-news-news-service granian news_service.main.app:app \
  --interface asgi --host 0.0.0.0 --port 8004

curl 'http://localhost:8004/api/v1/news/preview?limit=3'
```

Index through retrieval-service:

```bash
curl -X POST http://localhost:8004/api/v1/news/index \
  -H 'Content-Type: application/json' \
  -d '{"limit": 10}'
```
````

- [ ] **Step 4: Run all checks**

Run:

```bash
uv run ruff check apps packages research
uv run ty check apps packages research
uv run pytest packages apps research/tests -v -W error
docker compose -f deploy/compose.yaml config
```

Expected: all pass.

- [ ] **Step 5: Run Docker build if daemon is available**

Run:

```bash
docker compose -f deploy/compose.yaml build news-service
```

Expected: image builds successfully. If Docker daemon is not running, record the daemon error and continue without claiming Docker build passed.

- [ ] **Step 6: Commit**

Run:

```bash
git add pyproject.toml uv.lock .env.example deploy/compose.yaml deploy/docker/news-service.Dockerfile README.md
git commit -m "chore: подключить news service к workspace"
```

- [ ] **Step 7: Final branch review**

Request a final code review for `origin/dev..HEAD` with this checklist:

- contracts are stable and forbid extra fields;
- CSV adapter supports aliases and rejects invalid required data;
- generated ids are deterministic;
- no local absolute paths leak through API errors;
- `news-service` indexes through existing retrieval contract;
- API/DI/compose wiring follow existing service patterns;
- no PostgreSQL, Redis, Taskiq, FastStream, UI or scraping was added.

Expected: reviewer returns `PASS` or only non-blocking comments.

---

## Plan Self-Review

Spec coverage:

- New `apps/news-service` package: Tasks 2, 5 and 6.
- CSV local adapter and semantic column aliases: Task 3.
- Stable ids and row validation: Tasks 2 and 3.
- Preview and index endpoints: Task 5.
- Zapros client to retrieval-service: Task 4.
- Contracts: Task 1.
- Docker Compose and Dockerfile: Task 6.
- README demo: Task 6.
- PostgreSQL/Redis/Taskiq/FastStream/UI/scraping excluded: no task adds them.

Placeholder scan:

- No deferred-work markers or vague test steps remain.

Type consistency:

- Domain model is `NewsDocument`.
- Source protocol is `NewsSource.load(limit: int | None)`.
- Indexer protocol is `RetrievalIndexer.index(documents: list[NewsDocument])`.
- External API response model is `NewsDocumentResponse`.
- Index request/response models are `IndexNewsDatasetRequest` and `IndexNewsDatasetResponse`.
