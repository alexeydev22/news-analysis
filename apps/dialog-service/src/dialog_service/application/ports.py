from typing import Protocol

from economic_news_contracts.dialog import DialogImpactSummary

from dialog_service.domain.model import DialogContextItem, DialogGeneration, DialogQuestion


class DialogGenerator(Protocol):
    async def generate(
        self,
        question: DialogQuestion,
        context: list[DialogContextItem],
        impact_summaries: list[DialogImpactSummary],
        language: str,
    ) -> DialogGeneration:
        """Generate a dialog answer from question, context, and impact summaries."""
