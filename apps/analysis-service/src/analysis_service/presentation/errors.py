from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from analysis_service.domain.errors import (
    EmptyNewsTextError,
    MlReportJobNotFoundError,
    ModelUnavailableError,
    TopicForecastJobNotFoundError,
)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(EmptyNewsTextError)
    async def empty_news_text_handler(
        request: Request,
        exc: EmptyNewsTextError,
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(ModelUnavailableError)
    async def model_unavailable_handler(
        request: Request,
        exc: ModelUnavailableError,
    ) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(MlReportJobNotFoundError)
    async def ml_report_job_not_found_handler(
        request: Request,
        exc: MlReportJobNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(TopicForecastJobNotFoundError)
    async def topic_forecast_job_not_found_handler(
        request: Request,
        exc: TopicForecastJobNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
