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
