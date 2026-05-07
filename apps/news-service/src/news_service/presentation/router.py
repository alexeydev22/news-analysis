from dishka.integrations.fastapi import FromDishka, inject
from economic_news_contracts.news import (
    IndexNewsDatasetRequest,
    IndexNewsDatasetResponse,
    NewsDocumentResponse,
    PreviewNewsResponse,
)
from fastapi import APIRouter, Query

from news_service.application.use_cases import IndexNewsDataset, PreviewNews

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
) -> IndexNewsDatasetResponse:
    return await use_case.execute(limit=request.limit)
