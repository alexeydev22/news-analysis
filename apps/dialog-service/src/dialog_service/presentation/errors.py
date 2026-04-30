from fastapi import HTTPException, status

from dialog_service.domain.errors import DialogGeneratorUnavailableError


def map_generator_error(_: DialogGeneratorUnavailableError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="dialog-service is unavailable",
    )
