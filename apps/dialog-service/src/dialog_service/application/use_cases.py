from economic_news_contracts.dialog import GenerateDialogRequest, GenerateDialogResponse

from dialog_service.application.ports import DialogGenerator
from dialog_service.domain.model import DialogContextItem, DialogQuestion


class GenerateDialogAnswer:
    def __init__(self, generator: DialogGenerator) -> None:
        self._generator = generator

    async def execute(self, request: GenerateDialogRequest) -> GenerateDialogResponse:
        context = [
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
        generation = await self._generator.generate(
            question=DialogQuestion(request.question),
            context=context,
            impact_summaries=request.impact_summaries,
            language=request.language,
        )
        return GenerateDialogResponse(
            answer=generation.answer,
            used_context_ids=generation.used_context_ids,
            model_name=generation.model_name,
            metadata=dict(generation.metadata),
        )
