from api_gateway.application.errors import AnalysisServiceUnavailableError
from api_gateway.application.ports import VersionProvider
from api_gateway.application.use_cases import AnalyzeNewsUseCase
from api_gateway.presentation.errors import map_analysis_error
from dishka.integrations.fastapi import FromDishka, inject
from economic_news_contracts.analysis import AnalyzeNewsRequest, AnalyzeNewsResponse
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
