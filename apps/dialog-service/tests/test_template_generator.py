import pytest
from dialog_service.domain.errors import DialogGeneratorUnavailableError
from dialog_service.domain.model import DialogContextItem, DialogImpactItem, DialogQuestion
from dialog_service.infrastructure.template_generator import TemplateDialogGenerator


@pytest.mark.asyncio
async def test_template_generator_builds_russian_answer_from_context_and_impacts() -> None:
    generator = TemplateDialogGenerator(model_name="template-dialog-generator")
    context = [
        DialogContextItem(
            id="news-1",
            title="GDP grows",
            text="GDP grew by 2 percent.",
            source="demo",
            score=0.75,
        ),
    ]
    summaries = [
        DialogImpactItem(
            news_id="news-1",
            model_name="tfidf-logreg",
            impact="positive",
            confidence=0.82,
            explanation="Рост ВВП обычно поддерживает рынок.",
        ),
    ]

    result = await generator.generate(
        question=DialogQuestion("Что значит рост ВВП?"),
        context=context,
        impact_summaries=summaries,
        language="ru",
    )

    assert "Что значит рост ВВП?" in result.answer
    assert "GDP grows" in result.answer
    assert "positive" in result.answer
    assert "не является финансовой рекомендацией" in result.answer
    assert result.used_context_ids == ["news-1"]
    assert result.model_name == "template-dialog-generator"
    assert result.metadata == {
        "generator_kind": "template",
        "model_name": "template-dialog-generator",
        "context_count": 1,
        "impact_summary_count": 1,
        "language": "ru",
    }


@pytest.mark.asyncio
async def test_template_generator_handles_empty_context() -> None:
    generator = TemplateDialogGenerator(model_name="template-dialog-generator")

    result = await generator.generate(
        question=DialogQuestion("Что с рынком?"),
        context=[],
        impact_summaries=[],
        language="ru",
    )

    assert "релевантные новости не найдены" in result.answer
    assert result.used_context_ids == []


@pytest.mark.asyncio
async def test_template_generator_rejects_duplicate_impact_summaries() -> None:
    generator = TemplateDialogGenerator(model_name="template-dialog-generator")
    context = [
        DialogContextItem(
            id="news-1",
            title="GDP grows",
            text="GDP grew by 2 percent.",
            source="demo",
            score=0.75,
        ),
    ]

    with pytest.raises(DialogGeneratorUnavailableError, match="duplicate impact summaries"):
        await generator.generate(
            question=DialogQuestion("Что значит рост ВВП?"),
            context=context,
            impact_summaries=[
                DialogImpactItem(
                    news_id="news-1",
                    model_name="tfidf-logreg",
                    impact="positive",
                    confidence=0.82,
                    explanation="Позитивное влияние.",
                ),
                DialogImpactItem(
                    news_id="news-1",
                    model_name="embedding-logreg",
                    impact="neutral",
                    confidence=0.64,
                    explanation="Нейтральное влияние.",
                ),
            ],
            language="ru",
        )
