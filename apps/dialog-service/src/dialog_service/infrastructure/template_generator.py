from dialog_service.domain.errors import DialogGeneratorUnavailableError
from dialog_service.domain.model import (
    DialogContextItem,
    DialogGeneration,
    DialogImpactItem,
    DialogQuestion,
)

IMPACT_LABELS_RU = {
    "positive": "позитивное",
    "negative": "негативное",
    "neutral": "нейтральное",
}


class TemplateDialogGenerator:
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name

    async def generate(
        self,
        question: DialogQuestion,
        context: list[DialogContextItem],
        impact_summaries: list[DialogImpactItem],
        language: str,
    ) -> DialogGeneration:
        used_context_ids = [item.id for item in context]
        answer = self._build_answer(question, context, impact_summaries)
        return DialogGeneration(
            answer=answer,
            used_context_ids=used_context_ids,
            model_name=self._model_name,
            metadata={
                "generator_kind": "template",
                "model_name": self._model_name,
                "context_count": len(context),
                "impact_summary_count": len(impact_summaries),
                "language": language,
            },
        )

    def _build_answer(
        self,
        question: DialogQuestion,
        context: list[DialogContextItem],
        impact_summaries: list[DialogImpactItem],
    ) -> str:
        if not context:
            return (
                f'По вопросу "{question.value}" релевантные новости не найдены. '
                "Экономический вывод ограничен доступным контекстом и не является "
                "финансовой рекомендацией."
            )

        lines = [
            f'По вопросу "{question.value}" найденные новости дают следующий ориентир.',
            "Факторы влияния:",
        ]
        summaries_by_news_id = self._summaries_by_news_id(impact_summaries)
        for item in context:
            summary = summaries_by_news_id.get(item.id)
            if summary is None:
                lines.append(
                    f"- {item.title}: источник {item.source}, релевантность {item.score:.2f}.",
                )
            else:
                confidence = (
                    "нет оценки" if summary.confidence is None else f"{summary.confidence:.2f}"
                )
                impact = IMPACT_LABELS_RU.get(summary.impact, summary.impact)
                lines.append(
                    f"- {item.title}: влияние={impact}, уверенность={confidence}. "
                    f"{summary.explanation}",
                )
        lines.append(
            "Это аналитическая оценка на основе найденных новостей и не является "
            "финансовой рекомендацией.",
        )
        return "\n".join(lines)

    def _summaries_by_news_id(
        self,
        impact_summaries: list[DialogImpactItem],
    ) -> dict[str, DialogImpactItem]:
        summaries_by_news_id: dict[str, DialogImpactItem] = {}
        for summary in impact_summaries:
            if summary.news_id in summaries_by_news_id:
                raise DialogGeneratorUnavailableError("duplicate impact summaries")
            summaries_by_news_id[summary.news_id] = summary
        return summaries_by_news_id
