from dishka.integrations.fastapi import FromDishka, inject
from economic_news_contracts.analysis import AnalyzeNewsRequest, AnalyzeNewsResponse
from fastapi import APIRouter

from analysis_service.application.use_cases import AnalyzeNewsImpact

router = APIRouter(prefix="/api/v1")


@router.post("/analyze")
@inject
async def analyze(
    request: AnalyzeNewsRequest,
    use_case: FromDishka[AnalyzeNewsImpact],
) -> AnalyzeNewsResponse:
    prediction = use_case.execute(
        text=request.text,
        model_name=request.analysis_model,
    )
    return AnalyzeNewsResponse(
        model_name=prediction.model_name,
        impact=prediction.impact,
        confidence=prediction.confidence,
        explanation=prediction.explanation or "",
        metadata=dict(prediction.metadata),
    )
