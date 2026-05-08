from typing import Protocol

from economic_news_contracts.retrieval import IndexNewsResponse

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
