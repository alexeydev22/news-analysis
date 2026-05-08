from dishka.integrations.fastapi import FromDishka, inject
from economic_news_contracts.news import (
    EnqueueIndexNewsDatasetResponse,
    IndexNewsDatasetRequest,
    IndexNewsDatasetResponse,
    NewsDocumentResponse,
    PreviewNewsResponse,
)
from fastapi import APIRouter, Query

from news_service.application.use_cases import (
    EnqueueIndexNewsDataset,
    IndexNewsDataset,
    PreviewNews,
)
from news_service.main.settings import NewsServiceSettings

router = APIRouter(prefix="/api/v1/news")


@router.get("/preview")
@inject
async def preview_news(
    use_case: FromDishka[PreviewNews],
    limit: int = Query(default=10, ge=1, le=100),
) -> PreviewNewsResponse:
    documents, total_count = await use_case.execute(limit=limit)
    return PreviewNewsResponse(
        documents=[
            NewsDocumentResponse(
                id=document.id,
                title=document.title,
                text=document.text,
                source=document.source,
                published_at=document.published_at,
                metadata=dict(document.metadata),
            )
            for document in documents
        ],
        total_count=total_count,
    )


@router.post("/index")
@inject
async def index_news(
    request: IndexNewsDatasetRequest,
    use_case: FromDishka[IndexNewsDataset],
    settings: FromDishka[NewsServiceSettings],
) -> IndexNewsDatasetResponse:
    limit = request.limit if "limit" in request.model_fields_set else settings.default_index_limit
    return await use_case.execute(limit=limit)


@router.post("/index/jobs", status_code=202)
@inject
async def enqueue_index_news(
    request: IndexNewsDatasetRequest,
    use_case: FromDishka[EnqueueIndexNewsDataset],
    settings: FromDishka[NewsServiceSettings],
) -> EnqueueIndexNewsDatasetResponse:
    limit = request.limit if "limit" in request.model_fields_set else settings.default_index_limit
    return await use_case.execute(limit=limit)
