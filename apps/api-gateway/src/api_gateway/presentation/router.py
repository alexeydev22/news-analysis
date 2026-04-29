from api_gateway.application.errors import (
    AnalysisServiceUnavailableError,
    RetrievalServiceUnavailableError,
)
from api_gateway.application.ports import VersionProvider
from api_gateway.application.use_cases import (
    AnalyzeNewsUseCase,
    IndexNewsUseCase,
    SearchNewsUseCase,
)
from api_gateway.presentation.errors import map_analysis_error, map_retrieval_error
from dishka.integrations.fastapi import FromDishka, inject
from economic_news_contracts.analysis import AnalyzeNewsRequest, AnalyzeNewsResponse
from economic_news_contracts.retrieval import (
    IndexNewsRequest,
    IndexNewsResponse,
    SearchNewsRequest,
    SearchNewsResponse,
)
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")


@router.get("/version")
@inject
async def version(version_provider: FromDishka[VersionProvider]) -> dict[str, str]:
    return {"service": "api-gateway", "version": version_provider.get_version()}


@router.post("/analyze")
@inject
async def analyze(
    request: AnalyzeNewsRequest,
    use_case: FromDishka[AnalyzeNewsUseCase],
) -> AnalyzeNewsResponse:
    try:
        return await use_case.execute(request)
    except AnalysisServiceUnavailableError as error:
        raise map_analysis_error(error) from error


@router.post("/retrieval/index")
@inject
async def index_news(
    request: IndexNewsRequest,
    use_case: FromDishka[IndexNewsUseCase],
) -> IndexNewsResponse:
    try:
        return await use_case.execute(request)
    except RetrievalServiceUnavailableError as error:
        raise map_retrieval_error(error) from error


@router.post("/retrieval/search")
@inject
async def search_news(
    request: SearchNewsRequest,
    use_case: FromDishka[SearchNewsUseCase],
) -> SearchNewsResponse:
    try:
        return await use_case.execute(request)
    except RetrievalServiceUnavailableError as error:
        raise map_retrieval_error(error) from error
