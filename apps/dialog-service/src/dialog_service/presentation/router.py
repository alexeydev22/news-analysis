from dishka.integrations.fastapi import FromDishka, inject
from economic_news_contracts.dialog import GenerateDialogRequest, GenerateDialogResponse
from fastapi import APIRouter

from dialog_service.application.use_cases import GenerateDialogAnswer
from dialog_service.domain.errors import DialogGeneratorUnavailableError
from dialog_service.presentation.errors import map_generator_error

router = APIRouter(prefix="/api/v1")


@router.post("/dialog/generate")
@inject
async def generate_dialog(
    request: GenerateDialogRequest,
    use_case: FromDishka[GenerateDialogAnswer],
) -> GenerateDialogResponse:
    try:
        return await use_case.execute(request)
    except DialogGeneratorUnavailableError as error:
        raise map_generator_error(error) from error
