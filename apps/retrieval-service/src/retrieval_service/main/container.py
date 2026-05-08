from typing import Any

from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider
from qdrant_client import AsyncQdrantClient

from retrieval_service.application.ports import EmbeddingProvider, VectorRepository
from retrieval_service.application.use_cases import IndexNewsDocuments, SearchNews
from retrieval_service.domain.model import NewsDocument, SearchQuery, SearchResult
from retrieval_service.infrastructure.embeddings import FastEmbedEmbeddingProvider
from retrieval_service.infrastructure.qdrant_repository import QdrantNewsRepository
from retrieval_service.main.settings import RetrievalServiceSettings


class StaticEmbeddingProvider:
    def __init__(self, dimensions: int) -> None:
        self._dimensions = dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_text(text) for text in texts]

    def _embed_text(self, text: str) -> list[float]:
        base = sum(ord(char) for char in text)
        return [float(((base + index * 31) % 1000) / 1000) for index in range(self._dimensions)]


class FakeVectorRepository:
    async def upsert(self, documents: list[NewsDocument], vectors: list[list[float]]) -> int:
        return len(documents)

    async def search(self, query: SearchQuery, vector: list[float]) -> list[SearchResult]:
        document = NewsDocument(
            id="news-1",
            title="GDP grows",
            text="GDP grew by 2 percent.",
            source=query.source or "demo",
        )
        return [SearchResult(document=document, score=0.91)]


class RetrievalServiceProvider(Provider):
    def __init__(
        self,
        settings: RetrievalServiceSettings | None = None,
        *,
        use_fake_components: bool = False,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._use_fake_components = use_fake_components

    @provide(scope=Scope.APP)
    def settings(self) -> RetrievalServiceSettings:
        return self._settings or RetrievalServiceSettings()

    @provide(scope=Scope.APP, provides=EmbeddingProvider)
    def embedding_provider(self, settings: RetrievalServiceSettings) -> EmbeddingProvider:
        if self._use_fake_components or settings.use_static_embeddings:
            return StaticEmbeddingProvider(dimensions=settings.embedding_dimension)
        return FastEmbedEmbeddingProvider(model_name=settings.embedding_model_name)

    @provide(scope=Scope.APP, provides=VectorRepository)
    def vector_repository(
        self,
        settings: RetrievalServiceSettings,
    ) -> VectorRepository:
        if self._use_fake_components:
            return FakeVectorRepository()
        return QdrantNewsRepository(
            client=AsyncQdrantClient(url=str(settings.qdrant_url)),
            collection_name=settings.collection_name,
            vector_size=settings.embedding_dimension,
        )

    @provide(scope=Scope.APP)
    def index_news_documents(
        self,
        embedder: EmbeddingProvider,
        repository: VectorRepository,
    ) -> IndexNewsDocuments:
        return IndexNewsDocuments(embedder, repository)

    @provide(scope=Scope.APP)
    def search_news(
        self,
        embedder: EmbeddingProvider,
        repository: VectorRepository,
    ) -> SearchNews:
        return SearchNews(embedder, repository)


def create_container(
    settings: RetrievalServiceSettings | None = None,
    *,
    use_fake_components: bool = False,
) -> Any:
    return make_async_container(
        RetrievalServiceProvider(settings, use_fake_components=use_fake_components),
        FastapiProvider(),
    )
