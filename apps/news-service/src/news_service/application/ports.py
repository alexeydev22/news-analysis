from pathlib import Path
from typing import Protocol

from economic_news_contracts.retrieval import IndexNewsResponse

from news_service.domain.dataset import ActiveDataset, UploadedDataset
from news_service.domain.model import NewsDocument


class NewsSource(Protocol):
    async def load(self, limit: int | None = None) -> list[NewsDocument]:
        """Load normalized news documents."""
        ...


class RetrievalIndexer(Protocol):
    async def index(self, documents: list[NewsDocument]) -> IndexNewsResponse:
        """Index normalized news documents through retrieval-service."""
        ...


class NewsIndexTaskQueue(Protocol):
    async def enqueue(self, limit: int) -> str:
        """Schedule dataset indexing and return an externally visible job id."""
        ...


class DatasetStorage(Protocol):
    async def save_upload(self, *, filename: str, content: bytes) -> UploadedDataset:
        """Persist an uploaded dataset and return its metadata."""
        ...

    async def list_datasets(self) -> list[UploadedDataset]:
        """Return uploaded datasets sorted for stable presentation."""
        ...

    async def activate(self, dataset_id: str) -> ActiveDataset:
        """Mark an uploaded dataset as active."""
        ...

    async def get_active(self) -> ActiveDataset | None:
        """Return the active dataset if it still exists."""
        ...

    async def get_active_path(self) -> Path | None:
        """Return the active dataset path if it still exists."""
        ...
