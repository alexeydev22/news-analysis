from typing import Protocol

from retrieval_service.domain.model import NewsDocument, SearchQuery, SearchResult


class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Build embeddings for input texts."""
        ...


class VectorRepository(Protocol):
    async def upsert(self, documents: list[NewsDocument], vectors: list[list[float]]) -> int:
        """Store documents with their vectors."""
        ...

    async def search(self, query: SearchQuery, vector: list[float]) -> list[SearchResult]:
        """Search nearest documents for query vector."""
        ...

    async def list_documents(self, *, limit: int, source: str | None) -> list[NewsDocument]:
        """Return indexed documents from vector store payloads."""
        ...

    async def neighbors(
        self,
        *,
        document_ids: list[str],
        limit: int,
        source: str | None,
    ) -> dict[str, list[SearchResult]]:
        """Return nearest indexed documents for each seed document id."""
        ...
