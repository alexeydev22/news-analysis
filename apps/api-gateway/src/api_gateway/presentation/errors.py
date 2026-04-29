from api_gateway.application.errors import AnalysisServiceUnavailableError
from fastapi import HTTPException, status


def map_analysis_error(error: AnalysisServiceUnavailableError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(error),
    )
