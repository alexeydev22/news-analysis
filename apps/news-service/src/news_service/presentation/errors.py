from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from news_service.domain.errors import (
    NewsSourceUnavailableError,
    NewsSourceValidationError,
    RetrievalIndexUnavailableError,
)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NewsSourceValidationError)
    async def handle_validation_error(
        _: Request,
        __: NewsSourceValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": "Invalid news source data"},
        )

    @app.exception_handler(NewsSourceUnavailableError)
    async def handle_source_unavailable(
        _: Request,
        __: NewsSourceUnavailableError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "news source is unavailable"},
        )

    @app.exception_handler(RetrievalIndexUnavailableError)
    async def handle_retrieval_unavailable(
        _: Request,
        __: RetrievalIndexUnavailableError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "retrieval-service is unavailable"},
        )
