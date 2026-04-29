import pytest
from api_gateway.application.errors import RetrievalServiceUnavailableError
from api_gateway.application.use_cases import IndexNewsUseCase, SearchNewsUseCase
from economic_news_contracts.retrieval import (
    IndexNewsRequest,
    IndexNewsResponse,
    NewsDocumentPayload,
    SearchNewsRequest,
    SearchNewsResponse,
    SearchNewsResult,
)


class FakeRetrievalClient:
    def __init__(self) -> None:
        self.index_request: IndexNewsRequest | None = None
        self.search_request: SearchNewsRequest | None = None

    async def index(self, request: IndexNewsRequest) -> IndexNewsResponse:
        self.index_request = request
        return IndexNewsResponse(
            indexed_count=len(request.documents),
            collection_name="economic_news",
        )

    async def search(self, request: SearchNewsRequest) -> SearchNewsResponse:
        self.search_request = request
        return SearchNewsResponse(
            results=[
                SearchNewsResult(
                    id="news-1",
                    score=0.75,
                    title="GDP grows",
                    text="GDP grew by 2 percent.",
                    source="demo",
                ),
            ],
        )


class FailingRetrievalClient:
    async def index(self, request: IndexNewsRequest) -> IndexNewsResponse:
        raise RetrievalServiceUnavailableError("retrieval-service is unavailable")

    async def search(self, request: SearchNewsRequest) -> SearchNewsResponse:
        raise RetrievalServiceUnavailableError("retrieval-service is unavailable")


@pytest.mark.asyncio
async def test_index_news_use_case_delegates_to_client() -> None:
    client = FakeRetrievalClient()
    use_case = IndexNewsUseCase(client)
    request = IndexNewsRequest(
        documents=[
            NewsDocumentPayload(
                id="news-1",
                title="GDP grows",
                text="GDP grew by 2 percent.",
                source="demo",
            ),
        ],
    )

    response = await use_case.execute(request)

    assert client.index_request == request
    assert response.indexed_count == 1


@pytest.mark.asyncio
async def test_search_news_use_case_delegates_to_client() -> None:
    client = FakeRetrievalClient()
    use_case = SearchNewsUseCase(client)
    request = SearchNewsRequest(query="GDP", limit=3)

    response = await use_case.execute(request)

    assert client.search_request == request
    assert response.results[0].id == "news-1"


@pytest.mark.asyncio
async def test_retrieval_use_cases_preserve_unavailable_error() -> None:
    index_use_case = IndexNewsUseCase(FailingRetrievalClient())
    search_use_case = SearchNewsUseCase(FailingRetrievalClient())

    with pytest.raises(RetrievalServiceUnavailableError):
        await index_use_case.execute(
            IndexNewsRequest(
                documents=[
                    NewsDocumentPayload(
                        id="news-1",
                        title="GDP grows",
                        text="GDP grew by 2 percent.",
                        source="demo",
                    ),
                ],
            ),
        )

    with pytest.raises(RetrievalServiceUnavailableError):
        await search_use_case.execute(SearchNewsRequest(query="GDP"))
