from dialog_service.application.ports import DialogGenerator
from dialog_service.domain.model import (
    DialogContextItem,
    DialogGeneration,
    DialogImpactItem,
    DialogQuestion,
)


class GenerateDialogAnswer:
    def __init__(self, generator: DialogGenerator) -> None:
        self._generator = generator

    async def execute(
        self,
        question: DialogQuestion,
        context: list[DialogContextItem],
        impact_summaries: list[DialogImpactItem],
        language: str,
    ) -> DialogGeneration:
        return await self._generator.generate(
            question=question,
            context=context,
            impact_summaries=impact_summaries,
            language=language,
        )
