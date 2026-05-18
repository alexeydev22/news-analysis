from dialog_service.application.ports import DialogGenerator
from dialog_service.domain.errors import DialogGeneratorUnavailableError
from dialog_service.domain.model import (
    DialogContextItem,
    DialogGeneration,
    DialogImpactItem,
    DialogQuestion,
)


class FallbackDialogGenerator:
    def __init__(self, primary: DialogGenerator, fallback: DialogGenerator) -> None:
        self._primary = primary
        self._fallback = fallback

    async def generate(
        self,
        question: DialogQuestion,
        context: list[DialogContextItem],
        impact_summaries: list[DialogImpactItem],
        language: str,
    ) -> DialogGeneration:
        try:
            return await self._primary.generate(
                question=question,
                context=context,
                impact_summaries=impact_summaries,
                language=language,
            )
        except DialogGeneratorUnavailableError as error:
            generation = await self._fallback.generate(
                question=question,
                context=context,
                impact_summaries=impact_summaries,
                language=language,
            )
            return DialogGeneration(
                answer=generation.answer,
                used_context_ids=generation.used_context_ids,
                model_name=generation.model_name,
                metadata={
                    **generation.metadata,
                    "fallback_from": "llm",
                    "fallback_reason": type(error).__name__,
                },
            )
