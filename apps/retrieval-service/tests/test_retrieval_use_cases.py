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
