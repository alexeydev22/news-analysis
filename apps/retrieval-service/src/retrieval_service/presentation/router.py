from dishka.integrations.fastapi import FromDishka, inject
from economic_news_contracts.retrieval import (
    IndexNewsRequest,
    IndexNewsResponse,
    SearchNewsRequest,
    SearchNewsResponse,
)
from economic_news_contracts.retrieval import (
    SearchNewsResult as SearchNewsResultPayload,
)
from fastapi import APIRouter

from retrieval_service.application.use_cases import IndexNewsDocuments, SearchNews
from retrieval_service.domain.model import NewsDocument, SearchQuery
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
                score=result.score,
                title=result.document.title,
                text=result.document.text,
                source=result.document.source,
                published_at=result.document.published_at,
                metadata=dict(result.document.metadata),
            )
            for result in results
        ],
    )
