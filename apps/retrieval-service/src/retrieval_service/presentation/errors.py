from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from retrieval_service.domain.errors import (
    EmptyDocumentTextError,
    InvalidSearchLimitError,
    RetrievalUnavailableError,
)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(EmptyDocumentTextError)
    async def empty_document_text_handler(
        request: Request,
        exc: EmptyDocumentTextError,
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(InvalidSearchLimitError)
    async def invalid_search_limit_handler(
        request: Request,
        exc: InvalidSearchLimitError,
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(RetrievalUnavailableError)
    async def retrieval_unavailable_handler(
        request: Request,
        exc: RetrievalUnavailableError,
    ) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})
