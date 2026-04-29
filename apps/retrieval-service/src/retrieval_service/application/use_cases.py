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
