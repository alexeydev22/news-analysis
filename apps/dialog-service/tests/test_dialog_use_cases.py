import pytest
from dialog_service.application.use_cases import GenerateDialogAnswer
from dialog_service.domain.model import DialogGeneration
from economic_news_contracts.dialog import DialogContextNews, GenerateDialogRequest


class FakeGenerator:
    def __init__(self) -> None:
        self.question: str | None = None
        self.context_count: int | None = None

    async def generate(self, question, context, impact_summaries, language):
        self.question = question.value
        self.context_count = len(context)
        return DialogGeneration(
            answer="Рост ВВП выглядит позитивным фактором.",
            used_context_ids=[item.id for item in context],
            model_name="fake-generator",
            metadata={"language": language},
        )


@pytest.mark.asyncio
async def test_generate_dialog_answer_delegates_to_generator() -> None:
    generator = FakeGenerator()
    use_case = GenerateDialogAnswer(generator)
    request = GenerateDialogRequest(
        question="Что значит рост ВВП?",
        context=[
            DialogContextNews(
                id="news-1",
                title="GDP grows",
                text="GDP grew by 2 percent.",
                source="demo",
                score=0.75,
            ),
        ],
    )

    response = await use_case.execute(request)

    assert generator.question == "Что значит рост ВВП?"
    assert generator.context_count == 1
    assert response.answer == "Рост ВВП выглядит позитивным фактором."
    assert response.used_context_ids == ["news-1"]
    assert response.model_name == "fake-generator"
