from dishka.integrations.fastapi import FromDishka, inject
from economic_news_contracts.retrieval import (
    FindNeighborsRequest,
    FindNeighborsResponse,
    IndexedNewsDocument,
    IndexNewsRequest,
    IndexNewsResponse,
    ListIndexedDocumentsResponse,
    NewsNeighbor,
    NewsNeighborGroup,
    SearchNewsRequest,
    SearchNewsResponse,
)
from economic_news_contracts.retrieval import (
    SearchNewsResult as SearchNewsResultPayload,
)
from fastapi import APIRouter

from retrieval_service.application.use_cases import (
    FindNewsNeighbors,
    IndexNewsDocuments,
    ListIndexedDocuments,
    SearchNews,
)
from retrieval_service.domain.model import NewsDocument, SearchQuery, SearchResult
from retrieval_service.main.settings import RetrievalServiceSettings

router = APIRouter(prefix="/api/v1")


@router.post("/index")
@inject
async def index_news(
    request: IndexNewsRequest,
    use_case: FromDishka[IndexNewsDocuments],
    settings: FromDishka[RetrievalServiceSettings],
) -> IndexNewsResponse:
    documents = [
        NewsDocument(
            id=document.id,
            title=document.title,
            text=document.text,
            source=document.source,
            published_at=document.published_at,
            metadata=document.metadata,
        )
        for document in request.documents
    ]
    indexed_count = await use_case.execute(documents)
    return IndexNewsResponse(
        indexed_count=indexed_count,
        collection_name=settings.collection_name,
    )


@router.post("/search")
@inject
async def search_news(
    request: SearchNewsRequest,
    use_case: FromDishka[SearchNews],
) -> SearchNewsResponse:
    query = SearchQuery(query=request.query, limit=request.limit, source=request.source)
    results = await use_case.execute(query)
    return SearchNewsResponse(
        results=[
            SearchNewsResultPayload(
                id=result.document.id,
                score=_normalize_score(result.score),
                title=result.document.title,
                text=result.document.text,
                source=result.document.source,
                published_at=result.document.published_at,
                metadata=dict(result.document.metadata),
            )
            for result in results
        ],
    )


@router.get("/documents")
@inject
async def list_documents(
    use_case: FromDishka[ListIndexedDocuments],
    limit: int = 100,
    source: str | None = None,
) -> ListIndexedDocumentsResponse:
    documents = await use_case.execute(limit=min(max(limit, 1), 500), source=source)
    return ListIndexedDocumentsResponse(
        documents=[_to_indexed_document(document) for document in documents],
    )


@router.post("/neighbors")
@inject
async def find_neighbors(
    request: FindNeighborsRequest,
    use_case: FromDishka[FindNewsNeighbors],
) -> FindNeighborsResponse:
    groups = await use_case.execute(
        document_ids=request.document_ids,
        limit=request.limit,
        source=request.source,
    )
    return FindNeighborsResponse(
        groups=[
            NewsNeighborGroup(
                document_id=document_id,
                neighbors=[_to_neighbor(result) for result in results],
            )
            for document_id, results in groups.items()
        ],
    )


def _to_indexed_document(document: NewsDocument) -> IndexedNewsDocument:
    return IndexedNewsDocument(
        id=document.id,
        title=document.title,
        text=document.text,
        source=document.source,
        published_at=document.published_at,
        metadata=dict(document.metadata),
    )


def _to_neighbor(result: SearchResult) -> NewsNeighbor:
    return NewsNeighbor(
        id=result.document.id,
        score=_normalize_score(result.score),
        title=result.document.title,
        text=result.document.text,
        source=result.document.source,
        published_at=result.document.published_at,
        metadata=dict(result.document.metadata),
    )


def _normalize_score(score: float) -> float:
    return min(max(score, -1.0), 1.0)
