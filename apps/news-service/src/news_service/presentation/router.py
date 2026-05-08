from dishka.integrations.fastapi import FromDishka, inject
from economic_news_contracts.news import (
    ActiveDatasetResponse,
    DatasetListResponse,
    EnqueueIndexNewsDatasetResponse,
    IndexNewsDatasetRequest,
    IndexNewsDatasetResponse,
    NewsDocumentResponse,
    PreviewNewsResponse,
    UploadedDatasetResponse,
)
from fastapi import APIRouter, File, Query, UploadFile, status

from news_service.application.use_cases import (
    ActivateNewsDataset,
    EnqueueIndexNewsDataset,
    GetActiveNewsDataset,
    IndexNewsDataset,
    ListNewsDatasets,
    PreviewNews,
    UploadNewsDataset,
)
from news_service.domain.dataset import ActiveDataset, UploadedDataset
from news_service.main.settings import NewsServiceSettings

router = APIRouter(prefix="/api/v1/news")
_UPLOAD_FILE = File(...)


def _uploaded_dataset_response(dataset: UploadedDataset) -> UploadedDatasetResponse:
    return UploadedDatasetResponse(
        dataset_id=dataset.dataset_id,
        filename=dataset.filename,
        size_bytes=dataset.size_bytes,
        uploaded_at=dataset.uploaded_at,
    )


def _active_dataset_response(dataset: ActiveDataset) -> ActiveDatasetResponse:
    return ActiveDatasetResponse(
        dataset_id=dataset.dataset_id,
        filename=dataset.filename,
        activated_at=dataset.activated_at,
    )


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


@router.post("/datasets/upload", status_code=status.HTTP_201_CREATED)
@inject
async def upload_dataset(
    use_case: FromDishka[UploadNewsDataset],
    file: UploadFile = _UPLOAD_FILE,
) -> UploadedDatasetResponse:
    content = await file.read()
    dataset = await use_case.execute(
        filename=file.filename or "dataset.csv",
        content=content,
    )
    return _uploaded_dataset_response(dataset)


@router.get("/datasets")
@inject
async def list_datasets(use_case: FromDishka[ListNewsDatasets]) -> DatasetListResponse:
    datasets = await use_case.execute()
    return DatasetListResponse(
        datasets=[_uploaded_dataset_response(dataset) for dataset in datasets],
    )


@router.post("/datasets/{dataset_id}/activate")
@inject
async def activate_dataset(
    dataset_id: str,
    use_case: FromDishka[ActivateNewsDataset],
) -> ActiveDatasetResponse:
    active = await use_case.execute(dataset_id)
    return _active_dataset_response(active)


@router.get("/datasets/active")
@inject
async def get_active_dataset(
    use_case: FromDishka[GetActiveNewsDataset],
) -> ActiveDatasetResponse | None:
    active = await use_case.execute()
    if active is None:
        return None
    return _active_dataset_response(active)
