from api_gateway.application.errors import (
    AnalysisServiceUnavailableError,
    RetrievalServiceUnavailableError,
)
from fastapi import HTTPException, status


def map_analysis_error(error: AnalysisServiceUnavailableError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(error),
    )


def map_retrieval_error(_: RetrievalServiceUnavailableError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="retrieval-service is unavailable",
    )
