import sys
from pathlib import Path

import pytest
from economic_news_contracts.retrieval import IndexNewsResponse

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from news_service.application.use_cases import IndexNewsDataset, PreviewNews
from news_service.domain.model import NewsDocument


class FakeNewsSource:
    def __init__(self) -> None:
        self.limit: int | None = None

    async def load(self, limit: int | None = None) -> list[NewsDocument]:
        self.limit = limit
        documents = [
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
        if limit is not None:
            return documents[:limit]
        return documents


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
