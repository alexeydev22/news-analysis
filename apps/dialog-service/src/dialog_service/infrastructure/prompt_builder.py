from dialog_service.domain.model import DialogContextItem, DialogImpactItem, DialogQuestion


class DialogPromptBuilder:
    def build_messages(
        self,
        question: DialogQuestion,
        context: list[DialogContextItem],
        impact_summaries: list[DialogImpactItem],
        language: str,
    ) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self._build_system_prompt(language)},
            {
                "role": "user",
                "content": self._build_user_prompt(question, context, impact_summaries),
            },
        ]

    def _build_system_prompt(self, language: str) -> str:
        language_instruction = (
            "Отвечай на русском языке."
            if language == "ru"
            else f"Отвечай на языке с кодом {language}."
        )
        return (
            "Ты аналитическая диалоговая система для экономических новостей. "
            f"{language_instruction} Используй только переданный контекст, "
            "не выдумывай источники и факты, не обещай точные прогнозы рынка. "
            "Ответ не должен быть финансовой рекомендацией."
        )

    def _build_user_prompt(
        self,
        question: DialogQuestion,
        context: list[DialogContextItem],
        impact_summaries: list[DialogImpactItem],
    ) -> str:
        lines = [
            f"Вопрос пользователя: {question.value}",
            "",
            "Найденные новости:",
        ]
        if not context:
            lines.append(
                "Релевантные новости не найдены; не отвечай из общих знаний.",
            )
        else:
            for item in context:
                lines.extend(
                    [
                        f"- id: {item.id}",
                        f"  title: {item.title}",
                        f"  source: {item.source}",
                        f"  score: {item.score:.2f}",
                        f"  text: {item.text}",
                    ],
                )
        lines.extend(["", "Результаты анализа экономического влияния:"])
        if not impact_summaries:
            lines.append("- Нет результатов анализа.")
        else:
            for summary in impact_summaries:
                confidence = (
                    "нет оценки"
                    if summary.confidence is None
                    else f"{summary.confidence:.2f}"
                )
                lines.extend(
                    [
                        f"- news_id: {summary.news_id}",
                        f"  model_name: {summary.model_name}",
                        f"  impact: {summary.impact}",
                        f"  confidence: {confidence}",
                        f"  explanation: {summary.explanation}",
                    ],
                )
        lines.extend(
            [
                "",
                "Сформируй ответ в формате:",
                "1. Короткий вывод.",
                "2. Факторы влияния.",
                "3. Оговорка: это аналитическая оценка на основе найденных новостей, "
                "а не финансовая рекомендация.",
            ],
        )
        return "\n".join(lines)
