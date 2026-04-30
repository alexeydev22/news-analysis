from dishka.integrations.fastapi import FromDishka, inject
from economic_news_contracts.dialog import GenerateDialogRequest, GenerateDialogResponse
from fastapi import APIRouter

from dialog_service.application.use_cases import GenerateDialogAnswer
from dialog_service.domain.errors import DialogGeneratorUnavailableError
from dialog_service.domain.model import DialogContextItem, DialogGeneration, DialogQuestion
from dialog_service.presentation.errors import map_generator_error

router = APIRouter(prefix="/api/v1")


def _to_domain_context(request: GenerateDialogRequest) -> list[DialogContextItem]:
    return [
        DialogContextItem(
            id=item.id,
            title=item.title,
            text=item.text,
            source=item.source,
            score=item.score,
            published_at=item.published_at,
            metadata=item.metadata,
        )
        for item in request.context
    ]


def _to_response(generation: DialogGeneration) -> GenerateDialogResponse:
    return GenerateDialogResponse(
        answer=generation.answer,
        used_context_ids=generation.used_context_ids,
        model_name=generation.model_name,
        metadata=dict(generation.metadata),
    )


@router.post("/dialog/generate")
@inject
async def generate_dialog(
    request: GenerateDialogRequest,
    use_case: FromDishka[GenerateDialogAnswer],
) -> GenerateDialogResponse:
    try:
        generation = await use_case.execute(
            question=DialogQuestion(request.question),
            context=_to_domain_context(request),
            impact_summaries=request.impact_summaries,
            language=request.language,
        )
    except DialogGeneratorUnavailableError as error:
        raise map_generator_error(error) from error
    return _to_response(generation)
