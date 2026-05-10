# Dataset Upload And Training Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a demonstrable workflow where users upload a CSV dataset, preview/index the active dataset, train multiple impact classifiers, compare metrics, and run the app with trained artifacts.

**Architecture:** Keep training outside production services. `news-service` owns local dataset upload/activation, `frontend-web` exposes upload/status controls, `research` and `tools/prepare_dataset.py` own dataset conversion/training wrappers, and `analysis-service` only consumes joblib artifacts.

**Tech Stack:** FastAPI, Dishka, Pydantic, Python stdlib CSV/pathlib/json, React/Vitest, existing research package with pandas/scikit-learn/MLflow, Docker Compose, Justfile.

---

## File Map

- Create `apps/news-service/src/news_service/domain/dataset.py` for uploaded dataset value objects.
- Modify `apps/news-service/src/news_service/application/ports.py` to add `DatasetStorage`.
- Modify `apps/news-service/src/news_service/application/use_cases.py` to add dataset upload/list/activate/get-active use cases and active-source resolution.
- Create `apps/news-service/src/news_service/infrastructure/local_dataset_storage.py` for local upload persistence.
- Modify `apps/news-service/src/news_service/main/settings.py` for upload paths and max file size.
- Modify `apps/news-service/src/news_service/main/container.py` to wire `DatasetStorage` and active CSV source.
- Modify `packages/contracts/src/economic_news_contracts/news.py` for dataset upload/list DTOs.
- Modify `apps/news-service/src/news_service/presentation/router.py` to add upload/list/activate/active endpoints.
- Modify `apps/news-service/src/news_service/presentation/errors.py` if `413` mapping needs explicit support.
- Add/modify tests in `apps/news-service/tests/`.
- Modify `frontend/web/src/app/types.ts`, `frontend/web/src/api/news.ts`, `frontend/web/src/api/news.test.ts`.
- Create `frontend/web/src/components/DatasetUpload.tsx`.
- Modify `frontend/web/src/components/ControlsPanel.tsx`, `frontend/web/src/app/App.tsx`, `frontend/web/src/app/App.test.tsx`, and CSS.
- Create `tools/prepare_dataset.py` plus tests under `tests/` or `research/tests/`.
- Modify `justfile`, `.env.example`, `deploy/compose.yaml`, `docs/demo.md`, `docs/deployment/model-modes-and-large-datasets.md`, and final coursework docs.
- Modify `apps/analysis-service/src/analysis_service/infrastructure/classifiers.py` and tests for confidence metadata.

## Task 1: Backend Dataset Upload Domain And Storage

**Files:**
- Create: `apps/news-service/src/news_service/domain/dataset.py`
- Modify: `apps/news-service/src/news_service/application/ports.py`
- Create: `apps/news-service/src/news_service/infrastructure/local_dataset_storage.py`
- Test: `apps/news-service/tests/test_local_dataset_storage.py`

- [ ] **Step 1: Write storage tests**

Create `apps/news-service/tests/test_local_dataset_storage.py`:

```python
from pathlib import Path

import pytest
from news_service.domain.errors import NewsSourceValidationError
from news_service.infrastructure.local_dataset_storage import LocalDatasetStorage


CSV_BYTES = b"id,title,text,source,published_at\nn1,GDP grows,GDP grew,demo,2026-05-07T09:30:00Z\n"


@pytest.mark.asyncio
async def test_storage_saves_upload_with_stable_dataset_id(tmp_path: Path) -> None:
    storage = LocalDatasetStorage(
        upload_dir=tmp_path / "uploads",
        active_dataset_file=tmp_path / "uploads" / "active_dataset.json",
        max_upload_bytes=1024,
    )

    dataset = await storage.save_upload(filename="news.csv", content=CSV_BYTES)

    assert dataset.dataset_id == "news"
    assert dataset.filename == "news.csv"
    assert dataset.path == tmp_path / "uploads" / "news.csv"
    assert dataset.size_bytes == len(CSV_BYTES)
    assert dataset.path.read_bytes() == CSV_BYTES


@pytest.mark.asyncio
async def test_storage_rejects_non_csv_upload(tmp_path: Path) -> None:
    storage = LocalDatasetStorage(
        upload_dir=tmp_path / "uploads",
        active_dataset_file=tmp_path / "uploads" / "active_dataset.json",
        max_upload_bytes=1024,
    )

    with pytest.raises(NewsSourceValidationError, match="Only CSV uploads are supported"):
        await storage.save_upload(filename="news.txt", content=CSV_BYTES)


@pytest.mark.asyncio
async def test_storage_rejects_too_large_upload(tmp_path: Path) -> None:
    storage = LocalDatasetStorage(
        upload_dir=tmp_path / "uploads",
        active_dataset_file=tmp_path / "uploads" / "active_dataset.json",
        max_upload_bytes=4,
    )

    with pytest.raises(NewsSourceValidationError, match="Dataset upload is too large"):
        await storage.save_upload(filename="news.csv", content=CSV_BYTES)


@pytest.mark.asyncio
async def test_storage_activates_and_returns_active_dataset(tmp_path: Path) -> None:
    storage = LocalDatasetStorage(
        upload_dir=tmp_path / "uploads",
        active_dataset_file=tmp_path / "uploads" / "active_dataset.json",
        max_upload_bytes=1024,
    )
    uploaded = await storage.save_upload(filename="news.csv", content=CSV_BYTES)

    active = await storage.activate(uploaded.dataset_id)

    assert active.dataset_id == uploaded.dataset_id
    assert active.path == uploaded.path
    assert await storage.get_active_path() == uploaded.path
    assert (await storage.get_active()).dataset_id == uploaded.dataset_id


@pytest.mark.asyncio
async def test_storage_lists_uploaded_datasets(tmp_path: Path) -> None:
    storage = LocalDatasetStorage(
        upload_dir=tmp_path / "uploads",
        active_dataset_file=tmp_path / "uploads" / "active_dataset.json",
        max_upload_bytes=1024,
    )
    await storage.save_upload(filename="b.csv", content=CSV_BYTES)
    await storage.save_upload(filename="a.csv", content=CSV_BYTES)

    datasets = await storage.list_datasets()

    assert [dataset.filename for dataset in datasets] == ["a.csv", "b.csv"]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest apps/news-service/tests/test_local_dataset_storage.py -v
```

Expected: FAIL because `LocalDatasetStorage` does not exist.

- [ ] **Step 3: Add domain dataset models**

Create `apps/news-service/src/news_service/domain/dataset.py`:

```python
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class UploadedDataset:
    dataset_id: str
    filename: str
    path: Path
    size_bytes: int
    uploaded_at: datetime


@dataclass(frozen=True, slots=True)
class ActiveDataset:
    dataset_id: str
    filename: str
    path: Path
    activated_at: datetime


def utc_now() -> datetime:
    return datetime.now(tz=UTC)
```

- [ ] **Step 4: Add DatasetStorage protocol**

Modify `apps/news-service/src/news_service/application/ports.py`:

```python
from pathlib import Path
from typing import Protocol

from news_service.domain.dataset import ActiveDataset, UploadedDataset
from news_service.domain.model import NewsDocument


class NewsSource(Protocol):
    async def load(self, limit: int | None = None) -> list[NewsDocument]:
        raise NotImplementedError


class RetrievalIndexer(Protocol):
    async def index(self, documents: list[NewsDocument]) -> object:
        raise NotImplementedError


class NewsIndexTaskQueue(Protocol):
    async def enqueue(self, limit: int) -> str:
        raise NotImplementedError


class DatasetStorage(Protocol):
    async def save_upload(self, *, filename: str, content: bytes) -> UploadedDataset:
        raise NotImplementedError

    async def list_datasets(self) -> list[UploadedDataset]:
        raise NotImplementedError

    async def activate(self, dataset_id: str) -> ActiveDataset:
        raise NotImplementedError

    async def get_active(self) -> ActiveDataset | None:
        raise NotImplementedError

    async def get_active_path(self) -> Path | None:
        raise NotImplementedError
```

If the existing file contains the three old protocols, preserve imports and only append `DatasetStorage`.

- [ ] **Step 5: Implement LocalDatasetStorage**

Create `apps/news-service/src/news_service/infrastructure/local_dataset_storage.py`:

```python
import json
import re
from datetime import datetime
from pathlib import Path

from news_service.domain.dataset import ActiveDataset, UploadedDataset, utc_now
from news_service.domain.errors import NewsSourceValidationError

_SAFE_ID_PATTERN = re.compile(r"[^a-zA-Z0-9_.-]+")


class LocalDatasetStorage:
    def __init__(
        self,
        *,
        upload_dir: Path,
        active_dataset_file: Path,
        max_upload_bytes: int,
    ) -> None:
        self._upload_dir = upload_dir
        self._active_dataset_file = active_dataset_file
        self._max_upload_bytes = max_upload_bytes

    async def save_upload(self, *, filename: str, content: bytes) -> UploadedDataset:
        clean_name = self._clean_filename(filename)
        if not clean_name.lower().endswith(".csv"):
            raise NewsSourceValidationError("Only CSV uploads are supported")
        if len(content) > self._max_upload_bytes:
            raise NewsSourceValidationError("Dataset upload is too large")

        self._upload_dir.mkdir(parents=True, exist_ok=True)
        dataset_id = self._dataset_id_from_filename(clean_name)
        path = self._upload_dir / f"{dataset_id}.csv"
        path.write_bytes(content)
        return UploadedDataset(
            dataset_id=dataset_id,
            filename=clean_name,
            path=path,
            size_bytes=len(content),
            uploaded_at=utc_now(),
        )

    async def list_datasets(self) -> list[UploadedDataset]:
        if not self._upload_dir.exists():
            return []
        datasets: list[UploadedDataset] = []
        for path in sorted(self._upload_dir.glob("*.csv")):
            stat = path.stat()
            datasets.append(
                UploadedDataset(
                    dataset_id=path.stem,
                    filename=path.name,
                    path=path,
                    size_bytes=stat.st_size,
                    uploaded_at=datetime.fromtimestamp(stat.st_mtime).astimezone(),
                ),
            )
        return datasets

    async def activate(self, dataset_id: str) -> ActiveDataset:
        dataset = await self._find_dataset(dataset_id)
        active = ActiveDataset(
            dataset_id=dataset.dataset_id,
            filename=dataset.filename,
            path=dataset.path,
            activated_at=utc_now(),
        )
        self._active_dataset_file.parent.mkdir(parents=True, exist_ok=True)
        self._active_dataset_file.write_text(
            json.dumps(
                {
                    "dataset_id": active.dataset_id,
                    "filename": active.filename,
                    "path": str(active.path),
                    "activated_at": active.activated_at.isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return active

    async def get_active(self) -> ActiveDataset | None:
        if not self._active_dataset_file.exists():
            return None
        try:
            data = json.loads(self._active_dataset_file.read_text(encoding="utf-8"))
            path = Path(str(data["path"]))
            if not path.exists():
                return None
            return ActiveDataset(
                dataset_id=str(data["dataset_id"]),
                filename=str(data["filename"]),
                path=path,
                activated_at=datetime.fromisoformat(str(data["activated_at"])),
            )
        except (KeyError, ValueError, TypeError, json.JSONDecodeError):
            return None

    async def get_active_path(self) -> Path | None:
        active = await self.get_active()
        return None if active is None else active.path

    async def _find_dataset(self, dataset_id: str) -> UploadedDataset:
        normalized = self._dataset_id_from_filename(dataset_id)
        for dataset in await self.list_datasets():
            if dataset.dataset_id == normalized:
                return dataset
        raise NewsSourceValidationError("Uploaded dataset does not exist")

    def _clean_filename(self, filename: str) -> str:
        clean_name = Path(filename).name.strip()
        if not clean_name:
            raise NewsSourceValidationError("Dataset filename must not be empty")
        return clean_name

    def _dataset_id_from_filename(self, filename: str) -> str:
        stem = Path(filename).stem.strip() or "dataset"
        dataset_id = _SAFE_ID_PATTERN.sub("-", stem).strip(".-")
        return dataset_id or "dataset"
```

- [ ] **Step 6: Run storage tests**

Run:

```bash
uv run pytest apps/news-service/tests/test_local_dataset_storage.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/news-service/src/news_service/domain/dataset.py apps/news-service/src/news_service/application/ports.py apps/news-service/src/news_service/infrastructure/local_dataset_storage.py apps/news-service/tests/test_local_dataset_storage.py
git commit -m "feat: добавить хранилище загруженных датасетов"
```

## Task 2: Backend Upload API And Active Dataset Source

**Files:**
- Modify: `packages/contracts/src/economic_news_contracts/news.py`
- Modify: `apps/news-service/src/news_service/application/use_cases.py`
- Modify: `apps/news-service/src/news_service/main/settings.py`
- Modify: `apps/news-service/src/news_service/main/container.py`
- Modify: `apps/news-service/src/news_service/presentation/router.py`
- Test: `apps/news-service/tests/test_news_api.py`
- Test: `apps/news-service/tests/test_news_use_cases.py`

- [ ] **Step 1: Add failing API tests**

Append to `apps/news-service/tests/test_news_api.py`:

```python
from news_service.application.use_cases import (
    ActivateNewsDataset,
    GetActiveNewsDataset,
    ListNewsDatasets,
    UploadNewsDataset,
)
from news_service.domain.dataset import ActiveDataset, UploadedDataset
from pathlib import Path
from datetime import UTC, datetime


class StubUploadNewsDataset(UploadNewsDataset):
    def __init__(self) -> None:
        self.filename: str | None = None
        self.content: bytes | None = None

    async def execute(self, *, filename: str, content: bytes) -> UploadedDataset:
        self.filename = filename
        self.content = content
        return UploadedDataset(
            dataset_id="news",
            filename=filename,
            path=Path("data/uploads/news.csv"),
            size_bytes=len(content),
            uploaded_at=datetime(2026, 5, 8, tzinfo=UTC),
        )


class StubListNewsDatasets(ListNewsDatasets):
    async def execute(self) -> list[UploadedDataset]:
        return [
            UploadedDataset(
                dataset_id="news",
                filename="news.csv",
                path=Path("data/uploads/news.csv"),
                size_bytes=42,
                uploaded_at=datetime(2026, 5, 8, tzinfo=UTC),
            ),
        ]


class StubActivateNewsDataset(ActivateNewsDataset):
    def __init__(self) -> None:
        self.dataset_id: str | None = None

    async def execute(self, dataset_id: str) -> ActiveDataset:
        self.dataset_id = dataset_id
        return ActiveDataset(
            dataset_id=dataset_id,
            filename="news.csv",
            path=Path("data/uploads/news.csv"),
            activated_at=datetime(2026, 5, 8, tzinfo=UTC),
        )


class StubGetActiveNewsDataset(GetActiveNewsDataset):
    async def execute(self) -> ActiveDataset | None:
        return ActiveDataset(
            dataset_id="news",
            filename="news.csv",
            path=Path("data/uploads/news.csv"),
            activated_at=datetime(2026, 5, 8, tzinfo=UTC),
        )
```

Then extend the test provider constructor and providers to include these four use cases. If keeping the existing constructor too awkward, create a second `make_dataset_client(...)` helper with a provider that supplies all existing and dataset use cases.

Add tests:

```python
def test_upload_dataset_endpoint_accepts_csv() -> None:
    upload = StubUploadNewsDataset()

    with make_dataset_client(upload=upload) as client:
        response = client.post(
            "/api/v1/news/datasets/upload",
            files={"file": ("news.csv", b"title,text,source\nA,B,C\n", "text/csv")},
        )

    assert response.status_code == 201
    assert upload.filename == "news.csv"
    assert upload.content == b"title,text,source\nA,B,C\n"
    assert response.json()["dataset_id"] == "news"


def test_list_datasets_endpoint_returns_uploads() -> None:
    with make_dataset_client() as client:
        response = client.get("/api/v1/news/datasets")

    assert response.status_code == 200
    assert response.json()["datasets"][0]["filename"] == "news.csv"


def test_activate_dataset_endpoint_returns_active_dataset() -> None:
    activate = StubActivateNewsDataset()

    with make_dataset_client(activate=activate) as client:
        response = client.post("/api/v1/news/datasets/news/activate")

    assert response.status_code == 200
    assert activate.dataset_id == "news"
    assert response.json()["dataset_id"] == "news"


def test_get_active_dataset_endpoint_returns_active_dataset() -> None:
    with make_dataset_client() as client:
        response = client.get("/api/v1/news/datasets/active")

    assert response.status_code == 200
    assert response.json()["filename"] == "news.csv"
```

- [ ] **Step 2: Run API tests to verify failure**

Run:

```bash
uv run pytest apps/news-service/tests/test_news_api.py -v
```

Expected: FAIL because contracts/use cases/routes do not exist.

- [ ] **Step 3: Add news dataset contracts**

Modify `packages/contracts/src/economic_news_contracts/news.py`:

```python
class UploadedDatasetResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
    uploaded_at: datetime


class DatasetListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    datasets: list[UploadedDatasetResponse]


class ActiveDatasetResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    activated_at: datetime
```

- [ ] **Step 4: Add dataset use cases**

Append to `apps/news-service/src/news_service/application/use_cases.py`:

```python
from news_service.application.ports import DatasetStorage
from news_service.domain.dataset import ActiveDataset, UploadedDataset


class UploadNewsDataset:
    def __init__(self, storage: DatasetStorage) -> None:
        self._storage = storage

    async def execute(self, *, filename: str, content: bytes) -> UploadedDataset:
        return await self._storage.save_upload(filename=filename, content=content)


class ListNewsDatasets:
    def __init__(self, storage: DatasetStorage) -> None:
        self._storage = storage

    async def execute(self) -> list[UploadedDataset]:
        return await self._storage.list_datasets()


class ActivateNewsDataset:
    def __init__(self, storage: DatasetStorage) -> None:
        self._storage = storage

    async def execute(self, dataset_id: str) -> ActiveDataset:
        return await self._storage.activate(dataset_id)


class GetActiveNewsDataset:
    def __init__(self, storage: DatasetStorage) -> None:
        self._storage = storage

    async def execute(self) -> ActiveDataset | None:
        return await self._storage.get_active()
```

- [ ] **Step 5: Add settings**

Modify `apps/news-service/src/news_service/main/settings.py`:

```python
    dataset_upload_dir: Path = Path("data/uploads")
    active_dataset_file: Path = Path("data/uploads/active_dataset.json")
    upload_max_bytes: int = Field(default=50 * 1024 * 1024, ge=1)
```

- [ ] **Step 6: Wire container and active source**

Modify `apps/news-service/src/news_service/main/container.py`:

```python
from news_service.application.ports import DatasetStorage
from news_service.infrastructure.local_dataset_storage import LocalDatasetStorage


class ActiveDatasetCsvNewsSource:
    def __init__(self, storage: DatasetStorage, fallback_path: Path) -> None:
        self._storage = storage
        self._fallback_path = fallback_path

    async def load(self, limit: int | None = None) -> list[NewsDocument]:
        active_path = await self._storage.get_active_path()
        return await CsvNewsSource(active_path or self._fallback_path).load(limit=limit)
```

Update providers:

```python
    @provide(scope=Scope.APP, provides=DatasetStorage)
    def dataset_storage(self, settings: NewsServiceSettings) -> DatasetStorage:
        return LocalDatasetStorage(
            upload_dir=Path(settings.dataset_upload_dir),
            active_dataset_file=Path(settings.active_dataset_file),
            max_upload_bytes=settings.upload_max_bytes,
        )

    @provide(scope=Scope.APP, provides=NewsSource)
    def news_source(self, settings: NewsServiceSettings, storage: DatasetStorage) -> NewsSource:
        if self._use_fake_components:
            return FakeNewsSource()
        return ActiveDatasetCsvNewsSource(storage, Path(settings.news_dataset_path))
```

Add providers for the four dataset use cases.

- [ ] **Step 7: Add routes**

Modify `apps/news-service/src/news_service/presentation/router.py`:

```python
from fastapi import APIRouter, File, UploadFile, status
from economic_news_contracts.news import (
    ActiveDatasetResponse,
    DatasetListResponse,
    UploadedDatasetResponse,
)
```

Add helpers:

```python
def _uploaded_dataset_response(dataset: UploadedDataset) -> UploadedDatasetResponse:
    return UploadedDatasetResponse(
        dataset_id=dataset.dataset_id,
        filename=dataset.filename,
        size_bytes=dataset.size_bytes,
        uploaded_at=dataset.uploaded_at,
    )


def _active_dataset_response(dataset: ActiveDataset) -> ActiveDatasetResponse:
    return ActiveDatasetResponse(
        dataset_id=dataset.dataset_id,
        filename=dataset.filename,
        activated_at=dataset.activated_at,
    )
```

Add endpoints:

```python
@router.post("/datasets/upload", status_code=status.HTTP_201_CREATED)
@inject
async def upload_dataset(
    use_case: FromDishka[UploadNewsDataset],
    file: UploadFile = File(...),
) -> UploadedDatasetResponse:
    content = await file.read()
    dataset = await use_case.execute(filename=file.filename or "dataset.csv", content=content)
    return _uploaded_dataset_response(dataset)


@router.get("/datasets")
@inject
async def list_datasets(use_case: FromDishka[ListNewsDatasets]) -> DatasetListResponse:
    datasets = await use_case.execute()
    return DatasetListResponse(datasets=[_uploaded_dataset_response(dataset) for dataset in datasets])


@router.post("/datasets/{dataset_id}/activate")
@inject
async def activate_dataset(
    dataset_id: str,
    use_case: FromDishka[ActivateNewsDataset],
) -> ActiveDatasetResponse:
    return _active_dataset_response(await use_case.execute(dataset_id))


@router.get("/datasets/active")
@inject
async def get_active_dataset(use_case: FromDishka[GetActiveNewsDataset]) -> ActiveDatasetResponse | None:
    active = await use_case.execute()
    return None if active is None else _active_dataset_response(active)
```

- [ ] **Step 8: Run API tests**

Run:

```bash
uv run pytest apps/news-service/tests/test_news_api.py apps/news-service/tests/test_news_use_cases.py -v
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add packages/contracts/src/economic_news_contracts/news.py apps/news-service/src/news_service apps/news-service/tests
git commit -m "feat: добавить api загрузки датасетов"
```

## Task 3: Frontend Dataset Upload UI

**Files:**
- Modify: `frontend/web/src/app/types.ts`
- Modify: `frontend/web/src/api/news.ts`
- Modify: `frontend/web/src/api/news.test.ts`
- Create: `frontend/web/src/components/DatasetUpload.tsx`
- Modify: `frontend/web/src/components/ControlsPanel.tsx`
- Modify: `frontend/web/src/app/App.tsx`
- Modify: `frontend/web/src/app/App.test.tsx`
- Modify: `frontend/web/src/app/App.module.css`

- [ ] **Step 1: Add failing API client tests**

Append to `frontend/web/src/api/news.test.ts`:

```typescript
import { activateDataset, getActiveDataset, listDatasets, uploadDataset } from "./news";

it("uploads a CSV dataset", async () => {
  const fetchMock = vi.fn().mockResolvedValue(
    Response.json({
      dataset_id: "news",
      filename: "news.csv",
      size_bytes: 42,
      uploaded_at: "2026-05-08T00:00:00Z",
    }),
  );
  const file = new File(["title,text,source\nA,B,C\n"], "news.csv", { type: "text/csv" });

  const response = await uploadDataset(file, { baseUrl: "http://localhost:8004", fetcher: fetchMock });

  expect(fetchMock).toHaveBeenCalledWith(
    "http://localhost:8004/api/v1/news/datasets/upload",
    expect.objectContaining({ method: "POST", body: expect.any(FormData) }),
  );
  expect(response.dataset_id).toBe("news");
});

it("lists uploaded datasets", async () => {
  const fetchMock = vi.fn().mockResolvedValue(Response.json({ datasets: [] }));

  const response = await listDatasets({ baseUrl: "http://localhost:8004", fetcher: fetchMock });

  expect(fetchMock).toHaveBeenCalledWith("http://localhost:8004/api/v1/news/datasets");
  expect(response.datasets).toEqual([]);
});

it("activates uploaded dataset", async () => {
  const fetchMock = vi.fn().mockResolvedValue(
    Response.json({
      dataset_id: "news",
      filename: "news.csv",
      activated_at: "2026-05-08T00:00:00Z",
    }),
  );

  const response = await activateDataset("news", { baseUrl: "http://localhost:8004", fetcher: fetchMock });

  expect(fetchMock).toHaveBeenCalledWith("http://localhost:8004/api/v1/news/datasets/news/activate", {
    method: "POST",
  });
  expect(response.filename).toBe("news.csv");
});

it("loads active dataset", async () => {
  const fetchMock = vi.fn().mockResolvedValue(Response.json(null));

  const response = await getActiveDataset({ baseUrl: "http://localhost:8004", fetcher: fetchMock });

  expect(fetchMock).toHaveBeenCalledWith("http://localhost:8004/api/v1/news/datasets/active");
  expect(response).toBeNull();
});
```

- [ ] **Step 2: Run frontend API tests to verify failure**

Run:

```bash
npm --prefix frontend/web test -- --run src/api/news.test.ts
```

Expected: FAIL because new functions do not exist.

- [ ] **Step 3: Add types and API functions**

Modify `frontend/web/src/app/types.ts`:

```typescript
export type UploadedDataset = {
  dataset_id: string;
  filename: string;
  size_bytes: number;
  uploaded_at: string;
};

export type DatasetListResponse = {
  datasets: UploadedDataset[];
};

export type ActiveDataset = {
  dataset_id: string;
  filename: string;
  activated_at: string;
};
```

Modify `frontend/web/src/api/news.ts`:

```typescript
import type {
  ActiveDataset,
  DatasetListResponse,
  IndexNewsDatasetResponse,
  PreviewNewsResponse,
  UploadedDataset,
} from "../app/types";

export async function uploadDataset(file: File, options: ApiOptions = {}): Promise<UploadedDataset> {
  const fetcher = options.fetcher ?? fetch;
  const formData = new FormData();
  formData.append("file", file);

  let response: Response;
  try {
    response = await fetcher(`${normalizeBaseUrl(options.baseUrl ?? NEWS_SERVICE_URL)}/api/v1/news/datasets/upload`, {
      method: "POST",
      body: formData,
    });
  } catch {
    throw connectionError();
  }

  if (!response.ok) {
    throw await errorFromResponse(response, "Не удалось загрузить CSV");
  }

  return (await response.json()) as UploadedDataset;
}

export async function listDatasets(options: ApiOptions = {}): Promise<DatasetListResponse> {
  const fetcher = options.fetcher ?? fetch;
  const response = await fetcher(`${normalizeBaseUrl(options.baseUrl ?? NEWS_SERVICE_URL)}/api/v1/news/datasets`);
  if (!response.ok) {
    throw await errorFromResponse(response, "Не удалось получить список датасетов");
  }
  return (await response.json()) as DatasetListResponse;
}

export async function activateDataset(datasetId: string, options: ApiOptions = {}): Promise<ActiveDataset> {
  const fetcher = options.fetcher ?? fetch;
  const response = await fetcher(
    `${normalizeBaseUrl(options.baseUrl ?? NEWS_SERVICE_URL)}/api/v1/news/datasets/${datasetId}/activate`,
    { method: "POST" },
  );
  if (!response.ok) {
    throw await errorFromResponse(response, "Не удалось выбрать датасет");
  }
  return (await response.json()) as ActiveDataset;
}

export async function getActiveDataset(options: ApiOptions = {}): Promise<ActiveDataset | null> {
  const fetcher = options.fetcher ?? fetch;
  const response = await fetcher(`${normalizeBaseUrl(options.baseUrl ?? NEWS_SERVICE_URL)}/api/v1/news/datasets/active`);
  if (!response.ok) {
    throw await errorFromResponse(response, "Не удалось получить активный датасет");
  }
  return (await response.json()) as ActiveDataset | null;
}
```

Keep existing `previewNews` and `indexNewsDataset`.

- [ ] **Step 4: Add DatasetUpload component**

Create `frontend/web/src/components/DatasetUpload.tsx`:

```tsx
import type { ActiveDataset, UploadedDataset } from "../app/types";

type DatasetUploadProps = {
  datasets: UploadedDataset[];
  activeDataset: ActiveDataset | null;
  isUploading: boolean;
  onUpload: (file: File) => void;
  onActivate: (datasetId: string) => void;
};

export function DatasetUpload({
  datasets,
  activeDataset,
  isUploading,
  onUpload,
  onActivate,
}: DatasetUploadProps) {
  return (
    <section className="datasetUpload" aria-label="Датасет новостей">
      <label>
        <span>CSV датасет</span>
        <input
          aria-label="CSV датасет"
          type="file"
          accept=".csv,text/csv"
          disabled={isUploading}
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) {
              onUpload(file);
              event.target.value = "";
            }
          }}
        />
      </label>
      <p>{activeDataset ? `Активен: ${activeDataset.filename}` : "Активен demo CSV"}</p>
      {datasets.length > 0 ? (
        <label>
          <span>Загруженные</span>
          <select
            aria-label="Загруженные датасеты"
            value={activeDataset?.dataset_id ?? ""}
            onChange={(event) => {
              if (event.target.value) {
                onActivate(event.target.value);
              }
            }}
          >
            <option value="">demo CSV</option>
            {datasets.map((dataset) => (
              <option key={dataset.dataset_id} value={dataset.dataset_id}>
                {dataset.filename}
              </option>
            ))}
          </select>
        </label>
      ) : null}
    </section>
  );
}
```

- [ ] **Step 5: Wire App and ControlsPanel**

Modify `ControlsPanel` props to accept `datasetUploadSlot: React.ReactNode`, render it before action buttons.

Modify `App.tsx`:

```tsx
import { activateDataset, getActiveDataset, indexNewsDataset, listDatasets, previewNews, uploadDataset } from "../api/news";
import { DatasetUpload } from "../components/DatasetUpload";
```

Add state:

```tsx
const [datasets, setDatasets] = useState<UploadedDataset[]>([]);
const [activeDataset, setActiveDataset] = useState<ActiveDataset | null>(null);
const [isUploading, setUploading] = useState(false);
```

Add handlers:

```tsx
async function refreshDatasets() {
  setDatasets((await listDatasets()).datasets);
  setActiveDataset(await getActiveDataset());
}

async function handleUploadDataset(file: File) {
  setUploading(true);
  setError(null);
  try {
    const uploaded = await uploadDataset(file);
    const active = await activateDataset(uploaded.dataset_id);
    setActiveDataset(active);
    setDatasets((await listDatasets()).datasets);
  } catch (uploadError) {
    setError(messageFromError(uploadError));
  } finally {
    setUploading(false);
  }
}

async function handleActivateDataset(datasetId: string) {
  setError(null);
  try {
    setActiveDataset(await activateDataset(datasetId));
  } catch (activateError) {
    setError(messageFromError(activateError));
  }
}
```

Use `useEffect` to call `refreshDatasets()` on mount. Pass a `DatasetUpload` slot into `ControlsPanel`.

- [ ] **Step 6: Add App tests**

Modify `frontend/web/src/app/App.test.tsx` mock fetch to handle dataset endpoints. Add:

```typescript
it("uploads a CSV dataset and displays it as active", async () => {
  const fetchMock = mockFetch();
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();

  render(<App />);

  await user.upload(
    screen.getByLabelText("CSV датасет"),
    new File(["title,text,source\nA,B,C\n"], "custom.csv", { type: "text/csv" }),
  );

  await waitFor(() => {
    expect(screen.getByText("Активен: custom.csv")).toBeInTheDocument();
  });
});
```

- [ ] **Step 7: Run frontend tests**

Run:

```bash
npm --prefix frontend/web test -- --run
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/web/src
git commit -m "feat: добавить загрузку csv в интерфейс"
```

## Task 4: Dataset Preparation CLI

**Files:**
- Create: `tools/prepare_dataset.py`
- Test: `tests/test_prepare_dataset.py`
- Modify: `justfile`
- Modify: `docs/deployment/model-modes-and-large-datasets.md`

- [ ] **Step 1: Write failing tests**

Create `tests/test_prepare_dataset.py`:

```python
from pathlib import Path

import pandas as pd

from tools.prepare_dataset import prepare_dataset


def test_prepare_dataset_writes_application_and_training_csv(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    source.write_text(
        "headline,body,publisher,date,sentiment\n"
        "GDP grows,GDP grew by 2 percent,demo,2026-05-07,positive\n",
        encoding="utf-8",
    )
    app_output = tmp_path / "app.csv"
    train_output = tmp_path / "train.csv"

    prepare_dataset(
        input_path=source,
        app_output_path=app_output,
        train_output_path=train_output,
        id_column=None,
        title_column="headline",
        text_column="body",
        source_column="publisher",
        published_at_column="date",
        label_column="sentiment",
    )

    app_frame = pd.read_csv(app_output)
    train_frame = pd.read_csv(train_output)
    assert list(app_frame.columns) == ["id", "title", "text", "source", "published_at"]
    assert list(train_frame.columns) == ["article_id", "text", "impact", "source", "published_at"]
    assert train_frame.loc[0, "impact"] == "positive"


def test_prepare_dataset_maps_numeric_score_to_impact(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    source.write_text(
        "title,text,source,published_at,score\n"
        "A,Text A,demo,2026-05-07,0.7\n"
        "B,Text B,demo,2026-05-07,-0.8\n"
        "C,Text C,demo,2026-05-07,0.1\n",
        encoding="utf-8",
    )
    train_output = tmp_path / "train.csv"

    prepare_dataset(
        input_path=source,
        app_output_path=tmp_path / "app.csv",
        train_output_path=train_output,
        id_column=None,
        title_column="title",
        text_column="text",
        source_column="source",
        published_at_column="published_at",
        label_column="score",
        positive_threshold=0.2,
        negative_threshold=-0.2,
    )

    assert pd.read_csv(train_output)["impact"].tolist() == ["positive", "negative", "neutral"]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_prepare_dataset.py -v
```

Expected: FAIL because `tools.prepare_dataset` does not exist.

- [ ] **Step 3: Implement CLI**

Create `tools/prepare_dataset.py` with:

```python
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd

LABEL_MAP = {
    "positive": "positive",
    "pos": "positive",
    "1": "positive",
    "neutral": "neutral",
    "neu": "neutral",
    "0": "neutral",
    "negative": "negative",
    "neg": "negative",
    "-1": "negative",
}


def stable_id(*parts: str) -> str:
    digest = hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest()
    return digest[:16]


def normalize_impact(value: object, *, positive_threshold: float, negative_threshold: float) -> str:
    text = str(value).strip().lower()
    if text in LABEL_MAP:
        return LABEL_MAP[text]
    score = float(text)
    if score >= positive_threshold:
        return "positive"
    if score <= negative_threshold:
        return "negative"
    return "neutral"


def prepare_dataset(
    *,
    input_path: Path,
    app_output_path: Path,
    train_output_path: Path,
    id_column: str | None,
    title_column: str,
    text_column: str,
    source_column: str,
    published_at_column: str,
    label_column: str | None,
    positive_threshold: float = 0.2,
    negative_threshold: float = -0.2,
    limit: int | None = None,
) -> None:
    frame = pd.read_csv(input_path, nrows=limit)
    required = [title_column, text_column, source_column, published_at_column]
    if label_column is not None:
        required.append(label_column)
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    title = frame[title_column].astype(str).str.strip()
    text = frame[text_column].astype(str).str.strip()
    source = frame[source_column].astype(str).str.strip()
    published_at = pd.to_datetime(frame[published_at_column], errors="coerce").dt.strftime("%Y-%m-%dT%H:%M:%S")
    if id_column and id_column in frame.columns:
        ids = frame[id_column].astype(str).str.strip()
    else:
        ids = [stable_id(s, t, body) for s, t, body in zip(source, title, text, strict=True)]

    app_output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "id": ids,
            "title": title,
            "text": text,
            "source": source,
            "published_at": published_at,
        },
    ).dropna().to_csv(app_output_path, index=False)

    if label_column is None:
        return

    train_output_path.parent.mkdir(parents=True, exist_ok=True)
    impact = frame[label_column].map(
        lambda value: normalize_impact(
            value,
            positive_threshold=positive_threshold,
            negative_threshold=negative_threshold,
        ),
    )
    pd.DataFrame(
        {
            "article_id": ids,
            "text": text,
            "impact": impact,
            "source": source,
            "published_at": published_at,
        },
    ).dropna().to_csv(train_output_path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare external news dataset CSV files.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--app-output", type=Path, default=Path("data/raw/economic_news.csv"))
    parser.add_argument("--train-output", type=Path, default=Path("data/raw/news_impact.csv"))
    parser.add_argument("--id-column")
    parser.add_argument("--title-column", default="title")
    parser.add_argument("--text-column", default="text")
    parser.add_argument("--source-column", default="source")
    parser.add_argument("--published-at-column", default="published_at")
    parser.add_argument("--label-column")
    parser.add_argument("--positive-threshold", type=float, default=0.2)
    parser.add_argument("--negative-threshold", type=float, default=-0.2)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    prepare_dataset(
        input_path=args.input,
        app_output_path=args.app_output,
        train_output_path=args.train_output,
        id_column=args.id_column,
        title_column=args.title_column,
        text_column=args.text_column,
        source_column=args.source_column,
        published_at_column=args.published_at_column,
        label_column=args.label_column,
        positive_threshold=args.positive_threshold,
        negative_threshold=args.negative_threshold,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Add justfile wrappers**

Modify `justfile`:

```make
prepare-dataset input:
    uv run python tools/prepare_dataset.py {{input}}

train-baseline:
    uv run --project research python -m economic_news_research.cli train-baseline --dataset data/raw/news_impact.csv --output-dir artifacts/models/baseline

train-embedding:
    uv run --project research python -m economic_news_research.cli train-embedding --dataset data/raw/news_impact.csv --output-dir artifacts/models/embedding

train-transformer:
    uv run --project research python -m economic_news_research.cli train-transformer --dataset data/raw/news_impact.csv --output-dir artifacts/models/transformer

compare-models:
    uv run --project research python -m economic_news_research.cli compare-models

demo-up-trained:
    ANALYSIS_USE_STATIC_CLASSIFIER=false docker compose -f deploy/compose.yaml up --build
```

- [ ] **Step 5: Run CLI tests**

Run:

```bash
uv run pytest tests/test_prepare_dataset.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/prepare_dataset.py tests/test_prepare_dataset.py justfile
git commit -m "feat: добавить подготовку датасетов для обучения"
```

## Task 5: Classifier Confidence And Model Comparison Integration

**Files:**
- Modify: `apps/analysis-service/src/analysis_service/infrastructure/classifiers.py`
- Modify: `apps/analysis-service/tests/test_infrastructure.py`
- Modify: `research/README.md`
- Modify: `docs/deployment/model-modes-and-large-datasets.md`

- [ ] **Step 1: Add failing confidence test**

Append to `apps/analysis-service/tests/test_infrastructure.py`:

```python
class ProbabilityEstimator:
    classes_ = ["negative", "neutral", "positive"]

    def predict(self, texts: list[str]) -> list[str]:
        return ["positive"]

    def predict_proba(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.7]]


def test_joblib_classifier_uses_predict_proba_confidence(tmp_path: Path) -> None:
    model_path = tmp_path / "model.joblib"
    joblib.dump(ProbabilityEstimator(), model_path)
    classifier = JoblibImpactClassifier(
        model_name=AnalysisModelName.TFIDF_LOGREG,
        artifact_path=model_path,
    )

    prediction = classifier.predict(NewsText.from_raw("Markets rise"))

    assert prediction.confidence == 0.7
    assert prediction.metadata == {"artifact_path": str(model_path), "source": "joblib"}
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
uv run pytest apps/analysis-service/tests/test_infrastructure.py::test_joblib_classifier_uses_predict_proba_confidence -v
```

Expected: FAIL because confidence is not set and metadata lacks `source`.

- [ ] **Step 3: Implement confidence extraction**

Modify `JoblibImpactClassifier.predict`:

```python
    def predict(self, text: NewsText) -> ImpactPrediction:
        estimator = self._load_estimator()
        try:
            raw_prediction = estimator.predict([text.value])[0]
            impact = ImpactLabel(str(raw_prediction))
            confidence = self._confidence_for_prediction(estimator, text.value, impact)
        except Exception as exc:
            raise ModelUnavailableError(self.model_name) from exc
        return ImpactPrediction(
            model_name=self.model_name,
            impact=impact,
            confidence=confidence,
            metadata={"artifact_path": str(self._artifact_path), "source": "joblib"},
        )

    def _confidence_for_prediction(self, estimator: Any, text: str, impact: ImpactLabel) -> float | None:
        if not hasattr(estimator, "predict_proba"):
            return None
        probabilities = estimator.predict_proba([text])[0]
        classes = [str(item) for item in getattr(estimator, "classes_", [])]
        if impact.value not in classes:
            return None
        return float(probabilities[classes.index(impact.value)])
```

- [ ] **Step 4: Run analysis tests**

Run:

```bash
uv run pytest apps/analysis-service/tests/test_infrastructure.py apps/analysis-service/tests/test_api.py -v
```

Expected: PASS. If existing metadata assertions expect only `artifact_path`, update them to include `source: joblib`.

- [ ] **Step 5: Update docs**

Update `research/README.md` and `docs/deployment/model-modes-and-large-datasets.md` with:

```markdown
After training, run:

```bash
just compare-models
just demo-up-trained
```

The app can then switch between trained `tfidf-logreg`, `embedding-logreg` and
`tiny-transformer-classifier` modes from the chat UI. If an artifact is missing,
the corresponding model returns a controlled unavailable-model error.
```
```

- [ ] **Step 6: Commit**

```bash
git add apps/analysis-service/src/analysis_service/infrastructure/classifiers.py apps/analysis-service/tests/test_infrastructure.py apps/analysis-service/tests/test_api.py research/README.md docs/deployment/model-modes-and-large-datasets.md
git commit -m "feat: добавить confidence для обученных классификаторов"
```

## Task 6: Compose, Docs, Final Coursework Artifacts

**Files:**
- Modify: `deploy/compose.yaml`
- Modify: `.env.example`
- Modify: `docs/demo.md`
- Modify: `docs/final/README.md`
- Modify: `docs/coursework/thesis-draft.md`
- Modify: `docs/presentation/speaker-notes.md`
- Modify generators if final DOCX/PPTX need the new dataset/training workflow.

- [ ] **Step 1: Update compose mounts and env**

Modify `deploy/compose.yaml`:

```yaml
  news-service:
    environment:
      NEWS_SERVICE_DATASET_UPLOAD_DIR: "${NEWS_SERVICE_DATASET_UPLOAD_DIR:-data/uploads}"
      NEWS_SERVICE_ACTIVE_DATASET_FILE: "${NEWS_SERVICE_ACTIVE_DATASET_FILE:-data/uploads/active_dataset.json}"
      NEWS_SERVICE_UPLOAD_MAX_BYTES: "${NEWS_SERVICE_UPLOAD_MAX_BYTES:-52428800}"
    volumes:
      - ../data:/app/data

  news-worker:
    volumes:
      - ../data:/app/data
```

Modify `.env.example`:

```env
NEWS_SERVICE_DATASET_UPLOAD_DIR=data/uploads
NEWS_SERVICE_ACTIVE_DATASET_FILE=data/uploads/active_dataset.json
NEWS_SERVICE_UPLOAD_MAX_BYTES=52428800
```

- [ ] **Step 2: Update documentation**

Update `docs/demo.md`, `docs/final/README.md`, `docs/coursework/thesis-draft.md`, and `docs/presentation/speaker-notes.md` to mention:

- CSV upload through UI;
- active uploaded dataset;
- `just prepare-dataset`;
- `just train-baseline`, `just train-embedding`, `just train-transformer`, `just compare-models`;
- `just demo-up-trained`.

- [ ] **Step 3: Regenerate final DOCX/PPTX if generators changed**

If `tools/build_final_coursework_docx.py` or `tools/build_final_coursework_pptx.mjs` changed, run:

```bash
/Users/a.prudiev/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 tools/build_final_coursework_docx.py
NODE_PATH=/Users/a.prudiev/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules /Users/a.prudiev/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node tools/build_final_coursework_pptx.mjs
```

- [ ] **Step 4: Render Office QA if final files changed**

Run:

```bash
env TMPDIR=/private/tmp /Users/a.prudiev/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 /Users/a.prudiev/.codex/plugins/cache/openai-primary-runtime/documents/26.506.11943/skills/documents/render_docx.py docs/final/coursework-explanatory-note.docx --output_dir docs/final/qa/docx-render --emit_pdf
soffice --headless --convert-to pdf --outdir docs/final/qa/pptx-render docs/final/coursework-defense-presentation.pptx
pdftoppm -png -r 140 docs/final/qa/pptx-render/coursework-defense-presentation.pdf docs/final/qa/pptx-render/page
```

Expected: DOCX renders, PPTX exports to PDF, PNG pages generated.

- [ ] **Step 5: Run full verification**

Run:

```bash
uv run pytest packages apps -v
npm --prefix frontend/web test -- --run
uv run pytest tests/test_prepare_dataset.py -v
docker compose -f deploy/compose.yaml config --quiet
git diff --check
unzip -t docs/final/coursework-explanatory-note.docx
unzip -t docs/final/coursework-defense-presentation.pptx
```

Expected: all pass.

- [ ] **Step 6: Commit and push**

```bash
git add .
git commit -m "docs: обновить материалы по загрузке и обучению"
git push
```

## Self-Review

Spec coverage:

- Upload API/UI: Tasks 1-3.
- Active dataset for preview/index: Task 2.
- Dataset conversion CLI: Task 4.
- Training wrappers and model comparison: Task 4.
- Trained classifier confidence: Task 5.
- Compose/docs/final materials: Task 6.

No placeholders remain. Type names are consistent with the spec and current codebase patterns.
