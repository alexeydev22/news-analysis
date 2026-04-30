from dialog_service.domain.model import DialogContextItem, DialogImpactItem, DialogQuestion
from dialog_service.infrastructure.prompt_builder import DialogPromptBuilder


def test_prompt_builder_includes_question_context_impacts_and_constraints() -> None:
    builder = DialogPromptBuilder()

    messages = builder.build_messages(
        question=DialogQuestion("Что значит рост ВВП?"),
        context=[
            DialogContextItem(
                id="news-1",
                title="GDP grows",
                text="GDP grew by 2 percent.",
                source="demo",
                score=0.75,
            ),
        ],
        impact_summaries=[
            DialogImpactItem(
                news_id="news-1",
                model_name="tfidf-logreg",
                impact="positive",
                confidence=0.82,
                explanation="Рост ВВП обычно поддерживает рынок.",
            ),
        ],
        language="ru",
    )

    assert messages[0] == {
        "role": "system",
        "content": (
            "Ты аналитическая диалоговая система для экономических новостей. "
            "Отвечай на русском языке. Используй только переданный контекст, "
            "не выдумывай источники и факты, не обещай точные прогнозы рынка. "
            "Ответ не должен быть финансовой рекомендацией."
        ),
    }
    user_prompt = messages[1]["content"]
    assert messages[1]["role"] == "user"
    assert "Вопрос пользователя: Что значит рост ВВП?" in user_prompt
    assert "id: news-1" in user_prompt
    assert "title: GDP grows" in user_prompt
    assert "source: demo" in user_prompt
    assert "score: 0.75" in user_prompt
    assert "text: GDP grew by 2 percent." in user_prompt
    assert "impact: positive" in user_prompt
    assert "confidence: 0.82" in user_prompt
    assert "Рост ВВП обычно поддерживает рынок." in user_prompt
    assert "Короткий вывод" in user_prompt
    assert "Факторы влияния" in user_prompt
    assert "не финансовая рекомендация" in user_prompt


def test_prompt_builder_tells_model_when_context_is_empty() -> None:
    builder = DialogPromptBuilder()

    messages = builder.build_messages(
        question=DialogQuestion("Что с рынком?"),
        context=[],
        impact_summaries=[],
        language="ru",
    )

    user_prompt = messages[1]["content"]
    assert "Релевантные новости не найдены" in user_prompt
    assert "не отвечай из общих знаний" in user_prompt
