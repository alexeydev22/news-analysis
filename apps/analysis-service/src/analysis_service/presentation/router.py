from dishka.integrations.fastapi import FromDishka, inject
from economic_news_contracts.analysis import (
    AnalyzeNewsRequest,
    AnalyzeNewsResponse,
    EnqueueMlReportJobRequest,
    EnqueueMlReportJobResponse,
    EnqueueTopicForecastJobResponse,
    GroqForecastRequest,
    GroqForecastResponse,
    MlReportJobResponse,
    MlReportResponse,
    TopicForecastJobResponse,
    TopicForecastResponse,
)
from fastapi import APIRouter, status

from analysis_service.application.use_cases import (
    AnalyzeNewsImpact,
    EnqueueMlReportJob,
    EnqueueTopicForecastJob,
    GenerateGroqTopicForecast,
    GetLatestMlReport,
    GetLatestTopicForecast,
    GetMlReportJob,
    GetTopicForecastJob,
)

router = APIRouter(prefix="/api/v1")
PUBLIC_METADATA_KEYS = frozenset({"source"})


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
        metadata={
            key: value
            for key, value in prediction.metadata.items()
            if key in PUBLIC_METADATA_KEYS
        },
    )


@router.post(
    "/ml-report/jobs",
    response_model=EnqueueMlReportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@inject
async def enqueue_ml_report_job(
    request: EnqueueMlReportJobRequest,
    use_case: FromDishka[EnqueueMlReportJob],
) -> EnqueueMlReportJobResponse:
    return await use_case.execute()


@router.get("/ml-report/jobs/{job_id}", response_model=MlReportJobResponse)
@inject
async def get_ml_report_job(
    job_id: str,
    use_case: FromDishka[GetMlReportJob],
) -> MlReportJobResponse:
    return await use_case.execute(job_id)


@router.get("/ml-report/latest", response_model=MlReportResponse | None)
@inject
async def get_latest_ml_report(
    use_case: FromDishka[GetLatestMlReport],
) -> dict[str, object] | None:
    return await use_case.execute()


@router.post(
    "/topic-forecast/jobs",
    response_model=EnqueueTopicForecastJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@inject
async def enqueue_topic_forecast_job(
    use_case: FromDishka[EnqueueTopicForecastJob],
) -> EnqueueTopicForecastJobResponse:
    return await use_case.execute()


@router.get("/topic-forecast/jobs/{job_id}", response_model=TopicForecastJobResponse)
@inject
async def get_topic_forecast_job(
    job_id: str,
    use_case: FromDishka[GetTopicForecastJob],
) -> TopicForecastJobResponse:
    return await use_case.execute(job_id)


@router.get("/topic-forecast/latest", response_model=TopicForecastResponse | None)
@inject
async def get_latest_topic_forecast(
    use_case: FromDishka[GetLatestTopicForecast],
) -> TopicForecastResponse | None:
    return await use_case.execute()


@router.post("/topic-forecast/groq-predictions", response_model=GroqForecastResponse)
@inject
async def generate_groq_topic_prediction(
    request: GroqForecastRequest,
    use_case: FromDishka[GenerateGroqTopicForecast],
) -> GroqForecastResponse:
    return await use_case.execute(request)
